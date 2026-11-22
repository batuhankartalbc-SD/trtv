"""Yakala → değişim algıla → OCR → çevir → overlay'e gönder."""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from dataclasses import dataclass

import mss
import numpy as np
from PySide6.QtCore import QObject, Signal
from rapidfuzz import fuzz

from . import keystore, winutil
from .cache import TranslationCache
from .config import BLOCK_TYPES, ZONE_PRIORITY, Profile, Settings, Zone
from .detect import ChangeGate
from .ocr import FullScreenReader, Line, OcrEngine
from .textproc import (cache_key, clean_symbols, is_controls, is_navigation, is_noise, letters, looks_english,
                       normalize, split_speaker)
from .translate import FreeEngine, TranslationManager, make_engine

log = logging.getLogger("hat")
SAME = 90  # aynı satır sayılma benzerliği


@dataclass
class Item:
    src: str
    speaker: str
    box: tuple[float, float, float, float]   # oyun alanına göre 0–1 (x0, y0, x1, y1)
    line_h: float                             # tek satır yüksekliği (0–1)
    lines: int
    tr: str | None = None
    kind: str = "text"                        # subtitle | objective | text
    score: float = 1.0
    misses: int = 0
    t0: float = 0.0                            # ilk görüldüğü an (gecikme ölçümü)

    fg: str = ""                               # oyundaki yazı rengi (ölçülen)
    bg: str = ""                               # yazının arkasındaki zemin rengi (ölçülen)
    sc: str = ""                               # konuşmacı adının rengi (ölçülen)
    align: str = "c"                           # c = ortalı, l = sola dayalı
    first: tuple | None = None                 # ilk satırın kutusu (konuşmacı rengi için)

    def copy(self) -> "Item":
        it = Item(self.src, self.speaker, self.box, self.line_h, self.lines, self.tr, self.kind, self.score)
        it.fg, it.bg, it.sc, it.align = self.fg, self.bg, self.sc, self.align
        return it

    def measure(self, frame, W: int, H: int, ox: int = 0, oy: int = 0) -> None:
        """Renkleri kareden ölç. box 0–1 (W×H alanına göre); ox/oy: alanın kare içindeki başlangıcı."""
        try:
            from .colors import sample
            x0, y0, x1, y1 = self.box
            px = (ox + x0 * W, oy + y0 * H, ox + x1 * W, oy + y1 * H)
            self.fg, self.bg = sample(frame, px)
            if self.speaker and self.first:
                fx0, fy0, fx1, fy1 = self.first
                frac = min(0.6, (len(self.speaker) + 1) / max(1, len(self.speaker) + 2 + len(self.src)))
                spx = (ox + fx0 * W, oy + fy0 * H, ox + (fx0 + (fx1 - fx0) * frac) * W, oy + fy1 * H)
                self.sc, _ = sample(frame, spx)
            cx = (x0 + x1) / 2
            self.align = "c" if self.kind in ("subtitle", "objective") or abs(cx - 0.5) < 0.06 else "l"
        except Exception:
            pass


def apply_glossary_exact(text: str, glossary: dict[str, str]) -> str | None:
    for k, v in glossary.items():
        if v and k.lower() == text.lower():
            return v
    return None


