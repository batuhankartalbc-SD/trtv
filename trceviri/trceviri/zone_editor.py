"""Dondurulmuş kare üstünde bölge çizme / taşıma / boyutlandırma."""
from __future__ import annotations

import copy

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .config import ZONE_TYPES, Profile, Zone

COLORS = {"subtitle": "#FFD54A", "objective": "#66BB6A", "phone": "#42A5F5", "help": "#AB47BC",
          "menu": "#FF7043", "free": "#26C6DA"}
HANDLE = 10


class Canvas(QWidget):
    selected = Signal(int)
    changed = Signal()

    def __init__(self, zones: list[Zone]):
        super().__init__()
        self.zones = zones
        self.pix: QPixmap | None = None
        self.sel = -1
        self.drag_mode = None
        self.drag_start = QPointF()
        self.orig: tuple | None = None
        self.setMinimumSize(800, 450)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_frame(self, bgr: np.ndarray | None) -> None:
        if bgr is None:
            self.pix = None
        else:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            self.pix = QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())
        self.update()

    def area(self) -> QRectF:
        W, H = self.width(), self.height()
        if W * 9 > H * 16:
            w = H * 16 / 9
            return QRectF((W - w) / 2, 0, w, H)
        h = W * 9 / 16
        return QRectF(0, (H - h) / 2, W, h)

    def zrect(self, z: Zone) -> QRectF:
        a = self.area()
        return QRectF(a.x() + z.x * a.width(), a.y() + z.y * a.height(), z.w * a.width(), z.h * a.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1b1b1f"))
        a = self.area()
        if self.pix:
            p.drawPixmap(a.toRect(), self.pix)
        else:
            p.setPen(QColor("#888"))
            p.drawText(a, Qt.AlignCenter, "Kare yok — Remote Play açıkken 'Kareyi yakala'ya basın.\nYine de bölge çizebilirsiniz.")
            p.drawRect(a)
        for i, z in enumerate(self.zones):
            r = self.zrect(z)
            c = QColor(COLORS.get(z.type, "#fff"))
            if not z.enabled:
                c.setAlpha(110)
            p.setPen(QPen(c, 3 if i == self.sel else 2, Qt.SolidLine if z.enabled else Qt.DashLine))
            fill = QColor(c); fill.setAlpha(45 if i == self.sel else 20)
            p.setBrush(fill)
            p.drawRect(r)
            p.setPen(c)
            p.drawText(r.adjusted(4, 2, 0, 0), Qt.AlignLeft | Qt.AlignTop, f"{z.name} ({ZONE_TYPES.get(z.type, z.type)})")
            if i == self.sel:
                p.setBrush(c)
                p.drawRect(QRectF(r.right() - HANDLE, r.bottom() - HANDLE, HANDLE, HANDLE))
        p.end()

    def _hit(self, pos: QPointF):
        for i in reversed(range(len(self.zones))):
            r = self.zrect(self.zones[i])
            if QRectF(r.right() - HANDLE * 1.5, r.bottom() - HANDLE * 1.5, HANDLE * 2, HANDLE * 2).contains(pos):
                return i, "resize"
            if r.contains(pos):
                return i, "move"
        return -1, "new"

    def mousePressEvent(self, e):
        pos = e.position()
        i, mode = self._hit(pos)
        a = self.area()
        if mode == "new":
            if not a.contains(pos):
                return
            z = Zone(name=f"Bölge {len(self.zones) + 1}", type="free",
                     x=(pos.x() - a.x()) / a.width(), y=(pos.y() - a.y()) / a.height(), w=0.001, h=0.001)
            self.zones.append(z)
            i, mode = len(self.zones) - 1, "resize"
        self.sel = i
        self.drag_mode = mode
        self.drag_start = pos
        z = self.zones[i]
        self.orig = (z.x, z.y, z.w, z.h)
        self.selected.emit(i)
        self.update()

    def mouseMoveEvent(self, e):
        if self.drag_mode is None or self.sel < 0:
            return
        a = self.area()
        dx = (e.position().x() - self.drag_start.x()) / a.width()
        dy = (e.position().y() - self.drag_start.y()) / a.height()
        z = self.zones[self.sel]
        ox, oy, ow, oh = self.orig
        if self.drag_mode == "move":
            z.x = min(max(0.0, ox + dx), 1 - z.w)
            z.y = min(max(0.0, oy + dy), 1 - z.h)
        else:
            z.w = min(max(0.01, ow + dx), 1 - z.x)
            z.h = min(max(0.01, oh + dy), 1 - z.y)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.sel >= 0 and self.drag_mode:
            z = self.zones[self.sel]
            if z.w < 0.02 or z.h < 0.015:
                z.w, z.h = max(z.w, 0.2), max(z.h, 0.06)
        self.drag_mode = None
        self.changed.emit()
        self.update()


class ZoneEditor(QDialog):
    def __init__(self, profile: Profile, grab_frame, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Bölge düzenleyici — {profile.name}")
        self.resize(1300, 720)
        self.profile = profile
        self.zones = copy.deepcopy(profile.zones)
        self.grab_frame = grab_frame
        self.canvas = Canvas(self.zones)
        self.list = QListWidget()
        self.name = QLineEdit()
        self.type = QComboBox()
        for k, v in ZONE_TYPES.items():
            self.type.addItem(v, k)
        self.enabled = QCheckBox("Etkin")
        self.conf = QDoubleSpinBox(); self.conf.setRange(0.3, 0.99); self.conf.setSingleStep(0.05)
        self.scale = QDoubleSpinBox(); self.scale.setRange(0.5, 2.5); self.scale.setSingleStep(0.1)

        form = QFormLayout()
        form.addRow("Ad", self.name)
        form.addRow("Tür", self.type)
        form.addRow("", self.enabled)
        form.addRow("En düşük OCR güveni", self.conf)
        form.addRow("Yazı boyutu çarpanı", self.scale)
        b_grab = QPushButton("Kareyi yakala")
        b_del = QPushButton("Seçili bölgeyi sil")
        b_save = QPushButton("Kaydet")
        b_save.setDefault(True)
        b_cancel = QPushButton("Vazgeç")
        side = QVBoxLayout()
        side.addWidget(QLabel("Boş alanda sürükleyerek yeni bölge çizin.\nKutuyu sürükleyip taşıyın, sağ alt köşeden boyutlandırın."))
        side.addWidget(self.list)
        side.addLayout(form)
        side.addWidget(b_grab)
        side.addWidget(b_del)
        side.addStretch()
        row = QHBoxLayout(); row.addWidget(b_cancel); row.addWidget(b_save)
        side.addLayout(row)
        sw = QWidget(); sw.setLayout(side); sw.setFixedWidth(330)
        lay = QHBoxLayout(self)
        lay.addWidget(self.canvas, 1)
        lay.addWidget(sw)

        b_grab.clicked.connect(self.grab)
        b_del.clicked.connect(self.delete)
        b_save.clicked.connect(self.accept)
        b_cancel.clicked.connect(self.reject)
        self.canvas.selected.connect(self.select)
        self.canvas.changed.connect(self.refresh_list)
        self.list.currentRowChanged.connect(self.select_from_list)
        self.name.textEdited.connect(lambda t: self._set("name", t))
        self.type.currentIndexChanged.connect(lambda _: self._set("type", self.type.currentData()))
        self.enabled.toggled.connect(lambda v: self._set("enabled", v))
        self.conf.valueChanged.connect(lambda v: self._set("min_confidence", round(v, 2)))
        self.scale.valueChanged.connect(lambda v: self._set("font_scale", round(v, 2)))
        self.refresh_list()
        self.grab()

    def grab(self):
        try:
            self.canvas.set_frame(self.grab_frame())
        except Exception as e:
            QMessageBox.warning(self, "Kare alınamadı", str(e))

    def refresh_list(self):
        cur = self.canvas.sel
        self.list.blockSignals(True)
        self.list.clear()
        for z in self.zones:
            self.list.addItem(("✓ " if z.enabled else "✗ ") + f"{z.name} — {ZONE_TYPES.get(z.type, z.type)}")
        self.list.setCurrentRow(cur)
        self.list.blockSignals(False)
        self.select(cur)

    def select_from_list(self, i):
        self.canvas.sel = i
        self.canvas.update()
        self.select(i)

    def select(self, i):
        has = 0 <= i < len(self.zones)
        for w in (self.name, self.type, self.enabled, self.conf, self.scale):
            w.setEnabled(has)
            w.blockSignals(True)
        if has:
            z = self.zones[i]
            self.name.setText(z.name)
            self.type.setCurrentIndex(max(0, self.type.findData(z.type)))
            self.enabled.setChecked(z.enabled)
            self.conf.setValue(z.min_confidence)
            self.scale.setValue(z.font_scale)
            if self.list.currentRow() != i:
                self.list.blockSignals(True); self.list.setCurrentRow(i); self.list.blockSignals(False)
        for w in (self.name, self.type, self.enabled, self.conf, self.scale):
            w.blockSignals(False)

    def _set(self, attr, val):
        i = self.canvas.sel
        if 0 <= i < len(self.zones):
            setattr(self.zones[i], attr, val)
            self.canvas.update()
            item = self.list.item(i)
            z = self.zones[i]
            if item:
                item.setText(("✓ " if z.enabled else "✗ ") + f"{z.name} — {ZONE_TYPES.get(z.type, z.type)}")

    def delete(self):
        i = self.canvas.sel
        if 0 <= i < len(self.zones):
            del self.zones[i]
            self.canvas.sel = -1
            self.refresh_list()
            self.canvas.update()

    def result_zones(self) -> list[Zone]:
        return self.zones
