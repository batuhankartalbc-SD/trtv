"""Remote Play penceresinin üstünde duran, tıklama geçirgen çeviri katmanı."""
from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from . import winutil
from .config import Settings


def phys_to_logical(x: int, y: int, w: int, h: int) -> QRect:
    """Fiziksel ekran pikselini Qt mantıksal koordinatına çevir (karışık DPI dahil)."""
    for s in QGuiApplication.screens():
        dpr = s.devicePixelRatio()
        g = s.geometry()
        pw, ph = int(g.width() * dpr), int(g.height() * dpr)
        if g.x() <= x < g.x() + pw and g.y() <= y < g.y() + ph:
            return QRect(int(g.x() + (x - g.x()) / dpr), int(g.y() + (y - g.y()) / dpr), int(w / dpr), int(h / dpr))
    dpr = QGuiApplication.primaryScreen().devicePixelRatio()
    return QRect(int(x / dpr), int(y / dpr), int(w / dpr), int(h / dpr))


def wrap(text: str, fm: QFontMetricsF, width: float) -> list[str]:
    out: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            trial = f"{cur} {word}".strip()
            if fm.horizontalAdvance(trial) <= width or not cur:
                cur = trial
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
    return out or [""]


def layout_item(text: str, family: str, px: float, box_w: float, box_h: float, min_px: float = 12.0):
    """Metni kutuya sığdır: önce yazı boyutunu küçült, sonra kutuyu büyüt. (font, satırlar, yükseklik)"""
    size = px
    while True:
        f = QFont(family)
        f.setPixelSize(max(1, int(size)))
        fm = QFontMetricsF(f)
        lines = wrap(text, fm, box_w)
        need = len(lines) * fm.lineSpacing()
        if need <= box_h * 1.15 or size <= min_px:
            return f, lines, need
        size -= 1


