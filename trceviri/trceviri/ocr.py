"""RapidOCR sarmalayıcı: ön işleme ve satır gruplama."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger("ocr")


@dataclass
class Line:
    text: str
    box: tuple[int, int, int, int]   # x0, y0, x1, y1 (bölge kırpımına göre piksel)
    score: float


class OcrEngine:
    def __init__(self, use_gpu: bool = False, threads: int = 4):
        self.threads = max(1, int(threads))
        from rapidocr_onnxruntime import RapidOCR
        # Varsayılan "min" sınırı küçük kırpımları 736 px'e büyütüp OCR'ı ~1 sn'ye çıkarıyor.
        # "max" sınırı ile 1280x180 altyazı kırpımı ~90 ms.
        base = {"det_limit_side_len": self.MAX_SIDE, "det_limit_type": "max",
                "intra_op_num_threads": self.threads, "inter_op_num_threads": 1}
        kw = dict(base)
        if use_gpu:
            # Ölçüm (RTX 3050): tespit GPU'da 120→77 ms, tanıma GPU'da yavaşlıyor (62→500 ms) → sadece tespit GPU'da
            kw.update({"det_use_dml": True})
        try:
            self.engine = RapidOCR(**kw)
        except Exception as e:  # DirectML yoksa CPU
            log.warning("GPU OCR açılamadı (%s), CPU kullanılıyor", e)
            self.engine = RapidOCR(**base)

    MAX_SIDE = 1280

    def read(self, img: np.ndarray, min_conf: float = 0.6) -> list[Line]:
        if img is None or img.size == 0:
            return []
        h, w = img.shape[:2]
        scale = 1.0
        # küçük yazılar için büyüt, çok büyük kareleri küçült (hız)
        if h < 90:
            scale = 2.0
        elif h < 140:
            scale = 1.5
        scale = min(scale, self.MAX_SIDE / max(w, h))   # tespit sınırını aşmasın
        work = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1.0 else img
        try:
            result, _ = self.engine(work, use_cls=False)
        except Exception as e:
            log.error("OCR hatası: %s", e)
            return []
        if not result:
            return []
        boxes = []
        for pts, text, score in result:
            if float(score) < min_conf or not str(text).strip():
                continue
            arr = np.array(pts, dtype=np.float32) / scale
            x0, y0 = arr.min(axis=0)
            x1, y1 = arr.max(axis=0)
            boxes.append((float(x0), float(y0), float(x1), float(y1), str(text).strip(), float(score)))
        return group_lines(boxes)


class FullScreenReader:
    """Tüm kareyi tarar: küçültülmüş karede yazı tespiti, tam çözünürlükte tanıma.
    Ekranda duran satırlar önbellekten gelir; sadece yeni/değişen satırlar tanınır."""

    def __init__(self, engine: OcrEngine, scan_width: int = 960):
        self.engine = engine.engine
        self.scan_width = scan_width
        self.memo: list[tuple[tuple[float, float], np.ndarray, str, float]] = []

    @staticmethod
    def _sig(crop: np.ndarray) -> np.ndarray:
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        return cv2.resize(g, (48, 12), interpolation=cv2.INTER_AREA).astype(np.int16)

    def _lookup(self, center, sig):
        for c, s, text, score in self.memo:
            if abs(c[0] - center[0]) < 6 and abs(c[1] - center[1]) < 6 and np.abs(s - sig).mean() < 6:
                return text, score
        return None

    def read(self, frame: np.ndarray, min_conf: float = 0.6) -> list[Line]:
        H, W = frame.shape[:2]
        f = min(1.0, self.scan_width / W)
        small = cv2.resize(frame, (int(W * f), int(H * f)), interpolation=cv2.INTER_AREA) if f < 1 else frame
        try:
            dets, _ = self.engine(small, use_cls=False, use_rec=False)
        except Exception as e:
            log.error("yazı tespiti hatası: %s", e)
            return []
        if dets is None or len(dets) == 0:
            self.memo = []
            return []
        boxes, new_memo = [], []
        for pts in dets:
            arr = np.array(pts, dtype=np.float32) / f
            x0, y0 = arr.min(axis=0)
            x1, y1 = arr.max(axis=0)
            hgt = y1 - y0
            if hgt < 8 or (x1 - x0) < 10:
                continue
            pad = max(2, int(hgt * 0.12))
            X0, Y0 = max(0, int(x0) - pad), max(0, int(y0) - pad)
            X1, Y1 = min(W, int(x1) + pad), min(H, int(y1) + pad)
            crop = frame[Y0:Y1, X0:X1]
            if crop.size == 0:
                continue
            center = ((x0 + x1) / 2, (y0 + y1) / 2)
            sig = self._sig(crop)
            hit = self._lookup(center, sig)
            if hit is None:
                try:
                    res, _ = self.engine(crop, use_det=False, use_cls=False, use_rec=True)
                    text, score = (res[0][0], float(res[0][1])) if res else ("", 0.0)
                except Exception as e:
                    log.debug("tanıma hatası: %s", e)
                    text, score = "", 0.0
            else:
                text, score = hit
            new_memo.append((center, sig, text, score))
            text = str(text).strip()
            if text and score >= min_conf:
                boxes.append((float(x0), float(y0), float(x1), float(y1), text, score))
        self.memo = new_memo
        return group_lines(boxes)


def group_lines(boxes: list[tuple]) -> list[Line]:
    """Aynı yatay hizadaki kutuları tek satırda birleştirir."""
    boxes = sorted(boxes, key=lambda b: (b[1] + b[3]) / 2)
    rows: list[list[tuple]] = []
    for b in boxes:
        cy = (b[1] + b[3]) / 2
        hh = b[3] - b[1]
        for row in rows:
            ry0 = min(r[1] for r in row)
            ry1 = max(r[3] for r in row)
            near = any(max(r[0] - b[2], b[0] - r[2]) < hh * 2.5 for r in row)   # aynı satırda ve yakın
            if near and ry0 - hh * 0.3 <= cy <= ry1 + hh * 0.3:
                row.append(b)
                break
        else:
            rows.append([b])
    lines = []
    for row in rows:
        row.sort(key=lambda r: r[0])
        text = " ".join(r[4] for r in row)
        x0 = min(r[0] for r in row); y0 = min(r[1] for r in row)
        x1 = max(r[2] for r in row); y1 = max(r[3] for r in row)
        score = sum(r[5] for r in row) / len(row)
        lines.append(Line(text, (int(x0), int(y0), int(x1), int(y1)), score))
    return lines
