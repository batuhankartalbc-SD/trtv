"""Çeviri motorları ve öncelikli, toplu çalışan çeviri yöneticisi."""
from __future__ import annotations

import itertools
import json
import logging
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

import httpx

log = logging.getLogger("ceviri")
TIMEOUT = httpx.Timeout(6.0, connect=3.0)


class TranslateError(Exception):
    pass


def system_prompt(game: str, glossary: dict[str, str], tone: str, style: str = "") -> str:
    keep = [k for k, v in glossary.items() if not v]
    pairs = [f"{k} → {v}" for k, v in glossary.items() if v]
    s = (
        "You are a professional video game localizer translating English on-screen text into Turkish in real time.\n"
        f"Game: {game or 'unknown'}.\n"
        f"Style: natural, short, spoken Turkish ({'informal, friendly' if tone == 'samimi' else 'neutral, polite'}). "
        "Keep the meaning and the attitude; translate slang and profanity faithfully, do not soften or censor. "
        "Keep it about as short as the original so it fits on screen. "
        "Never translate proper names of people, brands, places, vehicles or radio stations. "
        "Keep button placeholders like [X], [L1] unchanged. "
        "If a line is OCR garbage, return it unchanged.\n"
    )
    if style.strip():
        s += "Game and character style notes (follow them): " + style.strip() + "\n"
    if keep:
        s += "Never translate: " + ", ".join(keep) + "\n"
    if pairs:
        s += "Glossary (use exactly): " + "; ".join(pairs) + "\n"
    s += ('Input is JSON: {"context": [previous dialogue lines], "lines": [lines to translate]}. '
          'Output ONLY a JSON array of Turkish strings, same length and order as "lines".')
    return s


def _parse_array(text: str, n: int) -> list[str]:
    text = text.strip()
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise TranslateError(f"JSON yok: {text[:120]}")
    arr = json.loads(m.group(0))
    if not isinstance(arr, list) or len(arr) != n:
        raise TranslateError(f"beklenen {n} satır, gelen {len(arr) if isinstance(arr, list) else '?'}")
    return [str(a) for a in arr]


class Engine:
    name = "base"
    is_llm = False

    def __init__(self, key: str = "", model: str = ""):
        self.key = key
        self.model = model
        self.client = httpx.Client(timeout=TIMEOUT, http2=False)

    def translate(self, lines: list[str], context: list[str], sys: str) -> list[str]:
        raise NotImplementedError


class FreeEngine(Engine):
    """Anahtarsız, ücretsiz MyMemory çeviri API'si (günlük kotalı). Kota/hız sınırında bir süre bekler."""
    name = "free"
    _lock = threading.Lock()
    _cooldown_until = 0.0
    _last = 0.0
    MIN_GAP = 0.15

    def translate(self, lines, context, sys):
        out = []
        for ln in lines:
            with FreeEngine._lock:
                now = time.monotonic()
                if now < FreeEngine._cooldown_until:
                    raise TranslateError(f"ücretsiz servis sınırı, {FreeEngine._cooldown_until - now:.0f} sn bekleniyor")
                wait = FreeEngine._last + self.MIN_GAP - now
                if wait > 0:
                    time.sleep(wait)
                FreeEngine._last = time.monotonic()
            r = self.client.get("https://api.mymemory.translated.net/get", params={"q": ln[:480], "langpair": "en|tr"})
            if r.status_code == 429:
                FreeEngine._cooldown_until = time.monotonic() + 60
                raise TranslateError("ücretsiz servis hız sınırı (429), 60 sn ara verildi")
            r.raise_for_status()
            data = r.json()
            if int(data.get("responseStatus", 200)) != 200:
                if "QUOTA" in str(data.get("responseDetails", "")).upper():
                    FreeEngine._cooldown_until = time.monotonic() + 600
                raise TranslateError(f"ücretsiz servis: {data.get('responseDetails')}")
            out.append(data["responseData"]["translatedText"])
        return out

