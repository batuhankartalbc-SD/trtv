"""Uygulama ikonunu (TRCeviri.ico) logo SVG'sinden üretir."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray

app = QGuiApplication([])
from trceviri.icons import svg

out = Path(__file__).resolve().parent / "TRCeviri.ico"
img = QImage(256, 256, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QColor("#0F1A17")); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(8, 8, 240, 240), 52, 52)
QSvgRenderer(QByteArray(svg("logo", "#3EE6A0").encode())).render(p, QRectF(40, 40, 176, 176))
p.end()
img.save(str(out))
print(out, out.stat().st_size)
