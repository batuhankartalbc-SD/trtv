"""Ortak arayüz bileşenleri: kart, başlık, anahtar (toggle), segment seçici, ikonlu düğmeler."""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import Property, QPointF, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from .icons import icon, pixmap
from .theme import ACCENT, BORDER, MUTED, TEXT


LOGO_PNG = __import__("pathlib").Path(__file__).resolve().parent.parent / "assets" / "logo.png"


def brand_icon():
    from PySide6.QtGui import QIcon
    return QIcon(str(LOGO_PNG)) if LOGO_PNG.exists() else icon("logo", ACCENT, 32)


def brand_logo(size: int = 40) -> QLabel:
    """Brolis Game Translate logosu (assets/logo.png)."""
    from PySide6.QtGui import QPixmap
    l = QLabel()
    if LOGO_PNG.exists():
        pm = QPixmap(str(LOGO_PNG)).scaled(size * 2, size * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(2)
        l.setPixmap(pm)
    else:
        l.setPixmap(pixmap("logo", ACCENT, size))
    l.setFixedSize(size + 4, size + 4)
    return l


def ibtn(text: str, ic: str | None = None, obj: str | None = None, color: str = TEXT, size: int = 18) -> QPushButton:
    b = QPushButton(("  " + text) if (ic and text) else text)
    if ic:
        b.setIcon(icon(ic, "#04140D" if obj == "primary" else color, size))
        b.setIconSize(QSize(size, size))
    if obj:
        b.setObjectName(obj)
    b.setCursor(Qt.PointingHandCursor)
    return b


def tool(ic: str, tip: str = "", color: str = "#C5CED8") -> QPushButton:
    b = QPushButton(); b.setObjectName("iconbtn")
    b.setIcon(icon(ic, color, 18)); b.setIconSize(QSize(18, 18)); b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor); b.setFixedSize(30, 30)
    return b


def iconlabel(ic: str, color: str = TEXT, size: int = 22) -> QLabel:
    l = QLabel(); l.setPixmap(pixmap(ic, color, size)); l.setFixedSize(size + 4, size + 4)
    return l


def card(title: str | None = None, ic: str | None = None, obj: str = "card", right: QWidget | None = None):
    f = QFrame(); f.setObjectName(obj)
    v = QVBoxLayout(f); v.setContentsMargins(22, 18, 22, 18); v.setSpacing(12)
    if title:
        h = QHBoxLayout(); h.setSpacing(12)
        if ic:
            h.addWidget(iconlabel(ic, TEXT, 22))
        t = QLabel(title); t.setObjectName("cardtitle"); h.addWidget(t); h.addStretch()
        if right is not None:
            h.addWidget(right)
        v.addLayout(h)
    return f, v


def sep(vertical: bool = False) -> QFrame:
    s = QFrame(); s.setObjectName("vsep" if vertical else "sep")
    return s


def page_header(title: str, sub: str, ic: str) -> QWidget:
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 6); h.setSpacing(16)
    h.addWidget(iconlabel(ic, TEXT, 34))
    col = QVBoxLayout(); col.setSpacing(2)
    t = QLabel(title); t.setObjectName("h2")
    s = QLabel(sub); s.setObjectName("sub")
    col.addWidget(t); col.addWidget(s)
    h.addLayout(col); h.addStretch()
    return w


def field(title: str, desc: str | None = None) -> QWidget:
    w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
    h = QHBoxLayout(); h.setSpacing(8)
    t = QLabel(title); t.setObjectName("field"); h.addWidget(t)
    h.addStretch(); v.addLayout(h)
    if desc:
        d = QLabel(desc); d.setObjectName("muted"); d.setWordWrap(True); v.addWidget(d)
    return w


