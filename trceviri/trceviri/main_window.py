"""Brolis Game Translate kontrol paneli — tasarım görselleriyle birebir düzen."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                               QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QDoubleSpinBox)

from . import applog, keystore, winutil
from .config import CACHE_FILE, list_profiles, load_profile, save_profile
from .icons import icon, pixmap
from .theme import ACCENT, MUTED, PURPLE, TEXT
from .translate import ENGINE_LABELS, local_model_dir, make_engine, system_prompt
from .widgets import brand_icon, brand_logo, Metric, Segmented, StatusRow, Toggle, card, field, ibtn, iconlabel, page_header, sep, tool
from .zones_page import ZonesPage

log = logging.getLogger("panel")
GUIDE = Path(__file__).resolve().parent.parent / "NASIL KULLANILIR.txt"
APK = Path(__file__).resolve().parent.parent / "TRCeviri-TV.apk"
OUTPUTS = [("pc", "Sadece PC", "monitor"), ("tv", "Sadece TV", "tv"), ("both", "İkisinde de", None)]
ENGINE_ICON = {"local": "cpu", "gemini": "sparkle", "openai": "sparkle", "claude": "sparkle", "deepl": "translate", "free": "google"}
MODELS = {"gemini": ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"],
          "openai": ["gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o-mini"],
          "claude": ["claude-haiku-5-5", "claude-sonnet-5-5"]}


def scroll(w: QWidget) -> QScrollArea:
    s = QScrollArea(); s.setWidget(w); s.setWidgetResizable(True); s.setFrameShape(QFrame.NoFrame)
    s.setStyleSheet("QScrollArea{background:transparent;} QScrollArea > QWidget > QWidget{background:transparent;}")
    return s


class Preview(QWidget):
    """Canlı kare + üstüne Türkçe (bilgisayar katmanıyla aynı çizim)."""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.img: QImage | None = None
        self.items: dict[str, list] = {}
        self.setMinimumSize(560, 315)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_frame(self, img):
        self.img = img; self.update()

    def set_items(self, zone, items):
        if items:
            self.items[zone] = items
        else:
            self.items.pop(zone, None)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        h = min(H, W * 9 / 16); w = h * 16 / 9
        r = QRectF((W - w) / 2, (H - h) / 2, w, h)
        path = QPainterPath(); path.addRoundedRect(r, 14, 14); p.setClipPath(path)
        if self.img is not None:
            p.drawImage(r, self.img)
        else:
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, QColor("#141B24")); g.setColorAt(1, QColor("#0D1218")); p.fillRect(r, g)
            p.setPen(QColor(MUTED))
            p.drawText(r, Qt.AlignCenter, "Oyun görüntüsü burada görünecek\nPS Remote Play açık ve PS5'e bağlı olmalı")
        p.translate(r.topLeft())
        ov = self.ctx.overlay
        bg = QColor(self.ctx.settings.box_color)
        for items in self.items.values():
            for it in items:
                ov._draw_item(p, it, int(w), int(h), bg, 1.0, None)
        p.end()


class LookPreview(QWidget):
    """Görünüm sayfasındaki örnek oynatıcı: örnek altyazılar seçili görünümle çizilir."""
    SAMPLES = [("Polisler sahil yolunu kapatmış.", "The cops closed the beach road.", "Jason"),
               ("Nereye gidiyorsun?", "Where are you going?", "Lucia"),
               ("Araca binmek için X'e bas.", "Press X to enter the vehicle.", "")]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.i = 0
        self.playing = False
        self.timer = QTimer(self); self.timer.timeout.connect(self.next)
        self.setMinimumSize(520, 330)

    def next(self):
        self.i = (self.i + 1) % len(self.SAMPLES); self.update()

    def toggle(self):
        self.playing = not self.playing
        self.timer.start(1800) if self.playing else self.timer.stop()
        self.update()

    def mousePressEvent(self, e):
        if e.position().y() > self.height() - 46:
            self.toggle()

    def paintEvent(self, _):
        from .pipeline import Item
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height() - 46
        h = min(H, W * 9 / 16); w = h * 16 / 9
        r = QRectF((W - w) / 2, 0, w, h)
        path = QPainterPath(); path.addRoundedRect(r, 12, 12); p.save(); p.setClipPath(path)
        img = self.ctx.window.preview.img if getattr(self.ctx, "window", None) else None
        if img is not None:
            p.drawImage(r, img)
        else:
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0, QColor("#1B1035")); g.setColorAt(0.55, QColor("#3A1F4D")); g.setColorAt(1, QColor("#0E1A22"))
            p.fillRect(r, g)
        p.translate(r.topLeft())
        tr, en, spk = self.SAMPLES[self.i]
        it = Item(en, spk if self.ctx.settings.show_speaker else "", (0.30, 0.84, 0.70, 0.90), 0.05, 1, tr, kind="subtitle")
        it.fg = "#FFFFFF"; it.sc = self.ctx.settings.speaker_color; it.bg = "#2A1B3A"; it.align = "c"
        self.ctx.overlay._draw_item(p, it, int(w), int(h), QColor(self.ctx.settings.box_color), 1.0, None)
        p.restore()
        # oynatıcı çubuğu
        y = H + 14
        p.drawPixmap(int(r.left()) + 6, int(y), pixmap("pause" if self.playing else "play", TEXT, 18))
        p.setPen(QColor("#C5CED8")); p.drawText(int(r.left()) + 38, int(y) + 14, f"0:{(self.i * 6 + 12) % 60:02d} / 0:20")
        x0, x1 = r.left() + 130, r.right() - 70
        p.setPen(Qt.NoPen); p.setBrush(QColor("#2A3440")); p.drawRoundedRect(QRectF(x0, y + 7, x1 - x0, 4), 2, 2)
        frac = (self.i + 1) / len(self.SAMPLES)
        p.setBrush(QColor(ACCENT)); p.drawRoundedRect(QRectF(x0, y + 7, (x1 - x0) * frac, 4), 2, 2)
        p.drawEllipse(QRectF(x0 + (x1 - x0) * frac - 7, y + 2, 14, 14))
        p.drawPixmap(int(r.right()) - 56, int(y), pixmap("volume", TEXT, 18))
        p.drawPixmap(int(r.right()) - 26, int(y), pixmap("maximize", TEXT, 18))
        p.end()


class MainWindow(QMainWindow):
    test_done = Signal(bool, str)
    model_prog = Signal(int, str)
    update_found = Signal(dict)
    update_prog = Signal(int)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.s = ctx.settings
        from .config import DEV
        self.setWindowTitle(("[GELİŞTİRME] " if DEV else "") + "Brolis Game Translate — Oyun içi anlık Türkçe çeviri")
        self.setWindowIcon(brand_icon())
        self.resize(1420, 900)
        root = QWidget(); root.setObjectName("root")
        lay = QHBoxLayout(root); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        lay.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        self.preview = Preview(ctx)
        self.pages = [self._page_main(), self._page_zones(), self._page_translate(), self._page_look(),
                      self._page_tv(), self._page_adv()]
        for i, page in enumerate(self.pages):
            wrap = QWidget(); v = QVBoxLayout(wrap); v.setContentsMargins(30, 24, 30, 24); v.addWidget(page)
            self.stack.addWidget(wrap if i in (0, 1) else scroll(wrap))
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        p = ctx.pipeline
        p.status.connect(self.on_status)
        p.translated.connect(self.on_translated)
        p.stats.connect(self.on_stats)
        p.preview.connect(self.preview.set_frame)
        p.items_changed.connect(self.preview.set_items)
        ctx.tv.status.connect(self.on_tv_status)
        applog.bridge.line.connect(self.log_view.appendPlainText)
        self.test_done.connect(self._on_test_done)
        self.update_found.connect(self._on_update)
        self.update_prog.connect(lambda p: self.upd_btn.setText(f"  İndiriliyor %{p}"))
        self.sync_run_buttons()
        QTimer.singleShot(4000, self.check_update)

    # ================================================================ kenar menü
    def _sidebar(self) -> QWidget:
        sb = QWidget(); sb.setObjectName("sidebar"); sb.setFixedWidth(250)
        v = QVBoxLayout(sb); v.setContentsMargins(14, 26, 14, 18); v.setSpacing(6)
        lr = QHBoxLayout(); lr.setContentsMargins(10, 0, 0, 0); lr.setSpacing(10)
        lr.addWidget(brand_logo(40))
        logo = QLabel(f"Brolis<br><span style='color:{ACCENT};font-size:13px;font-weight:600'>Game Translate</span>")
        logo.setObjectName("logo"); logo.setTextFormat(Qt.RichText)
        lr.addWidget(logo); lr.addStretch()
        v.addLayout(lr); v.addSpacing(26)
        self.nav = QButtonGroup(self)
        for i, (ic, name) in enumerate((("home", "Ana"), ("zones", "Bölgeler"), ("translate", "Çeviri"),
                                        ("monitor", "Görünüm"), ("tv", "TV"), ("settings", "Gelişmiş"))):
            b = QPushButton("   " + name); b.setObjectName("nav"); b.setCheckable(True)
            b.setIcon(icon(ic, TEXT, 22)); b.setIconSize(QSize(22, 22)); b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=i: self.go(k))
            self.nav.addButton(b, i); v.addWidget(b)
        self.nav.button(0).setChecked(True)
        v.addStretch()
        wiz = ibtn("Kurulum sihirbazı", "wand"); wiz.clicked.connect(self.ctx.open_wizard)
        hlp = ibtn("Nasıl kullanılır?", "help"); hlp.clicked.connect(self.open_help)
        v.addWidget(wiz); v.addWidget(hlp)
        from . import __version__
        from .config import DEV
        ver = QLabel(f"v{__version__}" + (" · GELİŞTİRME" if DEV else " · PS Remote Play + Android TV"))
        if DEV:
            ver.setStyleSheet("color:#F5B942;font-weight:700;"); ver.setObjectName("small"); ver.setContentsMargins(6, 6, 0, 0)
        v.addWidget(ver)
        return sb

    def go(self, k: int):
        self.nav.button(k).setChecked(True)
        self.stack.setCurrentIndex(k)
        if k == 1:
            self.zones_page.update_banner()

    # ================================================================ Ana
    def _page_main(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(16)
        self.upd_bar = QFrame(); self.upd_bar.setObjectName("card2"); ub = QHBoxLayout(self.upd_bar); ub.setContentsMargins(16, 10, 16, 10)
        ub.addWidget(iconlabel("download", ACCENT, 20)); self.upd_lbl = QLabel(); ub.addWidget(self.upd_lbl, 1)
        self.upd_btn = ibtn("Güncelle", "download", "primary"); ub.addWidget(self.upd_btn)
        self.upd_bar.hide(); v.addWidget(self.upd_bar)
        top = QHBoxLayout()
        t = QLabel("Canlı çeviri"); t.setObjectName("h1"); top.addWidget(t); top.addStretch()
        self.btn_run = ibtn("Çeviri çalışıyor", "play", "primary"); self.btn_run.setMinimumHeight(44); self.btn_run.setMinimumWidth(210)
        self.btn_run.clicked.connect(self.start)
        self.btn_stop = ibtn("Durdur", "stop"); self.btn_stop.setMinimumHeight(44); self.btn_stop.setMinimumWidth(160)
        self.btn_stop.clicked.connect(self.stop)
        top.addWidget(self.btn_run); top.addSpacing(10); top.addWidget(self.btn_stop)
        v.addLayout(top)
        v.addWidget(sep())

        row = QHBoxLayout(); row.setSpacing(12)
        wbox = QFrame(); wbox.setObjectName("card2"); wh = QHBoxLayout(wbox); wh.setContentsMargins(14, 4, 6, 4)
        wh.addWidget(iconlabel("gamepad", TEXT, 24))
        self.win_combo = QComboBox(); self.win_combo.setEditable(True); self.win_combo.setMinimumWidth(220)
        self.win_combo.setStyleSheet("QComboBox{border:none;background:transparent;font-size:16px;}")
        self.win_combo.setCurrentText(self.s.window_hint); wh.addWidget(self.win_combo)
        b_ref = ibtn("Pencereyi yenile", "refresh"); b_ref.setMinimumHeight(44); b_ref.clicked.connect(self.refresh_windows)
        pbox = QFrame(); pbox.setObjectName("card2"); ph = QHBoxLayout(pbox); ph.setContentsMargins(14, 4, 6, 4)
        ph.addWidget(iconlabel("monitor", TEXT, 22))
        self.prof_combo = QComboBox(); self.prof_combo.setMinimumWidth(150)
        self.prof_combo.setStyleSheet("QComboBox{border:none;background:transparent;font-size:16px;}")
        self.prof_combo.addItems(list_profiles()); self.prof_combo.setCurrentText(self.s.profile)
        self.prof_combo.currentTextChanged.connect(self.change_profile); ph.addWidget(self.prof_combo)
        ph.addWidget(QLabel("·  16:9  "))
        self.out_main = Segmented(OUTPUTS, self.s.output_target); self.out_main.changed.connect(self.set_output)
        row.addWidget(wbox); row.addWidget(b_ref); row.addWidget(pbox); row.addStretch()
        ol = QLabel("Çeviri nerede görünsün:"); ol.setObjectName("muted"); row.addWidget(ol); row.addWidget(self.out_main)
        v.addLayout(row)

        body = QHBoxLayout(); body.setSpacing(18)
        left = QVBoxLayout(); left.setSpacing(16)
        pv = QFrame(); pv.setObjectName("card"); pvl = QVBoxLayout(pv); pvl.setContentsMargins(0, 0, 0, 0); pvl.addWidget(self.preview)
        left.addWidget(pv, 3)
        rc, rv = card("Son çeviriler", "list")
        self.recent = QTableWidget(0, 3)
        self.recent.setHorizontalHeaderLabels(["İngilizce (kaynak)", "Türkçe (çeviri)", ""])
        hh = self.recent.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed); self.recent.setColumnWidth(2, 40)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.recent.verticalHeader().setVisible(False)
        self.recent.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent.setSelectionBehavior(QTableWidget.SelectRows); self.recent.setShowGrid(False)
        self.recent.setFocusPolicy(Qt.NoFocus)
        rv.addWidget(self.recent)
        left.addWidget(rc, 2)
        body.addLayout(left, 3)

        right = QVBoxLayout(); right.setSpacing(14)
        sc, sv = card("Sistem durumu", "monitor")
        sv.setSpacing(0)
        self.st = {}
        for i, (k, n) in enumerate((("pencere", "Pencere"), ("ocr", "OCR"), ("ceviri", "Çeviri"), ("tv", "TV"))):
            if i:
                sv.addWidget(sep())
            self.st[k] = StatusRow(n)
            sv.addWidget(self.st[k])
        right.addWidget(sc)
        self.m_ocr = Metric("scan", "OCR", ACCENT)
        self.m_tr = Metric("translate", "Çeviri", PURPLE)
        self.m_tot = Metric("timer", "Toplam", ACCENT)
        for m in (self.m_ocr, self.m_tr, self.m_tot):
            right.addWidget(m)
        fr = QHBoxLayout()
        self.lbl_cache = QLabel("Son 50 satır"); self.lbl_cache.setObjectName("muted"); fr.addWidget(self.lbl_cache); fr.addStretch()
        ii = iconlabel("info", MUTED, 18); ii.setToolTip("Değerler son 50 çevrilen satırın ortalamasıdır."); fr.addWidget(ii)
        right.addLayout(fr)
        right.addStretch()
        rw = QWidget(); rw.setLayout(right); rw.setFixedWidth(400)
        body.addWidget(rw)
        v.addLayout(body, 1)

        keys = QFrame(); keys.setObjectName("card")
        kh = QHBoxLayout(keys); kh.setContentsMargins(40, 12, 40, 12)
        for i, (k, d) in enumerate((("F8", "Katman (Aç/Kapat)"), ("F9", "Duraklat (Çeviri)"), ("F6", "Son konuşma"),
                                    ("F10", "Bölgeler"), ("F11", "Yeniden çevir"), ("F7", "Hata ayıklama"))):
            if i:
                kh.addStretch(); kh.addWidget(sep(True)); kh.addStretch()
            kl = QLabel(k); kl.setObjectName("key"); kh.addWidget(kl); kh.addSpacing(8); kh.addWidget(QLabel(d))
        v.addWidget(keys)
        self.refresh_windows()
        return w

    def refresh_windows(self):
        cur = self.win_combo.currentText()
        self.win_combo.blockSignals(True); self.win_combo.clear()
        titles = [t for _, t in winutil.list_windows() if "Brolis" not in t and "TRÇeviri" not in t and "toolbar" not in t.lower()]
        rp = [t for t in titles if any(h in t.lower() for h in winutil.REMOTE_HINTS)]
        self.win_combo.addItems(list(dict.fromkeys(rp + [t for t in titles if t not in rp])))
        self.win_combo.setCurrentText(cur or (rp[0] if rp else "PS Remote Play"))
        self.win_combo.blockSignals(False)

    def start(self):
        p = self.ctx.pipeline
        if p.running.is_set():
            return
        self.s.window_hint = self.win_combo.currentText().strip() or "PS Remote Play"
        self.s.save()
        p.hwnd = None
        p.start()
        self.sync_run_buttons()

    def stop(self):
        p = self.ctx.pipeline
        if p.running.is_set():
            p.stop()
            for k in ("pencere", "ocr", "ceviri"):
                self.st[k].set(None, "durduruldu")
        self.sync_run_buttons()

    def toggle_run(self):
        self.stop() if self.ctx.pipeline.running.is_set() else self.start()

    def sync_run_buttons(self):
        run = self.ctx.pipeline.running.is_set()
        self.btn_run.setText("  Çeviri çalışıyor" if run else "  Çeviriyi başlat")
        self.btn_stop.setEnabled(run)

    def set_output(self, target: str):
        self.s.set_output(target); self.s.save()
        for seg in (self.out_main, getattr(self, "out_tv", None)):
            if seg:
                seg.set(target)
        self.ctx.overlay.follow()
        if not self.s.tv_enabled:
            self.ctx.tv.clear()
        self.ctx.tv.reconnect() if self.s.tv_enabled and not self.ctx.tv.connected else None
        log.info("Çeviri gösterimi: %s", dict((k, t) for k, t, _ in OUTPUTS)[target])

    def set_auto(self, on: bool):
        self.s.auto_mode = on; self.s.save()
        self.ctx.overlay.zone_items.clear(); self.ctx.tv.clear()
        self.ctx.pipeline.reload_zones()
        if hasattr(self, "auto_toggle"):
            self.auto_toggle.blockSignals(True); self.auto_toggle.setChecked(on); self.auto_toggle.setPos(1.0 if on else 0.0)
            self.auto_toggle.blockSignals(False)
        self.zones_page.update_banner()
        log.info("Otomatik mod %s", "açık" if on else "kapalı (bölgeler kullanılıyor)")

    def change_profile(self, name: str):
        if not name:
            return
        self.s.profile = name; self.s.save()
        self.ctx.set_profile(load_profile(name))
        for c in (self.prof_combo,):
            c.blockSignals(True); c.setCurrentText(name); c.blockSignals(False)
        self.load_glossary()
        if hasattr(self, "style_edit"):
            self.style_edit.blockSignals(True); self.style_edit.setPlainText(self.ctx.profile.style); self.style_edit.blockSignals(False)
        if hasattr(self, "spk_table"):
            self.load_speakers()
        self.zones_page.reload_from_profile()

    def on_status(self, key, ok, msg):
        log.info("Durum [%s] %s", key, msg)
        if key in self.st:
            self.st[key].set(ok, msg)
        self.sync_run_buttons()

    def on_tv_status(self, ok, msg):
        self.st["tv"].set(ok if self.s.tv_enabled else None, msg if self.s.tv_enabled else "TV çıkışı kapalı")
        if hasattr(self, "tv_state"):
            self.tv_state.setText(msg)
            self.tv_state_icon.setPixmap(pixmap("check" if ok else "dot", ACCENT if ok else MUTED, 28))

    def on_translated(self, src, tr, engine, ms):
        self.recent.insertRow(0); self.recent.setRowHeight(0, 40)
        self.recent.setItem(0, 0, QTableWidgetItem(src))
        if ": " in tr and len(tr.split(": ", 1)[0]) <= 20:
            spk, rest = tr.split(": ", 1)
            lbl = QLabel(f"<b>{spk}:</b> {rest}")
        else:
            lbl = QLabel(tr)
        lbl.setContentsMargins(10, 0, 0, 0)
        self.recent.setCellWidget(0, 1, lbl)
        b = tool("copy", "Kopyala"); b.clicked.connect(lambda _=False, t=tr: QGuiApplication.clipboard().setText(t))
        self.recent.setCellWidget(0, 2, b)
        while self.recent.rowCount() > 200:
            self.recent.removeRow(self.recent.rowCount() - 1)

    def on_stats(self, d):
        self.m_ocr.set(d["ocr"]); self.m_tr.set(d["ceviri"]); self.m_tot.set(d.get("toplam", 0))
        self.lbl_cache.setText(f"Son 50 satır · önbellekte {d['onbellek']} çeviri")
        if d.get("refine") != getattr(self.ctx.tv, "refine_status", None):
            self.ctx.tv.refine_status = d.get("refine")        # TV Tanılama ekranı için (style.refine)
            self.ctx.tv.send_style()
        if d.get("refine"):
            ok = not any(w in d["refine"] for w in ("kota", "geçersiz"))
            self.st["ceviri"].set(ok, f"Yerel (anlık) + Gemini: {d['refine']}")

    # ================================================================ Bölgeler
    def _page_zones(self) -> QWidget:
        self.zones_page = ZonesPage(self.ctx)
        return self.zones_page

    def open_zone_editor(self):
        self.go(1)

    # ================================================================ Çeviri
    def _page_translate(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(18)
        v.addWidget(page_header("Çeviri", "Çeviri motorunu, API bağlantısını ve terim sözlüğünü ayarlayın.", "translate"))
        c, cv = card("Çeviri motoru")
        g = QGridLayout(); g.setHorizontalSpacing(14); g.setVerticalSpacing(14)
        self.eng = QComboBox()
        for k, lbl in ENGINE_LABELS.items():
            self.eng.addItem(icon(ENGINE_ICON.get(k, "translate"), ACCENT if k == "local" else "#8AB4F8", 18), lbl, k)
        self.eng.setCurrentIndex(max(0, self.eng.findData(self.s.engine)))
        self.model = QComboBox(); self.model.setEditable(True)
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.Password)
        eye = QAction(icon("eye", "#C5CED8", 18), "Göster", self.key); eye.setCheckable(True)
        eye.toggled.connect(lambda on: self.key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        self.key.addAction(eye, QLineEdit.TrailingPosition)
        self.key.editingFinished.connect(self._save_key)
        b_test = ibtn("Bağlantıyı test et", "link", "outlineGreen"); b_test.clicked.connect(self.test_engine)
        self.test_ok = QLabel(); self.test_ok.setFixedSize(28, 28)
        self.fallback = QComboBox()
        self.fallback.addItem(icon("google", TEXT, 18), "Ücretsiz (MyMemory)", True); self.fallback.addItem("Yok", False)
        self.fallback.setCurrentIndex(0 if self.s.fallback_free else 1)
        self.refine = Toggle(self.s.refine)
        g.addWidget(QLabel("Motor"), 0, 0); g.addWidget(self.eng, 0, 1)
        g.addWidget(QLabel("Model"), 0, 2); g.addWidget(self.model, 0, 3, 1, 2)
        g.addWidget(QLabel("API anahtarı"), 1, 0); g.addWidget(self.key, 1, 1, 1, 2); g.addWidget(b_test, 1, 3); g.addWidget(self.test_ok, 1, 4)
        g.addWidget(QLabel("Yedek motor"), 2, 0); g.addWidget(self.fallback, 2, 1)
        hint = QHBoxLayout(); hint.addWidget(iconlabel("info", MUTED, 16))
        hl = QLabel("Ana motor yanıt vermezse kullanılır."); hl.setObjectName("muted"); hint.addWidget(hl); hint.addStretch()
        g.addLayout(hint, 2, 2, 1, 3)
        rr = QHBoxLayout(); rr.addWidget(self.refine)
        rl = QLabel("Anlık yerel çeviriyi, Gemini anahtarı varsa daha doğal çeviriyle iyileştir"); rr.addWidget(rl); rr.addStretch()
        g.addLayout(rr, 3, 0, 1, 5)
        g.setColumnStretch(1, 2); g.setColumnStretch(3, 2)
        cv.addLayout(g)
        mrow = QHBoxLayout()
        self.model_status = QLabel(); self.model_status.setObjectName("muted"); mrow.addWidget(self.model_status)
        self.b_model = ibtn("Yerel modeli indir (≈450 MB)", "download", "outlineGreen"); self.b_model.clicked.connect(self.download_model)
        mrow.addWidget(self.b_model); mrow.addStretch()
        cv.addLayout(mrow)
        self.model_prog.connect(self._model_progress)
        self.eng.currentIndexChanged.connect(lambda _: (self._save_engine(), self.load_engine_fields()))
        self.model.currentTextChanged.connect(lambda _: self._save_engine(restart=False))
        self.fallback.currentIndexChanged.connect(lambda _: self._save_engine())
        self.refine.toggled.connect(lambda on: (setattr(self.s, "refine", on), self.s.save(), self.restart_if_running()))
        self.load_engine_fields()
        v.addWidget(c)

        cc, ccv = card("Neleri çevirsin?")
        crow = QGridLayout(); crow.setHorizontalSpacing(24); crow.setVerticalSpacing(10)
        for i, (attr, ic, label) in enumerate((("cat_dialogue", "message", "Konuşmalar"), ("cat_menu", "list", "Menüler"),
                                               ("cat_controls", "gamepad", "Kontroller / tuş ipuçları"),
                                               ("cat_other", "flag", "Diğer yazılar (görev, bildirim, tabela)"),
                                               ("cat_nav", "target", "GPS / yön (Sağa dön, 120 m)"))):
            tg = Toggle(getattr(self.s, attr)); tg.toggled.connect(lambda on, a=attr: self._set_cat(a, on))
            cell = QHBoxLayout(); cell.addWidget(tg); cell.addWidget(iconlabel(ic, "#C5CED8", 18)); cell.addWidget(QLabel(label)); cell.addStretch()
            crow.addLayout(cell, i // 3, i % 3)
        ccv.addLayout(crow)
        v.addWidget(cc)

        cs, csv = card("Oyun ve karakter üslubu")
        sl = QLabel("Gemini (ya da başka yapay zekâ) bu talimata göre çevirir: oyunun dünyası, karakterlerin konuşma tarzı, argo. "
                    "Her oyun profilinde ayrı saklanır.")
        sl.setObjectName("muted"); sl.setWordWrap(True); csv.addWidget(sl)
        self.style_edit = QPlainTextEdit(self.ctx.profile.style); self.style_edit.setFixedHeight(96)
        self.style_edit.setStyleSheet("QPlainTextEdit{font-family:'Segoe UI';font-size:14px;padding:6px;}")
        self._style_timer = QTimer(self); self._style_timer.setSingleShot(True); self._style_timer.timeout.connect(self._save_style)
        self.style_edit.textChanged.connect(lambda: self._style_timer.start(700))
        csv.addWidget(self.style_edit)
        v.addWidget(cs)
        c2, cv2 = card("Terim sözlüğü")
        sub = QLabel("Özel isimleri, oyun içi terimleri ve sık geçen ifadeleri nasıl çevireceğinizi tanımlayın. Değişiklikler kendiliğinden kaydedilir.")
        sub.setObjectName("muted"); sub.setWordWrap(True); cv2.addWidget(sub)
        self.gloss = QTableWidget(0, 4)
        self.gloss.setHorizontalHeaderLabels(["İngilizce", "Türkçe", "Çevirme", ""])
        gh = self.gloss.horizontalHeader(); gh.setSectionResizeMode(QHeaderView.Stretch)
        gh.setSectionResizeMode(3, QHeaderView.Fixed); self.gloss.setColumnWidth(3, 80)
        gh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.gloss.verticalHeader().setVisible(False); self.gloss.setShowGrid(False)
        self.gloss.setMinimumHeight(280)
        self.gloss.itemChanged.connect(lambda _: self._gloss_autosave())
        cv2.addWidget(self.gloss)
        r = QHBoxLayout()
        b_add = ibtn("Terim ekle", "plus", "primary"); b_add.clicked.connect(lambda: self._gloss_row("", "", False, edit=True))
        b_imp = ibtn("İçe aktar...", "upload"); b_imp.clicked.connect(self.import_glossary)
        b_exp = ibtn("Dışa aktar...", "download"); b_exp.clicked.connect(self.export_glossary)
        for b in (b_add, b_imp, b_exp):
            r.addWidget(b)
        r.addStretch()
        cv2.addLayout(r)
        v.addWidget(c2)
        self.load_glossary()
        v.addStretch()
        return w

    def load_engine_fields(self):
        k = self.eng.currentData()
        self.model.blockSignals(True)
        self.model.clear(); self.model.addItems(MODELS.get(k, []))
        self.model.setCurrentText(self.s.models.get(k, "")); self.model.setEnabled(k in MODELS)
        self.model.blockSignals(False)
        need_key = k not in ("free", "local")
        self.key.setEnabled(need_key)
        has = bool(self.s.api_keys_enc.get(k))
        self.key.clear()
        self.key.setPlaceholderText("•••••••••••••••••••• (kayıtlı)" if has else
                                    ("Anahtar gerekmez" if not need_key else "API anahtarını yapıştırın"))
        self.test_ok.clear()
        d = local_model_dir()
        self.b_model.setVisible(d is None)
        if k == "local":
            self.model_status.setText("Yerel model: " + ("hazır ✓ (internetsiz, satır başına ~0,1 sn)" if d else
                                                         "bulunamadı — ücretsiz motora geçilecek"))
        else:
            self.model_status.setText("")

    def check_update(self):
        from . import updater
        threading.Thread(target=lambda: (lambda u: u and self.update_found.emit(u))(updater.check()), daemon=True).start()

    def _on_update(self, u: dict):
        from . import updater
        self._upd = u
        self.upd_lbl.setText(f"<b>Yeni sürüm var: {u['version']}</b> — tek tıkla güncelleyin (ayarlarınız korunur).")
        self.upd_bar.show()
        try:
            self.upd_btn.clicked.disconnect()
        except Exception:
            pass

        def go():
            if not updater.frozen():
                QMessageBox.information(self, "Güncelleme", "Kaynak koddan çalışıyorsunuz; güncellemek için yeni zip/kurulumu indirin.")
                return
            self.upd_btn.setEnabled(False)

            def run():
                if updater.install(u["url"], lambda p: self.update_prog.emit(p)):
                    QTimer.singleShot(0, self.ctx.qapp.quit)
            threading.Thread(target=run, daemon=True).start()
        self.upd_btn.clicked.connect(go)

    def download_model(self):
        from .translate import download_model
        self.b_model.setEnabled(False)
        threading.Thread(target=lambda: download_model(lambda p, msg: self.model_prog.emit(p, msg)), daemon=True).start()

    def _model_progress(self, pct, msg):
        self.model_status.setText(f"Yerel model: {msg}")
        if "hazır" in msg or "İndirilemedi" in msg or "başarısız" in msg:
            self.b_model.setEnabled(True)
            self.load_engine_fields() if "hazır" in msg else None
            if "hazır" in msg:
                self.restart_if_running()

    def _save_key(self):
        k = self.eng.currentData()
        if self.key.text().strip():
            self.s.api_keys_enc[k] = keystore.encrypt(self.key.text().strip())
            self.s.save(); self.key.clear(); self.load_engine_fields(); self.restart_if_running()
            log.info("%s anahtarı kaydedildi", k)

    def _save_engine(self, restart: bool = True):
        k = self.eng.currentData()
        self.s.engine = k
        if self.model.isEnabled() and self.model.currentText().strip():
            self.s.models[k] = self.model.currentText().strip()
        self.s.fallback_free = bool(self.fallback.currentData())
        self.s.save()
        if restart:
            self.restart_if_running()

    def test_engine(self):
        k = self.eng.currentData()
        key = self.key.text().strip() or keystore.decrypt(self.s.api_keys_enc.get(k, ""))
        model = self.model.currentText().strip()
        sysmsg = system_prompt(self.ctx.profile.game, self.ctx.profile.glossary, self.s.tone)
        self.test_ok.setPixmap(pixmap("dot", MUTED, 24))

        def run():
            t = time.perf_counter()
            try:
                eng = make_engine(k, key, model)
                out = eng.translate(["Lucia: Where the hell were you? We gotta go, now!"], [], sysmsg)
                self.test_done.emit(True, f"✔ {eng.name} çalışıyor ({(time.perf_counter() - t) * 1000:.0f} ms)\n\n{out[0]}")
            except Exception as e:
                self.test_done.emit(False, f"✘ Hata:\n{e}")

        threading.Thread(target=run, daemon=True).start()

    def _on_test_done(self, ok, msg):
        self.test_ok.setPixmap(pixmap("check" if ok else "cross", ACCENT if ok else "#F87171", 24))
        QMessageBox.information(self, "Bağlantı testi", msg)

    def _set_cat(self, attr, on):
        setattr(self.s, attr, on); self.s.save()
        self.ctx.overlay.zone_items.clear(); self.ctx.tv.clear()
        self.ctx.pipeline.reload_zones()
        log.info("Çevrilecek türler: %s", ", ".join(sorted(self.s.categories())))

    def _gloss_row(self, en, tr, keep, edit=False):
        self.gloss.blockSignals(True)
        r = self.gloss.rowCount(); self.gloss.insertRow(r); self.gloss.setRowHeight(r, 44)
        self.gloss.setItem(r, 0, QTableWidgetItem(en)); self.gloss.setItem(r, 1, QTableWidgetItem(tr))
        mode = QComboBox(); mode.addItems(["Zorla çevir", "Çevirme (koru)"]); mode.setCurrentIndex(1 if keep else 0)
        mode.currentIndexChanged.connect(lambda _: self._gloss_autosave())
        self.gloss.setCellWidget(r, 2, mode)
        act = QWidget(); ah = QHBoxLayout(act); ah.setContentsMargins(0, 0, 0, 0); ah.setSpacing(2)
        be = tool("pencil", "Düzenle"); bd = tool("trash", "Sil")
        be.clicked.connect(lambda _=False, it=self.gloss.item(r, 1): self.gloss.editItem(it))
        bd.clicked.connect(lambda _=False, it=self.gloss.item(r, 0): (self.gloss.removeRow(self.gloss.row(it)), self._gloss_autosave()))
        ah.addWidget(be); ah.addWidget(bd)
        self.gloss.setCellWidget(r, 3, act)
        self.gloss.blockSignals(False)
        if edit:
            self.gloss.scrollToBottom(); self.gloss.editItem(self.gloss.item(r, 0))

    def load_glossary(self):
        if not hasattr(self, "gloss"):
            return
        self.gloss.blockSignals(True); self.gloss.setRowCount(0); self.gloss.blockSignals(False)
        for en, tr in self.ctx.profile.glossary.items():
            self._gloss_row(en, tr or en, not tr)

    def _collect_glossary(self) -> dict:
        g = {}
        for r in range(self.gloss.rowCount()):
            en = self.gloss.item(r, 0); tr = self.gloss.item(r, 1); mode = self.gloss.cellWidget(r, 2)
            if en and en.text().strip():
                keep = mode is not None and mode.currentIndex() == 1
                g[en.text().strip()] = "" if keep else (tr.text().strip() if tr else "")
        return g

    def _save_style(self):
        self.ctx.profile.style = self.style_edit.toPlainText().strip()
        self._gloss_autosave()

    def _gloss_autosave(self):
        self.ctx.profile.glossary = self._collect_glossary()
        save_profile(self.ctx.profile)
        if self.ctx.pipeline.manager:
            from .translate import system_prompt as sp
            self.ctx.pipeline.manager.sys = sp(self.ctx.profile.game, self.ctx.profile.glossary, self.s.tone,
                                               self.ctx.profile.style)

    def import_glossary(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Sözlük içe aktar", "", "JSON (*.json)")
        if fn:
            try:
                for en, tr in json.loads(Path(fn).read_text(encoding="utf-8")).items():
                    self._gloss_row(en, tr or en, not tr)
                self._gloss_autosave()
            except Exception as e:
                QMessageBox.warning(self, "İçe aktarılamadı", str(e))

    def export_glossary(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Sözlüğü dışa aktar", "sozluk.json", "JSON (*.json)")
        if fn:
            Path(fn).write_text(json.dumps(self._collect_glossary(), ensure_ascii=False, indent=2), encoding="utf-8")

    def restart_if_running(self):
        p = self.ctx.pipeline
        if p.running.is_set():
            p.stop(); p.start()
        self.sync_run_buttons()

    # ================================================================ Görünüm
    def _page_look(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(18)
        v.addWidget(page_header("Görünüm", "Canlı çeviri altyazılarının ekranda nasıl görüneceğini özelleştirin.", "monitor"))
        c, cv = card("Altyazı görünümü")
        h = QHBoxLayout(); h.setSpacing(22)
        self.look_prev = LookPreview(self.ctx)
        h.addWidget(self.look_prev, 3)
        f = QGridLayout(); f.setVerticalSpacing(14); f.setHorizontalSpacing(12)
        self.fsize = QComboBox()
        for val, t in ((1.0, "Birebir (oyunla aynı)"), (0.9, "%90"), (1.1, "%110"), (1.2, "%120"), (1.35, "%135"), (1.5, "%150")):
            self.fsize.addItem(t, val)
        idx = min(range(self.fsize.count()), key=lambda i: abs(self.fsize.itemData(i) - self.s.font_scale))
        self.fsize.setCurrentIndex(idx)
        self.fsize.currentIndexChanged.connect(lambda _: self._look("font_scale", self.fsize.currentData()))
        from .fonts import available
        self.font_combo = QComboBox()
        for k, t in available().items():
            self.font_combo.addItem(t, k)
        self.font_combo.setCurrentIndex(max(0, self.font_combo.findData(self.s.font_choice)))
        self.font_combo.currentIndexChanged.connect(lambda _: self._look("font_choice", self.font_combo.currentData()))
        self.font_combo.setToolTip("Türkçe yazının yazı tipi. 'Oyun stili (dar)' oyun altyazılarına en çok benzeyenidir.")
        f.addWidget(QLabel("Metin boyutu"), 0, 0); f.addWidget(self.fsize, 0, 1)
        self.spk_btn = self._color_btn("speaker_color")
        f.addWidget(QLabel("Konuşmacı rengi"), 1, 0); f.addWidget(self.spk_btn, 1, 1)
        f.addWidget(sep(), 2, 0, 1, 2)
        f.addWidget(QLabel("<b>Altyazı kutusu (siyah)</b>"), 3, 0, 1, 2)
        self.opac = QSpinBox(); self.opac.setRange(10, 100); self.opac.setPrefix("%")
        self.opac.setValue(round(self.s.box_opacity / 2.55))
        self.opac.valueChanged.connect(lambda val: self._look("box_opacity", round(val * 2.55)))
        f.addWidget(QLabel("Opaklık"), 4, 0); f.addWidget(self.opac, 4, 1)
        f.addWidget(sep(), 5, 0, 1, 2)
        f.addWidget(QLabel("<b>Görüntüleme modu</b>"), 6, 0, 1, 2)
        self.mode_grp = QButtonGroup(self)
        cur = self._cur_mode()
        for i, (key, t, d) in enumerate((("black", "Opak kutu", "Yüksek okunurluk (önerilen)."),
                                         ("semi", "Yarı saydam", "Arka planı kısmen gösterir."),
                                         ("none", "Altında göster", "Sadece metin; kutu yok."),
                                         ("game", "Oyun rengi", "Kutu, yazının arkasındaki oyun renginde."))):
            rb = QRadioButton(); rb.setChecked(cur == key)
            rb.toggled.connect(lambda on, k=key: on and self._set_mode(k))
            self.mode_grp.addButton(rb, i)
            cell = QHBoxLayout(); cell.addWidget(rb)
            col = QVBoxLayout(); col.setSpacing(0)
            tl = QLabel(f"<b>{t}</b>"); dl = QLabel(d); dl.setObjectName("muted")
            col.addWidget(tl); col.addWidget(dl); cell.addLayout(col); cell.addStretch()
            f.addLayout(cell, 7 + i, 0, 1, 2)
        f.setRowStretch(12, 1)
        fw = QWidget(); fw.setLayout(f); fw.setFixedWidth(330)
        h.addWidget(fw)
        cv.addLayout(h)
        v.addWidget(c)

        c2, cv2 = card("Ayrıntılar")
        g = QGridLayout(); g.setHorizontalSpacing(18); g.setVerticalSpacing(12)
        self.mcol = Toggle(self.s.match_colors); self.mcol.toggled.connect(lambda b: self._look("match_colors", b))
        self.spk = Toggle(self.s.show_speaker); self.spk.toggled.connect(lambda b: self._look("show_speaker", b))
        g.addWidget(self.mcol, 0, 0); g.addWidget(QLabel("Yazı rengini oyundaki İngilizceden al (beyaz yazı beyaz, sarı yazı sarı)"), 0, 1)
        g.addWidget(self.spk, 1, 0); g.addWidget(QLabel("Konuşan kişinin adını göster (ör. Lucia:)"), 1, 1)
        g.addWidget(QLabel("Yazı rengi"), 0, 2); g.addWidget(self._color_btn("text_color"), 0, 3)
        g.addWidget(QLabel("Kutu rengi"), 1, 2); g.addWidget(self._color_btn("box_color"), 1, 3)
        g.addWidget(QLabel("Yazı tipi"), 2, 2); g.addWidget(self.font_combo, 2, 3)
        fhint = QLabel("Ek yazı tipleri (Oyun stili, Yuvarlak, Sade) yüklüyse listede görünür; TV'de de aynı yazı tipi kullanılır.")
        fhint.setObjectName("muted"); fhint.setWordWrap(True); g.addWidget(fhint, 2, 0, 1, 2)
        g.setColumnStretch(1, 1)
        cv2.addLayout(g)
        v.addWidget(c2)

        c3, cv3 = card("Konuşmacı renkleri", "message")
        r3 = QHBoxLayout()
        self.spk_on = Toggle(self.s.speaker_colors_on); self.spk_on.toggled.connect(lambda b: self._look("speaker_colors_on", b))
        r3.addWidget(self.spk_on); r3.addWidget(QLabel("Her konuşmacının adı kendi renginde görünsün (ör. Lucia pembe, Jason mavi). "
                                                         "Listede olmayanlara otomatik renk verilir.")); r3.addStretch()
        cv3.addLayout(r3)
        self.spk_table = QTableWidget(0, 3); self.spk_table.setHorizontalHeaderLabels(["Konuşmacı", "Renk", ""])
        sh = self.spk_table.horizontalHeader(); sh.setSectionResizeMode(QHeaderView.Stretch)
        sh.setSectionResizeMode(2, QHeaderView.Fixed); self.spk_table.setColumnWidth(2, 50)
        sh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.spk_table.verticalHeader().setVisible(False); self.spk_table.setShowGrid(False); self.spk_table.setFixedHeight(190)
        self.spk_table.itemChanged.connect(lambda _: self._save_speakers())
        cv3.addWidget(self.spk_table)
        b_sp = ibtn("Konuşmacı ekle", "plus", "primary"); b_sp.clicked.connect(lambda: self._spk_row("Yeni", "#7CFFB2", edit=True))
        cv3.addWidget(b_sp, 0, Qt.AlignLeft)
        self.load_speakers()
        v.addWidget(c3)

        c4, cv4 = card("Türkçe seslendirme", "volume")
        from .tts import available_voices
        voices = available_voices()
        r4 = QHBoxLayout()
        self.tts_on = Toggle(self.s.tts_enabled); self.tts_on.toggled.connect(lambda b: (setattr(self.s, "tts_enabled", b), self.s.save()))
        r4.addWidget(self.tts_on)
        r4.addWidget(QLabel("Konuşmaları Türkçe sesle oku (bilgisayarın hoparlöründen)" +
                            (f" — ses: {voices[0]}" if voices else " — Türkçe ses bulunamadı (Windows Ayarlar → Konuşma)")))
        r4.addStretch()
        cv4.addLayout(r4)
        r5 = QHBoxLayout(); r5.addWidget(QLabel("Konuşma hızı"))
        rate = QSlider(Qt.Horizontal); rate.setRange(70, 200); rate.setValue(int(self.s.tts_rate * 100)); rate.setFixedWidth(260)
        rl = QLabel(f"{self.s.tts_rate:.2f}×")
        rate.valueChanged.connect(lambda val: (setattr(self.s, "tts_rate", val / 100), rl.setText(f"{val / 100:.2f}×"), self.s.save()))
        b_t = ibtn("Dene", "play", "outlineGreen"); b_t.clicked.connect(self._tts_test)
        r5.addWidget(rate); r5.addWidget(rl); r5.addSpacing(12); r5.addWidget(b_t); r5.addStretch()
        cv4.addLayout(r5)
        v.addWidget(c4)
        v.addStretch()
        return w

    def _tts_test(self):
        t = self.ctx.pipeline.tts
        if t is None:
            return
        was = self.s.tts_enabled
        self.s.tts_enabled = True
        t.say("Nereye gidiyorsun? Hemen gitmemiz lazım!", key=f"test{time.time()}")
        self.s.tts_enabled = was

    def _spk_row(self, name, col, edit=False):
        self.spk_table.blockSignals(True)
        r = self.spk_table.rowCount(); self.spk_table.insertRow(r); self.spk_table.setRowHeight(r, 46)
        self.spk_table.setItem(r, 0, QTableWidgetItem(name))
        b = QPushButton(f"  {col.upper()}"); b.setIcon(self._swatch(col)); b.setProperty("col", col)
        b.setStyleSheet("QPushButton{padding:2px 12px;margin:4px 0;text-align:left;}")   # tablo satırında kırpılmasın

        def pick(_=False, btn=b):
            c = QColorDialog.getColor(QColor(btn.property("col")), self)
            if c.isValid():
                btn.setProperty("col", c.name()); btn.setText(f"  {c.name().upper()}"); btn.setIcon(self._swatch(c.name()))
                self._save_speakers()
        b.clicked.connect(pick)
        self.spk_table.setCellWidget(r, 1, b)
        it0 = self.spk_table.item(r, 0)
        d = tool("trash", "Sil")
        d.clicked.connect(lambda _=False, it=it0: (self.spk_table.removeRow(self.spk_table.row(it)), self._save_speakers()))
        self.spk_table.setCellWidget(r, 2, d)
        self.spk_table.blockSignals(False)
        if edit:
            self.spk_table.editItem(it0); self._save_speakers()

    def load_speakers(self):
        self.spk_table.blockSignals(True); self.spk_table.setRowCount(0); self.spk_table.blockSignals(False)
        for n, c in (self.ctx.profile.speaker_colors or {}).items():
            self._spk_row(n, c)

    def _save_speakers(self):
        d = {}
        for r in range(self.spk_table.rowCount()):
            it = self.spk_table.item(r, 0); b = self.spk_table.cellWidget(r, 1)
            if it and it.text().strip() and b is not None:
                d[it.text().strip()] = b.property("col")
        self.ctx.profile.speaker_colors = d
        save_profile(self.ctx.profile)

    def _cur_mode(self) -> str:
        if self.s.display_mode == "text":
            return "none"
        return self.s.bg_mode if self.s.bg_mode in ("black", "semi", "game", "none") else "black"

    def _set_mode(self, k: str):
        self.s.display_mode = "match"
        self._look("bg_mode", k)

    def _color_btn(self, attr) -> QPushButton:
        b = QPushButton(f"  {getattr(self.s, attr).upper()}")
        b.setIcon(self._swatch(getattr(self.s, attr))); b.setIconSize(QSize(18, 18))
        b.clicked.connect(lambda _=False, a=attr, btn=b: self.pick_color(a, btn))
        return b

    @staticmethod
    def _swatch(col):
        from PySide6.QtGui import QIcon, QPixmap
        pm = QPixmap(18, 18); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QColor(col)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 18, 18, 4, 4); p.end()
        return QIcon(pm)

    def pick_color(self, attr, btn):
        c = QColorDialog.getColor(QColor(getattr(self.s, attr)), self)
        if c.isValid():
            btn.setText(f"  {c.name().upper()}"); btn.setIcon(self._swatch(c.name()))
            self._look(attr, c.name())

    def _look(self, attr, val):
        setattr(self.s, attr, val)
        self.s.save()
        self.ctx.overlay.update(); self.preview.update()
        if hasattr(self, "look_prev"):
            self.look_prev.update()
        self.ctx.tv.send_style()

    # ================================================================ TV
    def _page_tv(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(18)
        v.addWidget(page_header("TV", "Çevirileri Android TV / Google TV'de, PS5'in HDMI görüntüsünün tam üstünde gösterin.", "tv"))
        c, cv = card("Bağlantı")
        st = QHBoxLayout(); self.tv_state_icon = QLabel(); self.tv_state_icon.setPixmap(pixmap("dot", MUTED, 28))
        self.tv_state = QLabel("TV aranıyor…"); self.tv_state.setStyleSheet("font-size:18px;font-weight:700;")
        st.addWidget(self.tv_state_icon); st.addWidget(self.tv_state); st.addStretch()
        cv.addLayout(st)
        orow = QHBoxLayout(); orow.addWidget(QLabel("Çeviri nerede görünsün:"))
        self.out_tv = Segmented(OUTPUTS, self.s.output_target); self.out_tv.changed.connect(self.set_output)
        orow.addWidget(self.out_tv); orow.addStretch()
        cv.addLayout(orow)
        g = QHBoxLayout()
        self.tv_host = QLineEdit(self.s.tv_host); self.tv_host.setPlaceholderText("Boş bırakın: ev ağında otomatik bulunur (ör. 192.168.1.103)")
        b_conn = ibtn("Bağlan", "link", "primary"); b_conn.clicked.connect(self._tv_connect)
        b_scan = ibtn("Yeniden ara", "refresh"); b_scan.clicked.connect(lambda: (self.tv_host.clear(), self.ctx.tv.reconnect()))
        g.addWidget(QLabel("TV adresi")); g.addWidget(self.tv_host, 1); g.addWidget(b_conn); g.addWidget(b_scan)
        cv.addLayout(g)
        v.addWidget(c)

        cc, ccv = card("Hizalama", "target")
        hint = QLabel(
            "Türkçe yazılar TV'de İngilizcenin tam üstüne gelmiyorsa: <b>1)</b> TV'nin görüntü ayarında <b>Ekran boyutu</b>nu "
            "<b>Tam piksel / Just Scan</b> yapın. <b>2)</b> <b>Hizalama modu</b>nu açın; TV'de algılanan İngilizce yazıların çevresinde "
            f"<span style='color:#00E5FF'>mavi çerçeveler</span> çıkar. <b>3)</b> Çerçeveler İngilizcenin üstüne oturana kadar oklarla kaydırın. "
            "Oyun oynarken klavyeden de yapılabilir: <b>Ctrl+Alt+Oklar</b>, <b>Ctrl+Alt+PgUp/PgDn</b> (büyüt/küçült), "
            "<b>Ctrl+Alt+End</b> (modu aç/kapat), <b>Ctrl+Alt+Home</b> (sıfırla).")
        hint.setTextFormat(Qt.RichText); hint.setWordWrap(True); hint.setObjectName("muted"); ccv.addWidget(hint)
        row = QHBoxLayout()
        self.btn_calib = ibtn("Hizalama modunu aç", "target", "primary"); self.btn_calib.setCheckable(True)
        self.btn_calib.toggled.connect(lambda on: self.ctx.calibrate("CAL_MODE") if on != self.ctx.tv.calib else None)
        row.addWidget(self.btn_calib); row.addSpacing(10)
        for ic, act, tip in (("chev_left", "CAL_LEFT", "Sola"), ("chev_up", "CAL_UP", "Yukarı"), ("chev_down", "CAL_DOWN", "Aşağı"),
                             ("chev_right", "CAL_RIGHT", "Sağa"), ("zoom_in", "CAL_BIGGER", "Büyüt"), ("zoom_out", "CAL_SMALLER", "Küçült")):
            b = ibtn("", ic); b.setToolTip(tip); b.setAutoRepeat(True); b.setAutoRepeatInterval(120); b.setFixedWidth(52)
            b.clicked.connect(lambda _=False, a=act: self.ctx.calibrate(a)); row.addWidget(b)
        b_reset = ibtn("Sıfırla", "refresh"); b_reset.clicked.connect(lambda: self.ctx.calibrate("CAL_RESET")); row.addWidget(b_reset)
        row.addStretch()
        ccv.addLayout(row)
        cg = QGridLayout(); self.cal_spins = {}
        for i, (attr, label, lo, hi, step) in enumerate((("tv_dx", "Yatay kaydırma", -10.0, 10.0, 0.1), ("tv_dy", "Dikey kaydırma", -10.0, 10.0, 0.1),
                                                         ("tv_sx", "Yatay ölçek", 80.0, 120.0, 0.5), ("tv_sy", "Dikey ölçek", 80.0, 120.0, 0.5))):
            sp = QDoubleSpinBox(); sp.setRange(lo, hi); sp.setSingleStep(step); sp.setDecimals(1); sp.setSuffix(" %")
            sp.setValue(getattr(self.s, attr)); sp.valueChanged.connect(lambda val, a=attr: self._look(a, round(val, 2)))
            self.cal_spins[attr] = sp
            cg.addWidget(QLabel(label), i // 2, (i % 2) * 2); cg.addWidget(sp, i // 2, (i % 2) * 2 + 1)
        ccv.addLayout(cg)
        v.addWidget(cc)

        c2, cv2 = card("TV'ye kurulum (bir kere)", "download")
        txt = QLabel(
            "1. TV'de Google Play'den <b>Downloader</b> uygulamasını kurun ve bilinmeyen uygulamalara izin verin.<br>"
            "2. Downloader'a <b>github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk</b> yazıp kurun "
            "(aynı dosya: <i>TRCeviri-TV.apk</i>).<br>"
            "3. TV'de <b>Brolis Game Translate (TV)</b>'yi bir kez açın, <b>ekran üstünde gösterme</b> iznini verin, <b>Oyuna dön</b>'e basın.<br>"
            "4. Uygulama TV her açıldığında kendiliğinden başlar; bilgisayardaki Brolis Game Translate (TV)'yi kendisi bulur.<br>"
            "Bilgisayar ve TV <b>aynı modeme</b> bağlı olmalı.")
        txt.setTextFormat(Qt.RichText); txt.setWordWrap(True); cv2.addWidget(txt)
        b_apk = ibtn("APK dosyasının klasörünü aç", "folder"); b_apk.clicked.connect(lambda: os.startfile(str(APK.parent)))
        cv2.addWidget(b_apk, 0, Qt.AlignLeft)
        v.addWidget(c2)
        v.addStretch()
        return w

    def sync_calib(self):
        for attr, sp in getattr(self, "cal_spins", {}).items():
            sp.blockSignals(True); sp.setValue(getattr(self.s, attr)); sp.blockSignals(False)
        if hasattr(self, "btn_calib"):
            self.btn_calib.blockSignals(True); self.btn_calib.setChecked(self.ctx.tv.calib)
            self.btn_calib.setText("  Hizalama modunu kapat" if self.ctx.tv.calib else "  Hizalama modunu aç")
            self.btn_calib.blockSignals(False)

    def _tv_connect(self):
        self.s.tv_host = self.tv_host.text().strip(); self.s.save()
        self.ctx.tv.host = None
        self.ctx.tv._put({"t": "__reconnect"})

    # ================================================================ Gelişmiş
    def _page_adv(self) -> QWidget:
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(18)
        v.addWidget(page_header("Gelişmiş", "Performans, kaynak kullanımı ve tanılama seçenekleri.", "settings"))
        c, cv = card("Performans ve tanılama", "activity")
        cols = QHBoxLayout(); cols.setSpacing(28)
        L = QVBoxLayout(); L.setSpacing(14); R = QVBoxLayout(); R.setSpacing(14)

        def row(title, desc, widget):
            box = QHBoxLayout(); box.addWidget(field(title, desc), 1); box.addWidget(widget)
            return box

        fps = QComboBox()
        for fv in (10, 15, 20, 30):
            fps.addItem(f"{fv} FPS", fv)
        fps.setCurrentIndex(min(range(fps.count()), key=lambda i: abs(fps.itemData(i) - self.s.fps))); fps.setFixedWidth(210)
        fps.currentIndexChanged.connect(lambda _: (setattr(self.s, "fps", fps.currentData()), self.s.save()))
        L.addLayout(row("Yakalama (ekran görüntüsü) hızı", "Daha yüksek değerler akıcılığı artırır, CPU/GPU kullanımını yükseltir.", fps))
        L.addWidget(sep())
        thr = QComboBox()
        for n in (1, 2, 4, 6, 8):
            thr.addItem(str(n), n)
        thr.setCurrentIndex(max(0, thr.findData(self.s.ocr_threads))); thr.setFixedWidth(210)
        thr.currentIndexChanged.connect(lambda _: (setattr(self.s, "ocr_threads", thr.currentData()), self.s.save(), self.restart_if_running()))
        L.addLayout(row("OCR işçisi (eşzamanlı)", "Aynı anda çalışan OCR iş parçacığı sayısı. Çoğu sistem için 4 yeterlidir.", thr))
        L.addWidget(sep())
        dml = Toggle(self.s.use_gpu); self.dml_lbl = QLabel("Açık" if self.s.use_gpu else "Kapalı")
        dml.toggled.connect(lambda b: (setattr(self.s, "use_gpu", b), self.s.save(), self.dml_lbl.setText("Açık" if b else "Kapalı"),
                                       self.restart_if_running()))
        dw = QWidget(); dh = QHBoxLayout(dw); dh.setContentsMargins(0, 0, 0, 0); dh.addWidget(dml); dh.addWidget(self.dml_lbl)
        L.addLayout(row("DirectML hızlandırma", "Uygun GPU'nuz varsa OCR'ı GPU'da çalıştırır (Windows 10/11).", dw))
        L.addWidget(sep())
        scan = QComboBox()
        for px, t in ((800, "800 px · hızlı"), (960, "960 px · dengeli"), (1280, "1280 px · küçük yazılar"), (1600, "1600 px · en hassas")):
            scan.addItem(t, px)
        scan.setCurrentIndex(max(0, scan.findData(self.s.auto_scan_width))); scan.setFixedWidth(210)
        scan.currentIndexChanged.connect(lambda _: (setattr(self.s, "auto_scan_width", scan.currentData()), self.s.save(), self.restart_if_running()))
        L.addLayout(row("Tarama çözünürlüğü", "Küçük yazıları kaçırıyorsa artırın.", scan))

        thr2 = QHBoxLayout()
        sl = QSlider(Qt.Horizontal); sl.setRange(5, 100); sl.setValue(int(min(100, self.s.change_threshold * 10)))
        spv = QSpinBox(); spv.setRange(5, 100); spv.setPrefix("%"); spv.setValue(sl.value()); spv.setFixedWidth(90)
        sl.valueChanged.connect(spv.setValue); spv.valueChanged.connect(sl.setValue)
        sl.valueChanged.connect(lambda val: (setattr(self.s, "change_threshold", val / 10), self.s.save()))
        thr2.addWidget(sl, 1); thr2.addWidget(spv)
        R.addWidget(field("Değişim eşiği", "Aynı metnin gereksiz yere yeniden çevrilmesini önler. Düşük değer daha hassastır."))
        R.addLayout(thr2)
        R.addWidget(sep())
        lvl = QComboBox(); lvl.addItems(["Bilgi", "Ayrıntılı", "Sadece hatalar"]); lvl.setFixedWidth(260)
        lvl.currentIndexChanged.connect(lambda i: logging.getLogger().setLevel([logging.INFO, logging.DEBUG, logging.WARNING][i]))
        R.addLayout(row("Günlük seviyesi", "Uygulama günlüklerinin ayrıntı düzeyi.", lvl))
        R.addWidget(sep())
        cache_l = QLabel(); cache_l.setObjectName("muted")

        def upd():
            try:
                cache_l.setText(f"Boyut: {CACHE_FILE.stat().st_size / 1e6:.1f} MB")
            except Exception:
                cache_l.setText("Boyut: –")
        upd()
        ch = QHBoxLayout(); ch.addWidget(iconlabel("database", TEXT, 22))
        ch.addWidget(field("Önbellek", "OCR ve çeviri sonuçlarını geçici olarak saklar."), 1)
        ch.addWidget(cache_l)
        b_exp = ibtn("Dışa aktar...", "download", "outlineGreen"); b_exp.clicked.connect(self._export_cache)
        b_clr = ibtn("Temizle", "trash", "danger", PURPLE); b_clr.clicked.connect(lambda: (self.ctx.cache.clear(), upd(), log.info("Önbellek temizlendi")))
        ch.addWidget(b_exp); ch.addWidget(b_clr)
        R.addLayout(ch)
        cols.addLayout(L, 1); cols.addWidget(sep(True)); cols.addLayout(R, 1)
        cv.addLayout(cols)
        v.addWidget(c)

        c2, cv2 = card("Algılama", "scan")
        g = QGridLayout(); g.setHorizontalSpacing(14); g.setVerticalSpacing(12)
        self.auto_toggle = Toggle(self.s.auto_mode); self.auto_toggle.toggled.connect(self.set_auto)
        g.addWidget(self.auto_toggle, 0, 0); g.addWidget(QLabel("Otomatik mod: tüm ekranı tara (kapalıysa sadece Bölgeler sayfasındaki alanlar)"), 0, 1)
        rest = Toggle(self.s.auto_restore); rest.toggled.connect(lambda b: (setattr(self.s, "auto_restore", b), self.s.save()))
        g.addWidget(rest, 1, 0); g.addWidget(QLabel("Remote Play küçültülürse arka planda geri aç (okumaya devam et)"), 1, 1)
        r169 = Toggle(self.s.force_16_9); r169.toggled.connect(lambda b: (setattr(self.s, "force_16_9", b), self.s.save()))
        g.addWidget(r169, 2, 0); g.addWidget(QLabel("Pencerede siyah bant varsa 16:9 oyun alanını kullan"), 2, 1)
        self.dbg_chk = Toggle(self.s.debug_boxes); self.dbg_chk.toggled.connect(lambda b: self._look("debug_boxes", b))
        g.addWidget(self.dbg_chk, 3, 0); g.addWidget(QLabel("Bölge çerçevelerini bilgisayar ekranında göster (F7)"), 3, 1)
        from . import updater, __version__
        auto = Toggle(updater.autostart_enabled())
        auto.toggled.connect(lambda b: (updater.set_autostart(b), log.info("Windows ile başlat: %s", "açık" if b else "kapalı")))
        g.addWidget(auto, 4, 0); g.addWidget(QLabel("Windows açılınca Brolis Game Translate'yi başlat ve canlı çeviriyi aç"), 4, 1)
        vr = QHBoxLayout(); vl = QLabel(f"Sürüm {__version__}"); vl.setObjectName("muted"); vr.addWidget(vl)
        bu = ibtn("Güncellemeleri denetle", "refresh"); bu.clicked.connect(self._manual_update); vr.addWidget(bu); vr.addStretch()
        g.addLayout(vr, 5, 0, 1, 2)
        g.setColumnStretch(1, 1)
        cv2.addLayout(g)
        v.addWidget(c2)

        c3, cv3 = card("Kayıtlar", "list")
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumBlockCount(600)
        self.log_view.setMinimumHeight(200)
        cv3.addWidget(self.log_view)
        v.addWidget(c3)
        v.addStretch()
        return w

    def _manual_update(self):
        from . import updater

        def run():
            u = updater.check()
            if u:
                self.update_found.emit(u)
            else:
                self.test_done.emit(True, "Brolis Game Translate güncel ✓")
        threading.Thread(target=run, daemon=True).start()

    def _export_cache(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Önbelleği dışa aktar", "ceviriler.json", "JSON (*.json)")
        if fn:
            rows = self.ctx.cache.db.execute("SELECT src, dst FROM tr").fetchall()
            Path(fn).write_text(json.dumps(dict(rows), ensure_ascii=False, indent=2), encoding="utf-8")

    # ================================================================ diğer
    def open_help(self):
        if GUIDE.exists():
            os.startfile(str(GUIDE))

    def closeEvent(self, e):
        self.ctx.shutdown()
        e.accept()
