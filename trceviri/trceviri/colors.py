"""Oyundaki yazının rengini ve arkasındaki zemini kareden ölçer (Türkçeyi aynı görünümde çizmek için)."""
from __future__ import annotations

import numpy as np


def _hex(c) -> str:
    b, g, r = (int(max(0, min(255, v))) for v in c)   # kare BGR
    return f"#{r:02X}{g:02X}{b:02X}"


def _lum(c) -> float:
    b, g, r = c
    return 0.299 * r + 0.587 * g + 0.114 * b


def sample(frame: np.ndarray, box: tuple[int, int, int, int]) -> tuple[str, str]:
    """(yazı rengi, zemin rengi) — #RRGGBB."""
    H, W = frame.shape[:2]
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, max(x0 + 2, x1)), min(H, max(y0 + 2, y1))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return "#FFFFFF", "#101010"
    h = y1 - y0
    pad = max(3, int(h * 0.45))
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    outer = frame[Y0:Y1, X0:X1].reshape(-1, 3).astype(np.float32)
    mask = np.ones((Y1 - Y0, X1 - X0), bool)
    mask[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = False
    ring = frame[Y0:Y1, X0:X1][mask].astype(np.float32)
    bg = np.median(ring, axis=0) if len(ring) else np.median(outer, axis=0)
    inner = frame[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    dist = np.linalg.norm(inner - bg, axis=1)
    thr = np.percentile(dist, 80)
    far = inner[dist >= max(thr, 40)]
    if len(far) < 8:
        fg = np.array([255, 255, 255], np.float32) if _lum(bg) < 140 else np.array([20, 20, 20], np.float32)
    else:
        lum = 0.299 * far[:, 2] + 0.587 * far[:, 1] + 0.114 * far[:, 0]
        bright, dark = far[lum > _lum(bg)], far[lum <= _lum(bg)]
        # oyun yazıları çoğunlukla açık renk + koyu kontur: ikisi de varsa açık olanı al
        if len(bright) >= 0.2 * len(far):
            fg = np.median(bright, axis=0)
        else:
            fg = np.median(dark, axis=0)
    if abs(_lum(fg) - _lum(bg)) < 60:      # okunaklılık garantisi
        fg = np.array([255, 255, 255], np.float32) if _lum(bg) < 128 else np.array([15, 15, 15], np.float32)
    return _hex(fg), _hex(bg)