class ZoneTracker:
    def __init__(self, zone: Zone, pipe: "Pipeline"):
        self.zone = zone
        self.pipe = pipe
        self.gate = ChangeGate(pipe.settings.change_threshold)
        self.items: list[Item] = []
        self.candidate: list[Item] | None = None
        self.empty = 0
        self.lock = threading.Lock()

    # --- OCR sonucu → öğeler
    def _items_from_lines(self, lines: list[Line], cw: int, ch: int) -> list[Item]:
        z = self.zone

        def norm_box(b):
            x0, y0, x1, y1 = b
            return (z.x + x0 / cw * z.w, z.y + y0 / ch * z.h, z.x + x1 / cw * z.w, z.y + y1 / ch * z.h)

        clean = []
        for ln in lines:
            t = normalize(ln.text)
            if is_noise(t, self.pipe.profile.ignore):
                continue
            clean.append(Line(t, ln.box, ln.score))
        if not clean:
            return []
        if z.type in BLOCK_TYPES:
            # altyazılar ortalıdır: kenardaki GPS / HUD yazılarını blokdan çıkar
            mid = cw / 2
            centered = [c for c in clean
                        if abs((c.box[0] + c.box[2]) / 2 - mid) <= cw * 0.18 or (c.box[2] - c.box[0]) >= cw * 0.45]
            if not centered:
                return []
            clean = centered
            speaker, first = split_speaker(clean[0].text)
            text = " ".join([first] + [c.text for c in clean[1:]]).strip()
            x0 = min(c.box[0] for c in clean); y0 = min(c.box[1] for c in clean)
            x1 = max(c.box[2] for c in clean); y1 = max(c.box[3] for c in clean)
            lh = sum(c.box[3] - c.box[1] for c in clean) / len(clean) / ch * z.h
            it = Item(text, speaker if self.pipe.settings.show_speaker else "", norm_box((x0, y0, x1, y1)), lh,
                      len(clean), kind=z.type)
            it.first = norm_box(clean[0].box)
            return [it]
        out = []
        for c in clean:
            lh = (c.box[3] - c.box[1]) / ch * z.h
            out.append(Item(c.text, "", norm_box(c.box), lh, 1))
        return out

    @staticmethod
    def _same(a: list[Item], b: list[Item]) -> bool:
        return len(a) == len(b) and all(fuzz.ratio(x.src, y.src) >= SAME for x, y in zip(a, b))

    def update(self, lines: list[Line], cw: int, ch: int, frame=None) -> None:
        new = self._items_from_lines(lines, cw, ch)
        if frame is not None:
            FH, FW = frame.shape[:2]
            for it in new:
                it.measure(frame, FW, FH)
        with self.lock:
            if not new:
                self.empty += 1
                self.candidate = None
                if self.items:
                    self.gate.prev = None          # bir sonraki karede hemen tekrar oku
                if self.empty >= 2 and self.items:
                    self.items = []
                    self.pipe.publish(self.zone.id, [])
                return
            self.empty = 0
            if self.items and self._same(new, self.items):
                # aynı yazı: sadece konumu güncelle
                moved = any(abs(n.box[1] - o.box[1]) > 0.01 or abs(n.box[0] - o.box[0]) > 0.02 for n, o in zip(new, self.items))
                if moved:
                    for n, o in zip(new, self.items):
                        o.box, o.line_h, o.lines = n.box, n.line_h, n.lines
                    self._publish_locked()
                return
            avg = sum(l.score for l in lines) / max(1, len(lines))
            known = all(self.pipe.lookup(i.src, fuzzy=False) for i in new)
            stable = known or avg >= 0.93 or (self.candidate is not None and self._same(new, self.candidate))
            if not stable:
                self.candidate = new
                return
            self.candidate = None
            self.items = new
            pending = []
            for it in self.items:
                if not looks_english(it.src):
                    continue
                hit = self.pipe.lookup(it.src)
                if hit:
                    it.tr = hit
                    self.pipe.record(it.src, hit, "önbellek", 0.0)
                else:
                    pending.append(it.src)
            self._publish_locked()
        prio = ZONE_PRIORITY.get(self.zone.type, 3)
        for src in pending:
            self.pipe.manager.submit(src, prio, self.zone.type == "subtitle", self.on_translated)

    def on_translated(self, src: str, tr: str | None, engine: str, ms: float) -> None:
        if tr:
            self.pipe.cache.put(self.pipe.scope, src, tr, engine)
            self.pipe.record(src, tr, engine, ms)
        with self.lock:
            changed = False
            for it in self.items:
                if it.src == src and tr:
                    it.tr = tr
                    changed = True
            if changed:
                self._publish_locked()

    def _publish_locked(self) -> None:
        shown = [i.copy() for i in self.items if i.tr]
        for i in shown:
            self.pipe.remember(i)
        self.pipe.publish(self.zone.id, shown)


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _line_color(frame, box) -> tuple | None:
    """Satırdaki yazının rengi (BGR) — blokları ayırmak için (görev yazısı ≠ konuşma rengi)."""
    if frame is None:
        return None
    try:
        from .colors import sample
        fg, _ = sample(frame, box)
        return tuple(int(fg[i:i + 2], 16) for i in (1, 3, 5))
    except Exception:
        return None


