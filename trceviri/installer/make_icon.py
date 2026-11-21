import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtCore import Qt
app = QGuiApplication([])
root = Path(sys.argv[1])
img = QImage(str(root / "assets" / "logo.png")).scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
img.save(str(root / "installer" / "TRCeviri.ico"))
print("ico ok")