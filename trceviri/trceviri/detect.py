"""Değişim algılama: kare değişmediyse OCR'ı atla."""
from __future__ import annotations

import cv2
import numpy as np


def signature(img: np.ndarray) -> np.ndarray:
    small = cv2.resize(img, (max(8, img.shape[1] // 4), max(8, img.shape[0] // 4)), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if small.ndim == 3 else small
    return cv2.GaussianBlur(g, (3, 3), 0)


def diff(a: np.ndarray | None, b: np.ndarray) -> float:
    if a is None or a.shape != b.shape:
        return 255.0
    return float(cv2.absdiff(a, b).mean())


def has_text_like(img: np.ndarray) -> bool:
    """Hızlı ön kontrol: bölgede yazıya benzeyen keskin kenar var mı?"""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # altyazılar genelde çok açık (beyaz) ya da koyu konturlu
    bright = (g > 200).mean()
    edges = cv2.Canny(g, 80, 200).mean() / 255.0
    return edges > 0.004 or bright > 0.003


class ChangeGate:
    """Bölge başına: kare değişti mi ya da yeniden okuma zamanı geldi mi?"""

    def __init__(self, threshold: float = 3.0, max_idle_s: float = 0.8):
        self.threshold = threshold
        self.max_idle_s = max_idle_s
        self.prev: np.ndarray | None = None
        self.last_ocr = 0.0

    def should_ocr(self, img: np.ndarray, now: float) -> bool:
        sig = signature(img)
        d = diff(self.prev, sig)
        if d >= self.threshold or now - self.last_ocr >= self.max_idle_s:
            self.prev = sig
            self.last_ocr = now
            return True
        return False