class Gemini(Engine):
    name = "gemini"
    is_llm = True

    def translate(self, lines, context, sys):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": sys}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps({"context": context, "lines": lines}, ensure_ascii=False)}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        if getattr(self, "_thinking_ok", True):
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}   # düşünme kapalı = daha hızlı
        r = self.client.post(url, json=body, headers={"x-goog-api-key": self.key})
        if r.status_code == 400 and "thinking" in r.text.lower():
            self._thinking_ok = False
            body["generationConfig"].pop("thinkingConfig", None)
            r = self.client.post(url, json=body, headers={"x-goog-api-key": self.key})
        if r.status_code != 200:
            raise TranslateError(f"Gemini {r.status_code}: {r.text[:200]}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        return _parse_array("".join(p.get("text", "") for p in parts), len(lines))


class OpenAI(Engine):
    name = "openai"
    is_llm = True

    def translate(self, lines, context, sys):
        body = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": sys},
                {"role": "user", "content": json.dumps({"context": context, "lines": lines}, ensure_ascii=False)},
            ],
        }
        r = self.client.post("https://api.openai.com/v1/chat/completions", json=body,
                             headers={"Authorization": f"Bearer {self.key}"})
        if r.status_code != 200:
            raise TranslateError(f"OpenAI {r.status_code}: {r.text[:200]}")
        return _parse_array(r.json()["choices"][0]["message"]["content"], len(lines))


class Claude(Engine):
    name = "claude"
    is_llm = True

    def translate(self, lines, context, sys):
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0.2,
            "system": sys,
            "messages": [{"role": "user", "content": json.dumps({"context": context, "lines": lines}, ensure_ascii=False)}],
        }
        r = self.client.post("https://api.anthropic.com/v1/messages", json=body,
                             headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"})
        if r.status_code != 200:
            raise TranslateError(f"Claude {r.status_code}: {r.text[:200]}")
        text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        return _parse_array(text, len(lines))


class DeepL(Engine):
    name = "deepl"

    def translate(self, lines, context, sys):
        host = "api-free.deepl.com" if self.key.endswith(":fx") else "api.deepl.com"
        r = self.client.post(f"https://{host}/v2/translate",
                             json={"text": lines, "source_lang": "EN", "target_lang": "TR",
                                   "context": " ".join(context[-4:]) or None},
                             headers={"Authorization": f"DeepL-Auth-Key {self.key}"})
        if r.status_code != 200:
            raise TranslateError(f"DeepL {r.status_code}: {r.text[:200]}")
        return [t["text"] for t in r.json()["translations"]]


def local_model_dir():
    """Yerel model klasörü: önce uygulamanın kendi klasörü, sonra CouchSubs'ın indirdiği kopya."""
    import os
    from pathlib import Path
    from .config import APP_DIR
    for p in (APP_DIR / "models" / "en-tr-ct2",
              Path(os.environ.get("LOCALAPPDATA", "")) / "CouchSubs" / "models" / "en-tr-ct2"):
        if (p / "model.bin").exists() and (p / "source.spm").exists():
            return p
    return None


MODEL_URL = "https://github.com/batuhankartalbc-SD/trtv/releases/download/model-en-tr/en-tr-ct2.zip"


def download_model(progress=None) -> bool:
    """Yerel çeviri modelini (≈450 MB) indirir ve uygulama klasörüne kurar. progress(yüzde, mesaj)."""
    import shutil
    import tempfile
    import zipfile
    from pathlib import Path
    from .config import APP_DIR
    dst = APP_DIR / "models"
    dst.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.gettempdir()) / "trceviri_model.zip"
    try:
        with httpx.stream("GET", MODEL_URL, follow_redirects=True, timeout=httpx.Timeout(30.0, read=60.0)) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0)) or 1
            got = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
                    got += len(chunk)
                    if progress:
                        progress(int(got * 100 / total), f"İndiriliyor… {got / 1e6:.0f} / {total / 1e6:.0f} MB")
        if progress:
            progress(100, "Kuruluyor…")
        with zipfile.ZipFile(tmp) as z:
            z.extractall(dst)
        tmp.unlink(missing_ok=True)
        LocalEngine._shared = None
        ok = local_model_dir() is not None
        if progress:
            progress(100, "Yerel model hazır ✓" if ok else "Kurulum başarısız")
        return ok
    except Exception as e:
        log.error("model indirilemedi: %s", e)
        if progress:
            progress(0, f"İndirilemedi: {e}")
        try:
            shutil.rmtree(dst / "en-tr-ct2.partial", ignore_errors=True)
        except Exception:
            pass
        return False