class Toggle(QAbstractButton):
    """Tasarımdaki yuvarlak anahtar."""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True); self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 1.0 if checked else 0.0
        self.anim = QPropertyAnimation(self, b"pos", self); self.anim.setDuration(140)
        self.toggled.connect(self._animate)
        self.setFixedSize(52, 28)

    def _animate(self, on):
        self.anim.stop(); self.anim.setEndValue(1.0 if on else 0.0); self.anim.start()

    def getPos(self): return self._pos

    def setPos(self, v): self._pos = v; self.update()

    pos = Property(float, getPos, setPos)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        on = QColor(ACCENT); off = QColor("#2B3542")
        c = QColor(int(off.red() + (on.red() - off.red()) * self._pos), int(off.green() + (on.green() - off.green()) * self._pos),
                   int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(Qt.NoPen); p.setBrush(c); p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * self._pos
        p.setBrush(QColor("#FFFFFF") if self._pos > 0.5 else QColor("#C9D1DA"))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d)); p.end()

    def sizeHint(self): return QSize(52, 28)


class Segmented(QWidget):
    """Yan yana seçenek düğmeleri (ör. Çıkış: PC | TV | İkisi)."""
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str, str | None]], current: str):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for i, (key, text, ic) in enumerate(options):
            b = ibtn(text, ic, "seg")
            b.setCheckable(True)
            radius = "10px"
            style = (f"border-top-left-radius:{radius};border-bottom-left-radius:{radius};" if i == 0 else "") + \
                    (f"border-top-right-radius:{radius};border-bottom-right-radius:{radius};" if i == len(options) - 1 else "")
            b.setStyleSheet(style)
            self.group.addButton(b); self.buttons[key] = b; h.addWidget(b)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
        self.set(current)

    def set(self, key: str):
        b = self.buttons.get(key)
        if b:
            b.setChecked(True)


class Sparkline(QWidget):
    def __init__(self, color: str):
        super().__init__()
        self.color = QColor(color)
        self.vals: deque[float] = deque(maxlen=40)
        self.setMinimumSize(140, 36)

    def push(self, v: float):
        self.vals.append(v); self.update()

    def paintEvent(self, _):
        if len(self.vals) < 2:
            return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        lo, hi = min(self.vals), max(self.vals); rng = (hi - lo) or 1
        W, H = self.width(), self.height()
        path = QPainterPath()
        for i, v in enumerate(self.vals):
            pt = QPointF(i * W / (self.vals.maxlen - 1), H - 4 - (v - lo) / rng * (H - 8))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        p.setPen(QPen(self.color, 2)); p.drawPath(path); p.end()


class Metric(QFrame):
    def __init__(self, ic: str, name: str, color: str):
        super().__init__(); self.setObjectName("card")
        h = QHBoxLayout(self); h.setContentsMargins(20, 14, 20, 14); h.setSpacing(14)
        h.addWidget(iconlabel(ic, "#C5CED8", 26))
        col = QVBoxLayout(); col.setSpacing(0)
        n = QLabel(name); n.setStyleSheet("font-weight:600;font-size:15px;")
        self.val = QLabel("–"); self.color = color
        self.val.setTextFormat(Qt.RichText)
        col.addWidget(n); col.addWidget(self.val)
        self.spark = Sparkline(color)
        h.addLayout(col); h.addStretch(); h.addWidget(self.spark)
        self.set(0)

    def set(self, ms: float):
        txt = f"{ms:.0f}" if ms else "–"
        self.val.setText(f"<span style='font-size:28px;font-weight:700;color:{self.color}'>{txt}</span>"
                         f"<span style='font-size:16px;color:{self.color}'> ms</span>")
        if ms:
            self.spark.push(ms)


class StatusRow(QWidget):
    def __init__(self, name: str):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(4, 8, 4, 8)
        col = QVBoxLayout(); col.setSpacing(1)
        self.name = QLabel(name); self.name.setStyleSheet("font-weight:700;font-size:16px;")
        self.msg = QLabel("bekleniyor"); self.msg.setObjectName("muted")
        col.addWidget(self.name); col.addWidget(self.msg)
        self.dot = QLabel()
        h.addLayout(col); h.addStretch(); h.addWidget(self.dot)
        self.set(None, "bekleniyor")

    def set(self, ok: bool | None, msg: str):
        self.msg.setText(msg)
        self.dot.setPixmap(pixmap({True: "check", False: "cross", None: "dot"}[ok],
                                  {True: ACCENT, False: "#F87171", None: MUTED}[ok], 26))