def _same_color(a, b, tol: float = 70.0) -> bool:
    if a is None or b is None:
        return True
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5 <= tol


FILM_TOP = 0.55        # film modunda altyazı bandı: ekranın alt %45'i


def film_clean(t: str) -> str:
    """Film altyazısı satırını sadeleştirir: <i> etiketleri, baştaki konuşma tiresi korunur, boşluklar."""
    t = re.sub(r"</?[ibu]>", "", t, flags=re.I).strip()
    t = re.sub(r"^[-–—]\s*", "- ", t)
    return t.strip()


def build_blocks(lines: list[Line], W: int, H: int, ignore: list[str], show_speaker: bool,
                 cats: set[str] | None = None, frame=None, film: bool = False) -> list[Item]:
    """Tüm ekrandaki satırları paragraflara (bloklara) ayırır, türünü belirler ve
    sadece istenen türleri döndürür: subtitle (konuşma), menu, controls, other, nav (GPS).
    film=True: film/dizi — sadece ekranın alt kısmındaki altyazı okunur (oynatıcı düğmeleri, başlıklar atlanır)."""
    clean = []
    for ln in lines:
        if film:
            raw = normalize(ln.text)
            if "♪" in raw or "♫" in raw or ln.box[1] < FILM_TOP * H:
                continue                       # şarkı sözü satırı ya da altyazı bandı dışında
            raw = film_clean(raw)
            if not raw:
                continue
            t = clean_symbols(raw) if not raw.startswith(("[", "(", "-")) else raw
        else:
            t = clean_symbols(normalize(ln.text))
        if is_noise(t, ignore) or not looks_english(t):
            continue
        if letters(t) < 3 or not any(len(w) >= 3 and w.isalpha() for w in t.replace("'", "").split()):
            continue
        clean.append(Line(t, ln.box, ln.score))
    clean.sort(key=lambda l: l.box[1])
    blocks: list[list[Line]] = []
    for ln in clean:
        h = ln.box[3] - ln.box[1]
        cx = (ln.box[0] + ln.box[2]) / 2
        for blk in blocks:
            last = blk[-1]
            lh = last.box[3] - last.box[1]
            gap = ln.box[1] - last.box[3]
            lcx = (last.box[0] + last.box[2]) / 2
            overlap = min(ln.box[2], last.box[2]) - max(ln.box[0], last.box[0])
            wmax = max(ln.box[2] - ln.box[0], last.box[2] - last.box[0])
            # menü/telefon listelerindeki kısa öğeler ayrı kalsın; cümleler paragraf olsun
            prose = len(last.text.split()) >= 3 and len(ln.text.split()) >= 2
            # farklı renkteki satır (ör. sarı görev yazısı ↔ beyaz konuşma) aynı paragraf sayılmaz
            if frame is not None and not _same_color(_line_color(frame, last.box), _line_color(frame, ln.box)):
                continue
            if (prose and -0.3 * lh <= gap <= 0.9 * lh and 0.7 <= h / max(1, lh) <= 1.4
                    and (overlap > 0 or abs(cx - lcx) < 0.3 * wmax)):
                blk.append(ln)
                break
        else:
            blocks.append([ln])
    # menü listesi: aynı soldan hizalı, benzer boyutta, kısa (≤5 kelime) en az 3 tek satırlık öğe
    singles = [b for b in blocks if len(b) == 1 and len(b[0].text.split()) <= 5]
    menu_ids: set[int] = set()
    for b in singles:
        bx, bh = b[0].box[0], b[0].box[3] - b[0].box[1]
        col = [o for o in singles if abs(o[0].box[0] - bx) < 0.015 * W and 0.75 <= (o[0].box[3] - o[0].box[1]) / max(1, bh) <= 1.33]
        if len(col) >= 3:
            menu_ids.update(id(o) for o in col)
    items = []
    for blk in blocks:
        x0 = min(l.box[0] for l in blk); y0 = min(l.box[1] for l in blk)
        x1 = max(l.box[2] for l in blk); y1 = max(l.box[3] for l in blk)
        cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
        text = " ".join(l.text for l in blk)
        if film:
            kind = "subtitle"                  # film modunda alt banttaki her şey altyazıdır
        elif is_navigation(text):
            kind = "nav"
        elif cy > 0.6 and abs(cx - 0.5) < 0.18 and (x1 - x0) / W > 0.12 and not is_controls(text):
            kind = "subtitle"
        elif is_controls(text) or (x1 / W < 0.4 and y1 / H < 0.35):      # sol üst ipucu kutusu = kontroller
            kind = "controls"
        elif id(blk) in menu_ids:
            kind = "menu"
        else:
            kind = "other"
        if cats is not None and kind not in cats:
            continue
        speaker = ""
        if kind == "subtitle":
            speaker, text = split_speaker(text)
            if not show_speaker:
                speaker = ""
        lh = sum(l.box[3] - l.box[1] for l in blk) / len(blk) / H
        score = sum(l.score for l in blk) / len(blk)
        it = Item(text, speaker, (x0 / W, y0 / H, x1 / W, y1 / H), lh, len(blk), kind=kind, score=score)
        f0 = blk[0].box
        it.first = (f0[0] / W, f0[1] / H, f0[2] / W, f0[3] / H)
        items.append(it)
    return items


