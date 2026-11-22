"""Ölçüm aracı: sentetik oyun kareleri üretir, gerçek OCR + sınıflandırma + yerel çeviriden geçirir.

Ölçülen:
  - OCR doğruluğu (karakter hata oranı, CER) — farklı fontlar, arka planlar, yazı boyutları
  - tür (altyazı / kontrol / menü) doğruluğu
  - süreler: ilk kare (soğuk), aynı kare (önbellekli), yeni satır gelen kare, çeviri

Kullanım:  python tools/bench.py [--gpu] [--out rapor.json]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trceviri.ocr import FullScreenReader, OcrEngine  # noqa: E402
from trceviri.pipeline import build_blocks  # noqa: E402

W, H = 1920, 1080
WINFONTS = Path("C:/Windows/Fonts")
FONTS = [p for p in [WINFONTS / "segoeui.ttf", WINFONTS / "arial.ttf", WINFONTS / "bahnschrift.ttf",
                     WINFONTS / "tahoma.ttf", WINFONTS / "verdana.ttf", WINFONTS / "georgia.ttf",
                     ROOT.parent / "brand" / "fonts" / "condensed.ttf", ROOT.parent / "brand" / "fonts" / "clean.ttf"]
         if p.exists()]

SUBS = [("Lucia", "Where are you going? We need to leave now."),
        ("Jason", "Relax. I've got it under control."),
        ("Kratos", "Stay close, boy. Do not wander off."),
        ("", "Find a way out before the guards return."),
        ("Ellie", "I can't believe we actually made it here."),
        ("", "The bridge is out. We have to find another way across."),
        ("Aloy", "These machines are different. Something changed them."),
        ("Mimir", "Brother, the path ahead is treacherous."),
        ("", "Follow the river until you reach the old mill."),
        ("Leon", "Where's everyone going? Bingo?")]
HINTS = ["Press X to interact", "Hold R2 to accelerate", "Press Triangle to open the door",
         "Press L3 to sprint", "Hold L2 to aim", "Press OPTIONS to pause"]
MENU = ["Resume", "Settings", "Map", "Inventory", "Photo Mode", "Quit to Main Menu"]


def background(seed: int) -> Image.Image:
    rnd = random.Random(seed)
    kind = seed % 4
    if kind == 0:     # karanlık gradyan (gece sahnesi)
        a = np.linspace(rnd.randint(5, 40), rnd.randint(40, 90), H)[:, None, None]
        img = np.repeat(np.repeat(a, W, 1), 3, 2) * np.array([0.6, 0.8, 1.0])
    elif kind == 1:   # parlak gökyüzü (zor: beyaz yazı açık zemin)
        a = np.linspace(200, 120, H)[:, None, None]
        img = np.repeat(np.repeat(a, W, 1), 3, 2) * np.array([1.0, 0.95, 0.8])
    elif kind == 2:   # dokulu gürültü (orman/şehir)
        img = np.random.default_rng(seed).integers(20, 160, (H // 8, W // 8, 3)).astype(np.float32)
        img = np.array(Image.fromarray(img.astype(np.uint8)).resize((W, H), Image.BICUBIC))
    else:             # orta ton + bloklar
        img = np.full((H, W, 3), 90, np.float32)
        for _ in range(30):
            x, y = rnd.randint(0, W), rnd.randint(0, H)
            img[y:y + rnd.randint(50, 300), x:x + rnd.randint(50, 400)] = [rnd.randint(30, 220) for _ in range(3)]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def draw_text(d: ImageDraw.ImageDraw, xy, text, font, fill=(255, 255, 255), shadow=True, anchor="la"):
    if shadow:
        for dx, dy in ((2, 2), (1, 2), (2, 1)):
            d.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=(0, 0, 0), anchor=anchor)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def make_scene(i: int):
    rnd = random.Random(i)
    im = background(i)
    d = ImageDraw.Draw(im)
    fpath = FONTS[i % len(FONTS)]
    size = [30, 36, 42, 48][i % 4]
    f = ImageFont.truetype(str(fpath), size)
    truth = []
    spk, line = SUBS[i % len(SUBS)]
    sub = f"{spk}: {line}" if spk else line
    draw_text(d, (W // 2, int(H * 0.86)), sub, f, anchor="mm")
    truth.append(("subtitle", sub))
    if i % 2 == 0:
        hf = ImageFont.truetype(str(fpath), max(22, size - 10))
        hint = HINTS[i % len(HINTS)]
        d.rounded_rectangle((40, 40, 40 + d.textlength(hint, font=hf) + 40, 40 + size + 20), 8, fill=(15, 15, 15))
        draw_text(d, (60, 50), hint, hf, shadow=False)
        truth.append(("controls", hint))
    if i % 3 == 0:
        mf = ImageFont.truetype(str(fpath), 34)
        for k, m in enumerate(MENU):
            draw_text(d, (W - 520, 260 + k * 62), m, mf)
            truth.append(("menu", m))
    frame = np.array(im)[:, :, ::-1].copy()     # RGB → BGR (uygulama gibi)
    return frame, truth, fpath.stem, size


def cer(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if not a:
        return 0.0 if not b else 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / len(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--scan", type=int, default=960)
    ap.add_argument("--out", default="")
    ap.add_argument("--translate", action="store_true", help="yerel modelle çeviri süresini de ölç")
    a = ap.parse_args()
    eng = OcrEngine(a.gpu, 4)
    rd = FullScreenReader(eng, a.scan)
    cold, warm, cers, kinds_ok, kinds_n, missed = [], [], [], 0, 0, []
    per_font: dict[str, list[float]] = {}
    rd.read(make_scene(999)[0])                 # ısınma
    for i in range(a.n):
        frame, truth, font, size = make_scene(i)
        rd.memo = []
        t0 = time.perf_counter(); lines = rd.read(frame, 0.5); cold.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter(); rd.read(frame, 0.5); warm.append((time.perf_counter() - t0) * 1000)
        items = build_blocks(lines, W, H, [], True, {"subtitle", "menu", "controls", "other", "nav"}, frame)
        for kind, text in truth:
            want = text.split(": ", 1)[1] if kind == "subtitle" and ": " in text else text
            best, bk = None, None
            for it in items:
                c = cer(want, it.src)
                if best is None or c < best:
                    best, bk = c, it.kind
            best = 1.0 if best is None else best
            cers.append(best)
            per_font.setdefault(f"{font}", []).append(best)
            if best > 0.15:
                missed.append({"scene": i, "font": font, "size": size, "want": want,
                               "got": [it.src for it in items]})
            kinds_n += 1
            kinds_ok += int(bk == kind and best <= 0.15)
    # sabit zeminde altyazı değişimi: aynı arka plan, farklı (daha kısa) altyazı → yeni metin okunmalı
    swap_ok, swap_ms, static_ms = 0, [], []
    for i in range(8):
        bg = background(100 + i)
        fnt = ImageFont.truetype(str(FONTS[i % len(FONTS)]), 40)
        frames = []
        for s in (SUBS[i][1], SUBS[(i + 3) % len(SUBS)][1]):
            im = bg.copy(); draw_text(ImageDraw.Draw(im), (W // 2, int(H * 0.86)), s, fnt, anchor="mm")
            frames.append((np.array(im)[:, :, ::-1].copy(), s))
        rd.read(frames[0][0], 0.5)
        t0 = time.perf_counter(); rd.read(frames[0][0], 0.5); static_ms.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter(); got = rd.read(frames[1][0], 0.5); swap_ms.append((time.perf_counter() - t0) * 1000)
        swap_ok += int(any(cer(frames[1][1], ln.text) < 0.1 for ln in got))
    # hareketli zemin, aynı altyazı (kamera dönüyor): satır hafızası tutmalı → hızlı ve doğru
    move_ms, move_ok = [], 0
    for i in range(8):
        fnt = ImageFont.truetype(str(FONTS[i % len(FONTS)]), 40)
        s = SUBS[i][1]
        outs = []
        for shift in (0, 6, 12):
            bg = background(200 + i).transform((W, H), Image.AFFINE, (1, 0, shift, 0, 1, 0))
            im = bg.copy(); draw_text(ImageDraw.Draw(im), (W // 2, int(H * 0.86)), s, fnt, anchor="mm")
            fr = np.array(im)[:, :, ::-1].copy()
            t0 = time.perf_counter(); got = rd.read(fr, 0.5); outs.append((time.perf_counter() - t0) * 1000)
            move_ok += int(any(cer(s, ln.text) < 0.1 for ln in got))
        move_ms += outs[1:]
    rep_swap_move = {"moving_bg_same_sub_correct": f"{move_ok}/24", "moving_bg_ms_median": round(statistics.median(move_ms), 1)}
    rep_swap = {**rep_swap_move,"subtitle_swap_detected": f"{swap_ok}/8", "static_frame_ms_median": round(statistics.median(static_ms), 2),
                "subtitle_swap_ms_median": round(statistics.median(swap_ms), 1)}
    rep = {
        **rep_swap,
        "gpu": a.gpu, "scenes": a.n, "scan_width": a.scan,
        "ocr_cold_ms_median": round(statistics.median(cold), 1), "ocr_cold_ms_p90": round(sorted(cold)[int(len(cold) * .9) - 1], 1),
        "ocr_cached_ms_median": round(statistics.median(warm), 1),
        "cer_mean": round(statistics.mean(cers), 4), "exact_or_near(<=2%)": round(sum(c <= 0.02 for c in cers) / len(cers), 3),
        "kind_accuracy": round(kinds_ok / kinds_n, 3),
        "cer_by_font": {k: round(statistics.mean(v), 4) for k, v in per_font.items()},
        "misses": missed[:15],
    }
    if a.translate:
        from trceviri.translate import make_engine
        le = make_engine("local", "", "")
        le.translate(["Warm up."], [], "")
        ts = []
        for spk, line in SUBS:
            t0 = time.perf_counter(); le.translate([line], [], ""); ts.append((time.perf_counter() - t0) * 1000)
        rep["translate_ms_median"] = round(statistics.median(ts), 1)
        rep["end_to_end_estimate_ms"] = round(rep["ocr_cold_ms_median"] + rep["translate_ms_median"], 1)
    out = json.dumps(rep, ensure_ascii=False, indent=1)
    print(out)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
