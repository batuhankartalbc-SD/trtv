"""Dosya + arayüz log'u."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal

from .config import LOG_DIR


class _Bridge(QObject):
    line = Signal(str)


bridge = _Bridge()


class _QtHandler(logging.Handler):
    def emit(self, record):
        try:
            bridge.line.emit(self.format(record))
        except Exception:
            pass


def setup() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = RotatingFileHandler(LOG_DIR / "trceviri.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    qh = _QtHandler()
    qh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(qh)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    def hook(et, ev, tb):
        logging.getLogger("hata").error("Beklenmeyen hata", exc_info=(et, ev, tb))

    sys.excepthook = hook

    import threading

    def thook(args):          # arka plan iş parçacıklarındaki yakalanmamış hatalar da günlüğe yazılsın
        if args.exc_type is not SystemExit:
            logging.getLogger("hata").error("İş parçacığı hatası (%s)", getattr(args.thread, "name", "?"),
                                            exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = thook