class AutoTracker:
    """Otomatik mod: tüm ekranda çıkan/kalkan yazıları tek tek takip eder."""

    def __init__(self, pipe: "Pipeline"):
        self.zone_id = "auto"
        self.pipe = pipe
        self.items: list[Item] = []
        self.candidates: dict[str, int] = {}
        self.lock = threading.Lock()

    def update(self, lines: list[Line], W: int, H: int, frame=None) -> None:
        p = self.pipe
        film = getattr(p.profile, "is_film", False)
        new = build_blocks(lines, W, H, p.profile.ignore, p.settings.show_speaker, p.settings.categories(film), frame, film)
        pending: list[Item] = []
        with self.lock:
            changed = False
            matched: set[int] = set()
            fresh: list[Item] = []
            for n in new:
                ncx, ncy = (n.box[0] + n.box[2]) / 2, (n.box[1] + n.box[3]) / 2
                best = None
                for i, it in enumerate(self.items):
                    if i in matched:
                        continue
                    icx, icy = (it.box[0] + it.box[2]) / 2, (it.box[1] + it.box[3]) / 2
                    if abs(icx - ncx) < 0.08 and abs(icy - ncy) < 0.08 and fuzz.ratio(it.src, n.src) >= 88:
                        best = i
                        break
                if best is None:
                    fresh.append(n)
                    continue
                matched.add(best)
                it = self.items[best]
                it.misses = 0
                # titremeyi önle: OCR kutusu her karede birkaç piksel oynar. Yazı gerçekten taşınmadıkça
                # (merkez > %1.5 ekran ya da yükseklik > %25 değişim) konum ve boyut sabit kalır.
                icx, icy = (it.box[0] + it.box[2]) / 2, (it.box[1] + it.box[3]) / 2
                moved = abs(icx - ncx) > 0.015 or abs(icy - ncy) > 0.015
                resized = abs(n.line_h - it.line_h) > 0.25 * max(1e-4, it.line_h) or n.lines != it.lines
                if moved or resized:
                    it.box, it.line_h, it.lines = n.box, n.line_h, n.lines
                    changed = True
            for i, it in enumerate(self.items):
                if i not in matched:
                    it.misses += 1
            before = len(self.items)
            self.items = [it for it in self.items if it.misses < 2]
            changed |= len(self.items) != before
            seen_now: dict[str, int] = {}
            for n in fresh:
                # aynı yerde farklı yazı çıktı: eski Türkçeyi yenisi onaylanmadan HEMEN kaldır (geç kalma yok)
                # (OCR'ın aynı yazıyı biraz yanlış okuması "farklı yazı" sayılmasın: benzerlik < 70 şartı)
                stale = [it for it in self.items if _iou(it.box, n.box) >= 0.3 and fuzz.ratio(it.src, n.src) < 70]
                if stale:
                    self.items = [it for it in self.items if it not in stale]
                    changed = True
                key = cache_key(n.src)
                hit = p.lookup(n.src, fuzzy=False)
                # anlık mod: yazı ilk karede (okuma güveni yeterliyse) hemen gösterilir; normal modda
                # emin değilsek bir kare daha görülmesi beklenir (yanlış okumayı çevirmemek için)
                instant = p.settings.instant and n.score >= 0.6
                if hit or instant or n.score >= 0.85 or key in self.candidates:
                    # aynı yerde eski yazı varsa (satır değişti) hemen kaldır
                    self.items = [it for it in self.items if _iou(it.box, n.box) < 0.3]
                    n.tr = clean_symbols(hit) or hit if hit else hit
                    n.t0 = time.perf_counter()
                    if frame is not None:
                        n.measure(frame, W, H)
                    self.items.append(n)
                    changed = True
                    if hit:
                        p.record(n.src, hit, "önbellek", 0.0)
                    else:
                        pending.append(n)
                else:
                    seen_now[key] = 1
            self.candidates = seen_now
            if changed:
                self._publish_locked()
        for n in pending:
            prio = 0 if n.kind == "subtitle" else 2
            p.manager.submit(n.src, prio, n.kind == "subtitle", self.on_translated)

    def on_translated(self, src: str, tr: str | None, engine: str, ms: float) -> None:
        if tr:
            tr = clean_symbols(tr) or tr
            self.pipe.cache.put(self.pipe.scope, src, tr, engine)
            self.pipe.record(src, tr, engine, ms)
        with self.lock:
            hit = False
            for it in self.items:
                if it.src == src and tr:
                    it.tr = tr
                    hit = True
                    if it.t0:
                        self.pipe.total_ms.append((time.perf_counter() - it.t0) * 1000)
            if hit:
                self._publish_locked()

    def _publish_locked(self) -> None:
        shown = [i.copy() for i in self.items if i.tr]
        for i in shown:
            self.pipe.remember(i)
        self.pipe.publish(self.zone_id, shown)


