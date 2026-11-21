"""Bölge düzenleyici sayfası (tasarım: üst araç çubuğu, kare üstünde bölgeler, sağda özellikler, altta tablo + profil)."""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .config import ZONE_TYPES, Profile, Zone, list_profiles, load_profile, save_profile
from .icons import pixmap
from .theme import ACCENT, MUTED, PURPLE
from .widgets import card, ibtn, iconlabel, sep, tool, Toggle
from .zone_editor import Canvas

log = logging.getLogger("bolgeler")
REF_W, REF_H = 1920, 1080
TYPE_ICON = {"subtitle": "message", "help": "help", "phone": "phone", "objective": "flag", "menu": "list", "free": "zones"}
TYPE_LABEL = {"subtitle": "Altyazı", "help": "Yardım / İpucu", "phone": "Arayüz (Telefon)", "objective": "Görev",
              "menu": "Menü", "free": "Serbest"}


class ChipCanvas(Canvas):
    """Bölgeleri tasarımdaki gibi kesikli çerçeve + mor etiketle çizer."""

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        a = self.area()
        path = QPainterPath(); path.addRoundedRect(a, 12, 12); p.setClipPath(path)
        if self.pix:
            p.drawPixmap(a.toRect(), self.pix)
        else:
            p.fillRect(a, QColor("#0D1319"))
            p.setPen(QColor(MUTED))
            p.drawText(a, Qt.AlignCenter, "Oyun görüntüsü yok — PS Remote Play açık ve bağlıyken 'Kareyi yenile'ye basın.\n"
                                          "Yine de fareyle sürükleyerek bölge çizebilirsiniz.")
        p.setClipping(False)
        f = QFont(); f.setPixelSize(12)
        for i, z in enumerate(self.zones):
            r = self.zrect(z)
            sel = i == self.sel
            col = QColor(ACCENT) if sel else QColor("#E6E0FF")
            if not z.enabled:
                col.setAlpha(120)
            p.setPen(QPen(col, 2.5 if sel else 1.6, Qt.SolidLine if sel else Qt.DashLine))
            fill = QColor(col); fill.setAlpha(28 if sel else 10); p.setBrush(fill)
            p.drawRect(r)
            # etiket (chip)
            p.setFont(f)
            label = z.name
            tw = p.fontMetrics().horizontalAdvance(label) + 16
            chip = QRectF(r.left() - 1, r.top() - 20, tw, 20)
            p.setPen(Qt.NoPen); p.setBrush(QColor("#3A2E6B") if not sel else QColor("#1F5C46"))
            p.drawRoundedRect(chip, 6, 6)
            p.setPen(QColor("#EDE7FF") if not sel else QColor("#CFFFE9"))
            p.drawText(chip, Qt.AlignCenter, label)
            if sel:   # köşe tutamaçları
                p.setBrush(QColor(ACCENT)); p.setPen(Qt.NoPen)
                for cx, cy in ((r.left(), r.top()), (r.center().x(), r.top()), (r.right(), r.top()),
                               (r.left(), r.bottom()), (r.center().x(), r.bottom()), (r.right(), r.bottom())):
                    p.drawRect(QRectF(cx - 4, cy - 4, 8, 8))
        p.end()