class LocalEngine(Engine):
    """İnternetsiz, anlık çeviri: Helsinki-NLP opus-mt-tc-big-en-tr (CC-BY 4.0), CTranslate2 ile.
    Satır başına ~40–160 ms."""
    name = "local"
    _shared = None
    _lock = threading.Lock()

    def __init__(self, key: str = "", model: str = ""):
        super().__init__(key, model)
        with LocalEngine._lock:
            if LocalEngine._shared is None:
                import ctranslate2
                import sentencepiece as spm
                d = local_model_dir()
                if d is None:
                    raise TranslateError("Yerel çeviri modeli bulunamadı")
                tr = ctranslate2.Translator(str(d), device="cpu", compute_type="int8", inter_threads=2, intra_threads=4)
                src = spm.SentencePieceProcessor(model_file=str(d / "source.spm"))
                tgt = spm.SentencePieceProcessor(model_file=str(d / "target.spm"))
                tr.translate_batch([src.encode("ok", out_type=str) + ["</s>"]])   # ısınma
                LocalEngine._shared = (tr, src, tgt)
        self.tr, self.src, self.tgt = LocalEngine._shared

    @staticmethod
    def _tr_upper(s: str) -> str:
        return s.replace("i", "İ").replace("ı", "I").upper()

    def translate(self, lines, context, sys):
        # TAMAMI BÜYÜK HARF satırlar modelde bozuk harf (⁇) üretiyor: normal yazımla çevir, sonra büyüt
        caps = [l.isupper() and sum(c.isalpha() for c in l) >= 3 for l in lines]
        src = [l.capitalize() if c else l for l, c in zip(lines, caps)]
        toks = [self.src.encode(l, out_type=str)[:200] + ["</s>"] for l in src]
        res = self.tr.translate_batch(toks, beam_size=2, max_decoding_length=120, repetition_penalty=1.1)
        out = []
        for r, c in zip(res, caps):
            t = self.tgt.decode(r.hypotheses[0]).replace("⁇", "").strip()
            t = re.sub(r"^[-–]\s*", "", t)
            out.append(self._tr_upper(t) if c else t)
        return out


ENGINES = {"local": LocalEngine, "gemini": Gemini, "openai": OpenAI, "claude": Claude, "deepl": DeepL, "free": FreeEngine}
ENGINE_LABELS = {
    "local": "Yerel — anlık, internetsiz (önerilen)",
    "gemini": "Google Gemini (önerilen)",
    "openai": "OpenAI",
    "claude": "Anthropic Claude",
    "deepl": "DeepL",
    "free": "Ücretsiz (MyMemory, anahtarsız, günlük kotalı)",
}


def make_engine(name: str, key: str, model: str) -> Engine:
    cls = ENGINES.get(name, FreeEngine)
    if cls is LocalEngine:
        try:
            return LocalEngine()
        except Exception as e:
            log.warning("yerel motor açılamadı (%s), ücretsiz motor kullanılacak", e)
            return FreeEngine()
    if cls is not FreeEngine and not key:
        log.warning("%s için API anahtarı yok, ücretsiz motor kullanılacak", name)
        return FreeEngine()
    return cls(key, model)


@dataclass(order=True)
class Job:
    priority: int
    seq: int
    text: str = field(compare=False)
    is_dialogue: bool = field(compare=False, default=False)
    callback: Callable[[str, str | None, str, float], None] = field(compare=False, default=None)
    t0: float = field(compare=False, default_factory=time.perf_counter)