class Capturer:
    """Önce PrintWindow (pencere örtülse de çalışır), olmazsa ekran yakalama (mss)."""

    def __init__(self, mode: str = "auto"):
        self.mode = mode
        self.sct = mss.mss()
        self.window_failed = 0

    def grab(self, hwnd, client, content) -> np.ndarray | None:
        """Önce pencerenin kendisinden (PrintWindow) okur. Ekran yakalamaya SADECE pencere en öndeyse geçer;
        önünde başka pencere varken ekranı okursak o pencerenin yazılarını çevirirdik (ör. sohbet pencereleri)."""
        cx, cy, cw, ch = client
        x, y, w, h = content
        ox, oy = x - cx, y - cy
        now = time.monotonic()
        img = None
        # pencere yakalama başarısız olsa bile 2 sn'de bir yeniden dene (kalıcı olarak vazgeçme)
        if self.mode != "screen" and (self.window_failed < 30 or now - getattr(self, "_last_try", 0) > 2.0):
            self._last_try = now
            img = winutil.capture_window(hwnd, cw, ch)
            # karanlık sahne ≠ hata: sadece TAMAMEN siyah (çizilmemiş) kare başarısız sayılır
            if img is not None and (self.mode == "window" or int(img[::6, ::6].max()) > 6):
                if self.window_failed >= 30:
                    log.info("Pencere yakalama yeniden çalışıyor")
                self.window_failed = 0
                return np.ascontiguousarray(img[oy:oy + h, ox:ox + w])
            self.window_failed += 1
            if self.window_failed == 30:
                log.info("Pencere yakalama çalışmıyor; pencere öndeyken ekran yakalama kullanılacak")
        if self.window_failed < 30 and img is not None:
            return np.ascontiguousarray(img[oy:oy + h, ox:ox + w])     # kısa süreli siyah kare: olduğu gibi kullan
        if not winutil.is_on_top(hwnd, x + w // 2, y + h // 2):
            return None                                                   # önünde başka pencere var: okuma
        shot = self.sct.grab({"left": x, "top": y, "width": w, "height": h})
        return np.ascontiguousarray(np.array(shot)[:, :, :3])

    def close(self):
        try:
            self.sct.close()
        except Exception:
            pass


class Pipeline(QObject):
    items_changed = Signal(str, list)
    status = Signal(str, bool, str)        # anahtar, durum, mesaj
    translated = Signal(str, str, str, float)
    stats = Signal(dict)
    preview = Signal(object)               # küçültülmüş kare (QImage) — panel önizlemesi

    def __init__(self, settings: Settings, profile: Profile, cache: TranslationCache):
        super().__init__()
        self.settings = settings
        self.profile = profile
        self.cache = cache
        self.manager: TranslationManager | None = None
        self.thread: threading.Thread | None = None
        self.running = threading.Event()
        self.paused = False
        self.hwnd: int | None = None
        self.content_rect: tuple[int, int, int, int] | None = None
        self.trackers: dict[str, ZoneTracker] = {}
        self.auto: AutoTracker | None = None
        self.listeners: list = []
        self.pack: dict[str, str] = {}
        self.history: deque = deque(maxlen=30)
        self.tts = None
        self.ocr_ms: deque[float] = deque(maxlen=50)
        self.tr_ms: deque[float] = deque(maxlen=50)
        self.total_ms: deque[float] = deque(maxlen=50)
        self.want_preview = True
        self.force_retranslate = False

    @property
    def scope(self) -> str:
        return f"{self.profile.name}|{self.settings.engine}"

    # --- dış API
    def ensure_manager(self) -> TranslationManager:
        """Çeviri motoru; yakalama çalışmıyorken de (TV bağımsız mod çevirileri için) kullanılabilir."""
        sig = (self.settings.engine, self.settings.refine, self.profile.name)
        m = self.manager
        if m is None or m.stop_evt.is_set() or (not self.running.is_set() and getattr(self, "_mgr_sig", None) != sig):
            if m is not None and not m.stop_evt.is_set():
                m.stop()
            self.manager = self._build_manager()
            self._mgr_sig = sig
            self.load_pack()
        return self.manager

    def _build_manager(self) -> TranslationManager:
        s = self.settings
        key = keystore.decrypt(s.api_keys_enc.get(s.engine, ""))
        engine = make_engine(s.engine, key, s.models.get(s.engine, ""))
        fallback = FreeEngine() if s.fallback_free else None
        refine = None
        if s.refine and engine.name == "local":
            for name in ("gemini", "claude", "openai"):
                k2 = keystore.decrypt(s.api_keys_enc.get(name, ""))
                if k2:
                    refine = make_engine(name, k2, s.models.get(name, ""))
                    break
        return TranslationManager(engine, fallback, self.profile.game or self.profile.name,
                                  self.profile.glossary, s.tone, s.context_lines, refine=refine,
                                  style=self.profile.style, kind=getattr(self.profile, "kind", "game"))

    def start(self) -> None:
        if self.running.is_set():
            return
        s = self.settings
        if self.manager is not None:
            self.manager.stop()
        self.manager = self._build_manager()
        self._mgr_sig = (s.engine, s.refine, self.profile.name)
        engine, refine = self.manager.engine, self.manager.refine
        self.load_pack()
        label = {"local": "Yerel (anlık)", "free": "Ücretsiz (MyMemory)"}.get(engine.name, engine.name)
        self.status.emit("ceviri", True, f"Çeviri: {label}" + (f" + {refine.name} iyileştirme" if refine else ""))
        self.reload_zones()
        self.running.set()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="yakalama")
        self.thread.start()

    def stop(self) -> None:
        self.running.clear()
        if self.thread:
            self.thread.join(timeout=3)
        if self.manager:
            self.manager.stop()
        for zid in list(self.trackers) + ["auto"]:
            self.items_changed.emit(zid, [])
        self.content_rect = None

    def reload_zones(self) -> None:
        if self.settings.auto_mode:
            self.auto = AutoTracker(self)
            self.trackers = {}
            for z in self.profile.zones:
                self.items_changed.emit(z.id, [])
            return
        self.auto = None
        self.items_changed.emit("auto", [])
        self.trackers = {z.id: ZoneTracker(z, self) for z in self.profile.zones if z.enabled}
        for z in self.profile.zones:
            if not z.enabled:
                self.items_changed.emit(z.id, [])

    # --- hazır paket, sözlük, önbellek
    def load_pack(self) -> None:
        self.pack = {}
        name = getattr(self.profile, "pack", "")
        if not name:
            return
        import json
        from .config import BUNDLED_PROFILES, PROFILE_DIR
        for d in (PROFILE_DIR / "packs", BUNDLED_PROFILES / "packs"):
            f = d / f"{name}.json"
            if f.exists():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    self.pack = {cache_key(k): v for k, v in data.items()}
                    log.info("Hazır çeviri paketi: %s (%d satır)", name, len(self.pack))
                except Exception as e:
                    log.warning("paket okunamadı: %s", e)
                return

    def lookup(self, text: str, fuzzy: bool = True) -> str | None:
        """Sırayla: sözlük (tam eşleşme) → hazır oyun paketi → çeviri önbelleği."""
        return (apply_glossary_exact(text, self.profile.glossary)
                or getattr(self, "pack", {}).get(cache_key(text))
                or self.cache.get(self.scope, text, fuzzy=fuzzy))

    def speaker_color(self, name: str) -> str:
        pal = ["#FF7AB6", "#5EC8FF", "#FFD54A", "#7CFFB2", "#C9A2FF", "#FF9F5A", "#7FE3FF", "#F4F48C"]
        sc = getattr(self.profile, "speaker_colors", {}) or {}
        for k, v in sc.items():
            if k.lower() == name.lower():
                return v
        return pal[sum(map(ord, name.lower())) % len(pal)]

    def _decorate(self, items: list[Item]) -> list[Item]:
        s = self.settings
        for it in items:
            if it.speaker and s.speaker_colors_on:
                it.sc = self.speaker_color(it.speaker)
            elif not s.match_colors:
                it.sc = ""
        return items

    def remember(self, it: Item) -> None:
        """Konuşma geçmişi (F6 ile tekrar gösterilir) + seslendirme."""
        if it.kind != "subtitle" or not it.tr:
            return
        if not self.history or self.history[-1].src != it.src:
            self.history.append(it.copy())
        if self.tts is not None:
            self.tts.say((f"{it.tr}"), key=it.src)

    def publish(self, zone_id: str, items: list[Item]) -> None:
        items = self._decorate(items)
        for cb in self.listeners:          # TV'ye doğrudan, Qt kuyruğunu beklemeden
            try:
                cb(zone_id, items)
            except Exception:
                log.exception("dinleyici hatası")
        self.items_changed.emit(zone_id, items)

    def record(self, src: str, tr: str, engine: str, ms: float) -> None:
        if ms > 0:
            self.tr_ms.append(ms)
        self.translated.emit(src, tr, engine, ms)

    def retranslate_last(self) -> None:
        for t in list(self.trackers.values()) + ([self.auto] if self.auto else []):
            with t.lock:
                for it in t.items:
                    self.manager.submit(it.src, 0, False, t.on_translated)

    def locate(self):
        """(istemci alanı, oyun alanı) — ekran koordinatlarında; pencere yoksa None."""
        now = time.monotonic()
        if not winutil.is_valid(self.hwnd) or now - getattr(self, "_last_find", 0) > 2.0:
            self._last_find = now
            found = winutil.find_window(self.settings.window_hint, restore=self.settings.auto_restore)
            if found != self.hwnd:
                log.info("Oyun penceresi: %s", found)
                self.hwnd = found
        if not self.hwnd or winutil.is_minimized(self.hwnd):
            return None
        client = winutil.client_rect(self.hwnd)
        if not client:
            return None
        content = winutil.fit_16_9(client) if self.settings.force_16_9 else client
        return client, content

    def grab_frame(self) -> np.ndarray | None:
        """Bölge düzenleyici için anlık kare (BGR)."""
        loc = self.locate()
        if not loc:
            return None
        cap = Capturer(self.settings.capture_mode)
        try:
            return cap.grab(self.hwnd, *loc)
        finally:
            cap.close()

    # --- iş parçacığı
    def _loop(self) -> None:
        try:
            self.status.emit("ocr", False, "OCR yükleniyor…")
            ocr = OcrEngine(self.settings.use_gpu, self.settings.ocr_threads)
            self.status.emit("ocr", True, "OCR hazır")
        except Exception as e:
            log.exception("OCR başlatılamadı")
            self.status.emit("ocr", False, f"OCR başlatılamadı: {e}")
            self.running.clear()
            return
        cap = Capturer(self.settings.capture_mode)
        reader = FullScreenReader(ocr, self.settings.auto_scan_width)
        last_stats = 0.0
        frames = 0
        last_prev = 0.0
        last_win_ok = None
        while self.running.is_set():
            tick = time.perf_counter()
            if self.paused:
                time.sleep(0.2)
                continue
            loc = self.locate()
            ok = loc is not None
            if ok != last_win_ok:
                self.status.emit("pencere", ok, "Pencere bulundu" if ok else "Remote Play penceresi bulunamadı / küçültülmüş")
                last_win_ok = ok
            self.content_rect = loc[1] if loc else None
            if not loc:
                time.sleep(0.5)
                continue
            try:
                frame = cap.grab(self.hwnd, *loc)
            except Exception as e:
                log.warning("yakalama hatası: %s", e)
                frame = None
            if frame is None:
                time.sleep(0.3)
                continue
            h, w = frame.shape[:2]
            now = time.perf_counter()
            if self.want_preview and now - last_prev > 0.5:
                last_prev = now
                try:
                    import cv2
                    from PySide6.QtGui import QImage
                    pw = 640
                    small = cv2.cvtColor(cv2.resize(frame, (pw, max(1, int(h * pw / w))), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
                    self.preview.emit(QImage(small.data, small.shape[1], small.shape[0], 3 * small.shape[1], QImage.Format_RGB888).copy())
                except Exception:
                    pass
            auto = self.auto
            if auto is not None:
                t0 = time.perf_counter()
                lines = reader.read(frame, 0.6)
                self.ocr_ms.append((time.perf_counter() - t0) * 1000)
                try:
                    auto.update(lines, w, h, frame)
                except Exception:
                    log.exception("otomatik mod hatası")
            for t in sorted(self.trackers.values(), key=lambda t: ZONE_PRIORITY.get(t.zone.type, 3)):
                z = t.zone
                x0, y0 = max(0, int(z.x * w)), max(0, int(z.y * h))
                x1, y1 = min(w, int((z.x + z.w) * w)), min(h, int((z.y + z.h) * h))
                if x1 - x0 < 8 or y1 - y0 < 8:
                    continue
                crop = np.ascontiguousarray(frame[y0:y1, x0:x1])
                if not t.gate.should_ocr(crop, now):
                    continue
                t0 = time.perf_counter()
                lines = ocr.read(crop, z.min_confidence)
                self.ocr_ms.append((time.perf_counter() - t0) * 1000)
                try:
                    t.update(lines, x1 - x0, y1 - y0, frame)
                except Exception:
                    log.exception("bölge güncelleme hatası")
            frames += 1
            if tick - last_stats > 1.0:
                self.real_fps = frames / max(1e-3, tick - last_stats) if last_stats else 0.0
                frames = 0
                last_stats = tick
                self.stats.emit({
                    "fps": round(self.real_fps, 1),
                    "ocr": sum(self.ocr_ms) / len(self.ocr_ms) if self.ocr_ms else 0,
                    "ceviri": sum(self.tr_ms) / len(self.tr_ms) if self.tr_ms else 0,
                    "toplam": sum(self.total_ms) / len(self.total_ms) if self.total_ms else 0,
                    "onbellek": self.cache.count(),
                    "refine": (self.manager.refine_status if self.manager and self.manager.refine else None),
                })
            spent = time.perf_counter() - tick
            time.sleep(max(0.0, 1.0 / max(1, self.settings.fps) - spent))
        cap.close()