class ZonesPage(QWidget):
    ocr_done = Signal(str)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.zones: list[Zone] = copy.deepcopy(ctx.profile.zones)
        self.frame: np.ndarray | None = None
        self.frozen = False
        self._ocr = None
        self._busy = False
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(14)

        t = QLabel("Bölge düzenleyici"); t.setObjectName("h1")
        v.addWidget(t)
        self.auto_banner = QFrame(); self.auto_banner.setObjectName("card2")
        ab = QHBoxLayout(self.auto_banner); ab.setContentsMargins(16, 10, 16, 10)
        ab.addWidget(iconlabel("info", ACCENT, 20))
        abl = QLabel("Otomatik mod açık: tüm ekran taranıyor, bu bölgeler şu an kullanılmıyor."); ab.addWidget(abl); ab.addStretch()
        b_use = ibtn("Bölgeleri kullan", None, "outlineGreen"); b_use.clicked.connect(lambda: self.ctx.window.set_auto(False))
        ab.addWidget(b_use)
        v.addWidget(self.auto_banner)

        body = QHBoxLayout(); body.setSpacing(16)
        left = QVBoxLayout(); left.setSpacing(12)
        bar = QFrame(); bar.setObjectName("card")
        bh = QHBoxLayout(bar); bh.setContentsMargins(12, 10, 12, 10); bh.setSpacing(10)
        self.prof = QComboBox(); self.prof.setMinimumWidth(220)
        self._fill_profiles()
        self.prof.currentTextChanged.connect(self._change_profile)
        self.b_freeze = ibtn("Kareyi dondur", "pause"); self.b_freeze.setCheckable(True)
        self.b_freeze.toggled.connect(self._freeze)
        b_add = ibtn("Bölge ekle", "plus"); b_add.clicked.connect(self.add_zone)
        b_save = ibtn("Profili kaydet", "save", "primary"); b_save.clicked.connect(self.save)
        bh.addWidget(self.prof); bh.addWidget(sep(True)); bh.addWidget(self.b_freeze); bh.addStretch()
        bh.addWidget(b_add); bh.addWidget(b_save)
        left.addWidget(bar)
        self.canvas = ChipCanvas(self.zones)
        self.canvas.setMinimumSize(760, 428)
        self.canvas.selected.connect(self.select)
        self.canvas.changed.connect(self._canvas_changed)
        left.addWidget(self.canvas, 1)
        body.addLayout(left, 3)

        # sağ: özellikler
        pc, pv = card()
        pv.setSpacing(10)
        self.p_title = QLabel("Bölge seçin"); self.p_title.setObjectName("cardtitle")
        pv.addWidget(self.p_title); pv.addWidget(sep())
        g = QGridLayout(); g.setVerticalSpacing(10); g.setHorizontalSpacing(12)
        self.p_name = QLineEdit()
        self.p_en = Toggle(True)
        self.p_type = QComboBox()
        for k, lbl in TYPE_LABEL.items():
            self.p_type.addItem(lbl, k)
        self.p_stab = QSpinBox(); self.p_stab.setRange(0, 2000); self.p_stab.setSingleStep(20); self.p_stab.setSuffix(" ms")
        self.p_conf = QSpinBox(); self.p_conf.setRange(30, 99); self.p_conf.setPrefix("%")
        self.p_align = QComboBox(); self.p_align.addItem("Orta", "c"); self.p_align.addItem("Sol", "l"); self.p_align.addItem("Sağ", "r")
        lab = lambda s: (QLabel(s))
        g.addWidget(QLabel("<b>Etkin</b>"), 0, 0); g.addWidget(self.p_en, 0, 1, Qt.AlignRight)
        g.addWidget(lab("Ad:"), 1, 0); g.addWidget(self.p_name, 1, 1)
        g.addWidget(lab("Tür:"), 2, 0); g.addWidget(self.p_type, 2, 1)
        g.addWidget(lab("Kararlılık:"), 3, 0); g.addWidget(self.p_stab, 3, 1)
        g.addWidget(lab("OCR güveni:"), 4, 0); g.addWidget(self.p_conf, 4, 1)
        g.addWidget(lab("Hizalama:"), 5, 0); g.addWidget(self.p_align, 5, 1)
        pv.addLayout(g); pv.addWidget(sep())
        pv.addWidget(QLabel("<b>Konum ve boyut:</b>"))
        g2 = QGridLayout(); g2.setHorizontalSpacing(8)
        self.p_xywh = {}
        for i, k in enumerate("XYWH"):
            sp = QSpinBox(); sp.setRange(0, 1920 if k in "XW" else 1080); sp.setGroupSeparatorShown(True)
            self.p_xywh[k] = sp
            g2.addWidget(QLabel(f"{k}:"), i // 2, (i % 2) * 2); g2.addWidget(sp, i // 2, (i % 2) * 2 + 1)
        pv.addLayout(g2); pv.addWidget(sep())
        pv.addWidget(QLabel("<b>OCR önizlemesi:</b>"))
        self.p_ocr = QLabel("—"); self.p_ocr.setWordWrap(True)
        self.p_ocr.setStyleSheet("background:#0D1319;border:1px solid #263240;border-radius:10px;padding:12px;font-size:15px;")
        self.p_ocr.setMinimumHeight(54)
        pv.addWidget(self.p_ocr)
        pv.addStretch()
        pc.setFixedWidth(340)
        body.addWidget(pc)
        v.addLayout(body, 1)

        # alt: tablo + profil
        bottom = QHBoxLayout(); bottom.setSpacing(16)
        tc, tv = card()
        self.t_title = QLabel("Bölgeler (0)"); self.t_title.setObjectName("cardtitle"); tv.addWidget(self.t_title)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "Ad", "Tür", "Durum", "Konum (X, Y, W, H)", ""])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        for c, w in ((0, 40), (3, 90), (5, 80)):
            hh.setSectionResizeMode(c, QHeaderView.Fixed); self.table.setColumnWidth(c, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.cellClicked.connect(lambda r, c: self.select(r))
        self.table.setMinimumHeight(170)
        tv.addWidget(self.table)
        bottom.addWidget(tc, 3)
        prc, prv = card("Profil")
        self.prof2 = QComboBox(); self._fill_profiles(self.prof2)
        self.prof2.currentTextChanged.connect(lambda n: self.prof.setCurrentText(n))
        b_imp = ibtn("Profili içe aktar", "upload"); b_imp.clicked.connect(self.import_profile)
        b_exp = ibtn("Profili dışa aktar", "download"); b_exp.clicked.connect(self.export_profile)
        b_new = ibtn("Yeni profil", "plus"); b_new.clicked.connect(self.new_profile)
        b_share = ibtn("Arkadaşla paylaş", "upload", "outlineGreen"); b_share.clicked.connect(self.share_profile)
        for w in (self.prof2, b_imp, b_exp, b_share, b_new):
            prv.addWidget(w)
        prv.addStretch()
        prc.setFixedWidth(340)
        bottom.addWidget(prc)
        v.addLayout(bottom)

        # özellik değişiklikleri
        self.p_en.toggled.connect(lambda on: self._set("enabled", on))
        self.p_name.textEdited.connect(lambda t: self._set("name", t))
        self.p_type.currentIndexChanged.connect(lambda _: self._set("type", self.p_type.currentData()))
        self.p_stab.valueChanged.connect(lambda val: self._set("stability_ms", val))
        self.p_conf.valueChanged.connect(lambda val: self._set("min_confidence", round(val / 100, 2)))
        self.p_align.currentIndexChanged.connect(lambda _: self._set("align", self.p_align.currentData()))
        for k, sp in self.p_xywh.items():
            sp.valueChanged.connect(lambda val, kk=k: self._set_geom(kk, val))
        self.ocr_done.connect(self.p_ocr.setText)
        ctx.pipeline.preview.connect(self._live_frame)
        self.refresh()
        self.select(0 if self.zones else -1)
        self.update_banner()

    # ---------- profil
    def _fill_profiles(self, combo=None):
        combo = combo or self.prof
        combo.blockSignals(True); combo.clear(); combo.addItems(list_profiles())
        combo.setCurrentText(self.ctx.profile.name); combo.blockSignals(False)

    def _change_profile(self, name):
        if not name or name == self.ctx.profile.name:
            return
        self.ctx.window.change_profile(name)

    def reload_from_profile(self):
        self.zones[:] = copy.deepcopy(self.ctx.profile.zones)
        self._fill_profiles(); self._fill_profiles(self.prof2)
        self.refresh(); self.select(0 if self.zones else -1)

    def new_profile(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Yeni profil", "Oyun / profil adı:")
        if ok and name.strip():
            p = Profile.from_dict(self.ctx.profile.to_dict()); p.name = p.game = name.strip()
            save_profile(p)
            self._fill_profiles(); self._fill_profiles(self.prof2)
            self.ctx.window.change_profile(p.name)

    def import_profile(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Profil içe aktar", "", "TRÇeviri profili (*.json)")
        if fn:
            try:
                p = Profile.from_dict(json.loads(Path(fn).read_text(encoding="utf-8")))
                save_profile(p)
                self._fill_profiles(); self._fill_profiles(self.prof2)
                self.ctx.window.change_profile(p.name)
            except Exception as e:
                QMessageBox.warning(self, "İçe aktarılamadı", str(e))

    def export_profile(self):
        self._commit()
        fn, _ = QFileDialog.getSaveFileName(self, "Profili dışa aktar", f"{self.ctx.profile.name}.json", "JSON (*.json)")
        if fn:
            Path(fn).write_text(json.dumps(self.ctx.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def share_profile(self):
        """Profili masaüstüne kaydeder; dosyayı arkadaşınıza gönderin, o da 'Profili içe aktar' ile yükler."""
        import ctypes
        self._commit()
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x10, None, 0, buf)      # gerçek masaüstü (OneDrive dahil)
        desk = Path(buf.value or str(Path.home() / "Desktop"))
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.ctx.profile.name)
        f = desk / f"TRCeviri profili - {safe}.json"
        f.write_text(json.dumps(self.ctx.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Paylaş", f"Profil masaüstüne kaydedildi:\n{f.name}\n\nBu dosyayı arkadaşınıza gönderin; "
                                               "o da Bölgeler → Profil → 'Profili içe aktar' ile yükler.")

    # ---------- kare
    def _live_frame(self, img: QImage):
        if not self.frozen and self.isVisible():
            self.canvas.pix = QPixmap.fromImage(img); self.canvas.update()

    def _freeze(self, on):
        self.frozen = on
        self.b_freeze.setText("  Canlıya dön" if on else "  Kareyi dondur")
        if on:
            self.grab()

    def grab(self):
        try:
            self.frame = self.ctx.pipeline.grab_frame()
            self.canvas.set_frame(self.frame)
        except Exception as e:
            log.warning("kare alınamadı: %s", e)

    # ---------- bölgeler
    def add_zone(self):
        z = Zone(name=f"Bölge {len(self.zones) + 1}", type="free", x=0.35, y=0.4, w=0.3, h=0.1)
        self.zones.append(z)
        self.refresh(); self.select(len(self.zones) - 1)

    def delete_zone(self, i):
        if 0 <= i < len(self.zones):
            del self.zones[i]
            self.refresh(); self.select(min(i, len(self.zones) - 1))

    def _canvas_changed(self):
        self.refresh(); self.select(self.canvas.sel)

    def refresh(self):
        self.t_title.setText(f"Bölgeler ({len(self.zones)})")
        self.table.setRowCount(0)
        for i, z in enumerate(self.zones):
            self.table.insertRow(i); self.table.setRowHeight(i, 40)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            name = QWidget(); nh = QHBoxLayout(name); nh.setContentsMargins(8, 0, 0, 0); nh.setSpacing(8)
            nh.addWidget(iconlabel(TYPE_ICON.get(z.type, "zones"), "#C5CED8", 18)); nh.addWidget(QLabel(z.name)); nh.addStretch()
            self.table.setCellWidget(i, 1, name)
            self.table.setItem(i, 2, QTableWidgetItem(TYPE_LABEL.get(z.type, z.type)))
            pill = QLabel("Etkin" if z.enabled else "Pasif"); pill.setObjectName("pill_on" if z.enabled else "pill_off")
            pw = QWidget(); ph = QHBoxLayout(pw); ph.setContentsMargins(6, 0, 0, 0); ph.addWidget(pill); ph.addStretch()
            self.table.setCellWidget(i, 3, pw)
            self.table.setItem(i, 4, QTableWidgetItem(
                f"{round(z.x * REF_W):,}, {round(z.y * REF_H):,}, {round(z.w * REF_W):,}, {round(z.h * REF_H):,}".replace(",", ".")
                .replace(". ", ", ")))
            act = QWidget(); ah = QHBoxLayout(act); ah.setContentsMargins(0, 0, 0, 0); ah.setSpacing(2)
            be = tool("pencil", "Düzenle"); be.clicked.connect(lambda _=False, k=i: self.select(k))
            bd = tool("trash", "Sil"); bd.clicked.connect(lambda _=False, k=i: self.delete_zone(k))
            ah.addWidget(be); ah.addWidget(bd)
            self.table.setCellWidget(i, 5, act)
        self.canvas.update()

    def select(self, i):
        self.canvas.sel = i if 0 <= i < len(self.zones) else -1
        self.canvas.update()
        has = self.canvas.sel >= 0
        widgets = [self.p_en, self.p_name, self.p_type, self.p_stab, self.p_conf, self.p_align, *self.p_xywh.values()]
        for w in widgets:
            w.setEnabled(has); w.blockSignals(True)
        if has:
            z = self.zones[i]
            self.table.selectRow(i)
            self.p_title.setText(z.name)
            self.p_en.setChecked(z.enabled); self.p_en.setPos(1.0 if z.enabled else 0.0)
            self.p_name.setText(z.name)
            self.p_type.setCurrentIndex(max(0, self.p_type.findData(z.type)))
            self.p_stab.setValue(getattr(z, "stability_ms", 120))
            self.p_conf.setValue(round(z.min_confidence * 100))
            self.p_align.setCurrentIndex(max(0, self.p_align.findData(getattr(z, "align", "c"))))
            self.p_xywh["X"].setValue(round(z.x * REF_W)); self.p_xywh["Y"].setValue(round(z.y * REF_H))
            self.p_xywh["W"].setValue(round(z.w * REF_W)); self.p_xywh["H"].setValue(round(z.h * REF_H))
            self.preview_ocr(z)
        else:
            self.p_title.setText("Bölge seçin"); self.p_ocr.setText("—")
        for w in widgets:
            w.blockSignals(False)

    def _set(self, attr, val):
        i = self.canvas.sel
        if 0 <= i < len(self.zones):
            setattr(self.zones[i], attr, val)
            if attr == "name":
                self.p_title.setText(val)
            self.refresh(); self.table.selectRow(i)

    def _set_geom(self, k, val):
        i = self.canvas.sel
        if not (0 <= i < len(self.zones)):
            return
        z = self.zones[i]
        if k == "X": z.x = min(val / REF_W, 1 - z.w)
        if k == "Y": z.y = min(val / REF_H, 1 - z.h)
        if k == "W": z.w = max(0.01, min(val / REF_W, 1 - z.x))
        if k == "H": z.h = max(0.01, min(val / REF_H, 1 - z.y))
        self.refresh(); self.table.selectRow(i)

    def preview_ocr(self, z: Zone):
        if self._busy:
            return
        frame = self.frame
        if frame is None:
            try:
                frame = self.ctx.pipeline.grab_frame()
            except Exception:
                frame = None
        if frame is None:
            self.p_ocr.setText("Kare yok"); return
        H, W = frame.shape[:2]
        crop = np.ascontiguousarray(frame[int(z.y * H):int((z.y + z.h) * H), int(z.x * W):int((z.x + z.w) * W)])
        self.p_ocr.setText("okunuyor…"); self._busy = True

        def run():
            try:
                if self._ocr is None:
                    from .ocr import OcrEngine
                    self._ocr = OcrEngine(False, 2)
                lines = self._ocr.read(crop, z.min_confidence)
                self.ocr_done.emit("\n".join(l.text for l in lines) or "(yazı yok)")
            except Exception as e:
                self.ocr_done.emit(f"okunamadı: {e}")
            finally:
                self._busy = False

        threading.Thread(target=run, daemon=True).start()

    def _commit(self):
        self.ctx.profile.zones = copy.deepcopy(self.zones)

    def save(self):
        self._commit()
        save_profile(self.ctx.profile)
        self.ctx.pipeline.reload_zones()
        log.info("Profil kaydedildi: %s (%d bölge)", self.ctx.profile.name, len(self.zones))

    def update_banner(self):
        self.auto_banner.setVisible(self.ctx.settings.auto_mode)