class Overlay(QWidget):
    def __init__(self, settings: Settings, pipeline):
        super().__init__(None)
        self.settings = settings
        self.pipe = pipeline
        self.zone_items: dict[str, list] = {}
        self.visible_flag = True
        self.setWindowTitle("Brolis Game Translate Katman")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                            | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.capture_excluded = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.follow)
        self.timer.start(100)
        pipeline.items_changed.connect(self.set_items)

    def set_items(self, zone_id: str, items: list) -> None:
        if items:
            self.zone_items[zone_id] = items
        else:
            self.zone_items.pop(zone_id, None)
        self.update()

    def toggle(self) -> None:
        self.visible_flag = not self.visible_flag
        self.follow()

    def follow(self) -> None:
        r = self.pipe.content_rect
        if not r or not self.visible_flag or not self.settings.output_pc:
            if self.isVisible():
                self.hide()
            return
        geo = phys_to_logical(*r)
        if self.geometry() != geo:
            self.setGeometry(geo)
        if not self.isVisible():
            self.show()
            hwnd = int(self.winId())
            self.capture_excluded = winutil.make_overlay(hwnd)
            if os.environ.get("TRCEVIRI_SHOW_IN_CAPTURE") == "1":   # sadece test/ekran görüntüsü için
                winutil.user32.SetWindowDisplayAffinity(hwnd, 0)
                self.capture_excluded = False
        self.raise_()

    def paintEvent(self, _ev) -> None:
        s = self.settings
        W, H = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        if s.debug_boxes and not s.auto_mode:
            p.setPen(QPen(QColor(0, 200, 255, 200), 2, Qt.DashLine))
            for z in self.pipe.profile.zones:
                if z.enabled:
                    p.drawRect(QRectF(z.x * W, z.y * H, z.w * W, z.h * H))
        bg = QColor(s.box_color)
        alpha = {"semi": 160, "text": 0}.get(s.display_mode, s.box_opacity)
        bg.setAlpha(max(0, min(255, alpha)))
        zones = {z.id: z for z in self.pipe.profile.zones}
        for zid, items in self.zone_items.items():
            z = zones.get(zid)
            zscale = z.font_scale if z else 1.0
            for it in items:
                self._draw_item(p, it, W, H, bg, zscale, z)
        p.end()

    def _draw_match(self, p: QPainter, it, W: int, H: int) -> None:
        """Birebir stil: Türkçe, İngilizcenin tam yerine ve İngilizceyle AYNI boyutta çizilir (her yazı kendi boyutunda).
        Uzunsa önce hafifçe sıkıştırılır; ancak sığmazsa genişler / alt satıra geçer.
        Zemin varsayılan olarak simsiyah (bg_mode: black | semi | game)."""
        s = self.settings
        x0, y0, x1, y1 = it.box[0] * W, it.box[1] * H, it.box[2] * W, it.box[3] * H
        ow = max(8.0, x1 - x0)
        lh = max(8.0, it.line_h * H)                 # İngilizce satır yüksekliği (OCR kutusu)
        base = max(10.0, lh * 0.78 * s.font_scale)   # Qt piksel boyutu ≈ satır kutusunun %78'i = aynı görünen boyut
        text = f"{it.speaker}: {it.tr}" if it.speaker else it.tr
        nl = max(1, it.lines)
        sub = it.kind in ("subtitle", "objective")

        def font_for(px):
            from .fonts import family
            f = QFont(family(s)); f.setPixelSize(max(9, int(px))); f.setWeight(QFont.DemiBold)
            return f, QFontMetricsF(f)

        # 1) İngilizceyle aynı satır sayısında, aynı genişliğe sığdır (en çok %18 küçült)
        size = base
        while True:
            f, fm = font_for(size)
            lines = wrap(text, fm, ow * 1.06)
            if len(lines) <= nl or size <= base * 0.82:
                break
            size *= 0.96
        # 2) Hâlâ sığmıyorsa: altyazı bir satır daha alır / diğerleri sağa doğru genişler
        if len(lines) > nl:
            if sub:
                lines = wrap(text, fm, max(ow, W * 0.82))
            elif it.align == "l":
                lines = wrap(text, fm, max(ow, min(W - x0 - 8, ow * 1.6)))
            else:
                lines = wrap(text, fm, max(ow, ow * 1.5))
        lw = max(fm.horizontalAdvance(l) for l in lines)
        th = len(lines) * fm.lineSpacing()
        tx0 = x0 if it.align == "l" else (x0 + x1) / 2 - lw / 2
        tx0 = max(4.0, min(tx0, W - lw - 4))
        if sub and len(lines) > nl:
            ty0 = y1 - th                            # altyazı yukarı doğru büyür (alt kenar sabit)
        else:
            ty0 = (y0 + y1) / 2 - th / 2
        pad = max(2.0, lh * 0.16)
        cover = QRectF(min(x0, tx0) - pad, min(y0, ty0) - pad,
                       max(x1, tx0 + lw) - min(x0, tx0) + 2 * pad, max(y1, ty0 + th) - min(y0, ty0) + 2 * pad)
        p.setPen(Qt.NoPen)
        mode = getattr(s, "bg_mode", "black")
        if mode == "game" and it.bg:
            base_c = QColor(it.bg)
            for grow, alpha in ((pad * 1.6, 50), (pad * 0.9, 120), (0.0, 255)):
                c = QColor(base_c); c.setAlpha(alpha); p.setBrush(c)
                p.drawRoundedRect(cover.adjusted(-grow, -grow, grow, grow), pad + grow, pad + grow)
        elif mode == "none":
            pass                                    # "Altında göster": kutu yok, sadece yazı
        else:
            c = QColor(s.box_color if mode == "black" else "#000000")
            c.setAlpha(max(0, min(255, s.box_opacity)) if mode == "black" else 170)
            p.setBrush(c)
            p.drawRoundedRect(cover, pad * 0.8, pad * 0.8)
        fg = QColor(it.fg) if (s.match_colors and it.fg) else QColor(s.text_color)
        spk = QColor(it.sc) if it.sc else QColor(s.speaker_color)
        if mode not in ("game", "none"):       # koyu zeminde koyu yazı okunmaz → beyaz
            if fg.lightness() < 110:
                fg = QColor(s.text_color)
            if spk.lightness() < 110:
                spk = QColor(s.speaker_color)
        y = ty0 + fm.ascent()
        prefix = f"{it.speaker}:" if it.speaker else ""
        for i, line in enumerate(lines):
            w = fm.horizontalAdvance(line)
            x = tx0 if it.align == "l" else tx0 + (lw - w) / 2
            if i == 0 and prefix and line.startswith(prefix):
                self._text(p, f, QPointF(x, y), prefix, spk)
                self._text(p, f, QPointF(x + fm.horizontalAdvance(prefix), y), line[len(prefix):], fg)
            else:
                self._text(p, f, QPointF(x, y), line, fg)
            y += fm.lineSpacing()

    def _draw_item(self, p: QPainter, it, W: int, H: int, bg: QColor, zscale: float, zone) -> None:
        s = self.settings
        if s.display_mode == "match":
            return self._draw_match(p, it, W, H)
        x0, y0, x1, y1 = it.box[0] * W, it.box[1] * H, it.box[2] * W, it.box[3] * H
        pad = max(6.0, it.line_h * H * 0.3)   # OCR kutusu harfleri tam sarmayabilir; İngilizce hiç görünmesin
        cover = QRectF(x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad)
        text = f"{it.speaker}: {it.tr}" if it.speaker else it.tr
        # Türkçe genelde daha uzun: bölge genişliğine kadar yayılmasına izin ver
        kind = getattr(it, "kind", "text")
        if kind in ("subtitle", "objective"):
            lo, hi = (zone.x * W, (zone.x + zone.w) * W) if zone is not None else (0.06 * W, 0.94 * W)
            avail_w = max(cover.width(), min(hi - lo, cover.width() * 1.35))
            cx = cover.center().x()
            left = max(lo, min(cx - avail_w / 2, hi - avail_w))
            cover.setLeft(left)
            cover.setWidth(avail_w)
        else:
            # serbest yazı: sağa doğru biraz genişleyebilir (Türkçe daha uzun)
            cover.setWidth(min(W - cover.left(), cover.width() * 1.25))
        px = max(12.0, it.line_h * H * 0.92 * zscale * s.font_scale)
        from .fonts import family
        font, lines, need = layout_item(text, family(s), px, cover.width() - 2 * pad, cover.height() - 2 * pad)
        fm = QFontMetricsF(font)
        if need + 2 * pad > cover.height():
            grow = need + 2 * pad - cover.height()
            # altyazıyı yukarı doğru büyüt (alt kenar sabit)
            if kind == "subtitle":
                cover.setTop(cover.top() - grow)
            else:
                cover.setHeight(cover.height() + grow)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(cover, 6, 6)
        y = cover.top() + (cover.height() - need) / 2 + fm.ascent()
        spk_prefix = f"{it.speaker}:" if it.speaker else ""
        for i, line in enumerate(lines):
            lw = fm.horizontalAdvance(line)
            x = cover.left() + (cover.width() - lw) / 2
            if i == 0 and spk_prefix and line.startswith(spk_prefix):
                self._text(p, font, QPointF(x, y), spk_prefix, QColor(s.speaker_color))
                rest = line[len(spk_prefix):]
                self._text(p, font, QPointF(x + fm.horizontalAdvance(spk_prefix), y), rest, QColor(s.text_color))
            else:
                self._text(p, font, QPointF(x, y), line, QColor(s.text_color))
            y += fm.lineSpacing()

    @staticmethod
    def _text(p: QPainter, font: QFont, pos: QPointF, text: str, color: QColor) -> None:
        path = QPainterPath()
        path.addText(pos, font, text)
        p.setPen(QPen(QColor(0, 0, 0, 230), max(2.0, font.pixelSize() / 14), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(path)