class TranslationManager:
    """Arka planda çalışır; aynı anda gelen satırları tek istekte toplar."""

    BATCH_WINDOW = 0.04

    def __init__(self, engine: Engine, fallback: Engine | None, game: str, glossary: dict, tone: str, context_lines: int,
                 refine: Engine | None = None, style: str = ""):
        self.engine = engine
        self.fallback = fallback
        self.refine = refine          # anlık çeviriden sonra daha kaliteli çeviriyle değiştir (ör. Gemini)
        self.rq: queue.Queue = queue.Queue()
        if refine is not None:
            for i in range(3):
                threading.Thread(target=self._refine_run, daemon=True, name=f"iyilestir-{i}").start()
        self.sys = system_prompt(game, glossary, tone, style)
        self.context: deque[str] = deque(maxlen=max(0, context_lines))
        self.q: queue.PriorityQueue[Job] = queue.PriorityQueue()
        self.seq = itertools.count()
        self.inflight: set[str] = set()
        self.lock = threading.Lock()
        self.stop_evt = threading.Event()
        self.workers = [threading.Thread(target=self._run, daemon=True, name=f"ceviri-{i}") for i in range(4)]
        for w in self.workers:
            w.start()

    def submit(self, text: str, priority: int, is_dialogue: bool, callback) -> None:
        with self.lock:
            if text in self.inflight:
                return
            self.inflight.add(text)
        self.q.put(Job(priority, next(self.seq), text, is_dialogue, callback))

    def stop(self) -> None:
        self.stop_evt.set()
        for _ in self.workers:
            self.q.put(Job(-1, next(self.seq), "", False, None))

    def _run(self) -> None:
        while not self.stop_evt.is_set():
            job = self.q.get()
            if job.callback is None:
                return
            batch = [job]
            # altyazı (öncelik 0) beklemeden tek başına gider: en düşük gecikme
            deadline = time.perf_counter() + (0 if job.priority == 0 else self.BATCH_WINDOW)
            while len(batch) < 8:
                left = deadline - time.perf_counter()
                if left <= 0:
                    break
                try:
                    nxt = self.q.get(timeout=left)
                except queue.Empty:
                    break
                if nxt.callback is None:
                    self.q.put(nxt)
                    break
                batch.append(nxt)
            self._do(batch)

    def _do(self, batch: list[Job]) -> None:
        texts = [j.text for j in batch]
        ctx = list(self.context)
        used = self.engine.name
        result: list[str | None]
        try:
            result = list(self.engine.translate(texts, ctx, self.sys))
        except Exception as e:
            log.warning("%s hatası: %s", self.engine.name, e)
            result = [None] * len(texts)
            if self.fallback is not None and self.fallback is not self.engine:
                try:
                    result = list(self.fallback.translate(texts, ctx, self.sys))
                    used = self.fallback.name
                except Exception as e2:
                    log.error("yedek motor da başarısız: %s", e2)
        for j, tr in zip(batch, result):
            with self.lock:
                self.inflight.discard(j.text)
            if j.is_dialogue:
                self.context.append(j.text)
            try:
                j.callback(j.text, tr, used, (time.perf_counter() - j.t0) * 1000)
            except Exception:
                log.exception("çeviri geri çağrısı hatası")
            if self.refine is not None and tr:
                self.rq.put((j, list(self.context)))

    def _refine_run(self) -> None:
        while not self.stop_evt.is_set():
            try:
                j, ctx = self.rq.get(timeout=1)
            except queue.Empty:
                continue
            try:
                better = self.refine.translate([j.text], ctx[:-1] if ctx and ctx[-1] == j.text else ctx, self.sys)[0]
                if better:
                    j.callback(j.text, better, self.refine.name, (time.perf_counter() - j.t0) * 1000)
            except Exception as e:
                log.info("iyileştirme atlandı (%s): %s", self.refine.name, e)
