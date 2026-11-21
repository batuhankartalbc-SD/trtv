"""Windows yardımcıları: pencere bulma, istemci alanı, DPI, yakalamadan hariç tutma."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

WDA_EXCLUDEFROMCAPTURE = 0x11
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14

user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]


def set_dpi_aware() -> None:
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def _title(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _cloaked(hwnd: int) -> bool:
    v = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), DWMWA_CLOAKED, ctypes.byref(v), ctypes.sizeof(v))
    return v.value != 0


def list_windows() -> list[tuple[int, str]]:
    """Görünür, başlıklı üst düzey pencereler."""
    out: list[tuple[int, str]] = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and not _cloaked(hwnd):
            t = _title(hwnd)
            if t.strip():
                out.append((int(hwnd), t))
        return True

    user32.EnumWindows(proc(cb), 0)
    return out


REMOTE_HINTS = ("ps remote play", "remoteplay", "chiaki", "pxplay", "remote play")


def _area(hwnd: int) -> int:
    r = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(r)):
        return 0
    return (r.right - r.left) * (r.bottom - r.top)


def restore_in_background(hwnd: int) -> None:
    """Küçültülmüş pencereyi öne getirmeden geri açar ve diğer pencerelerin arkasına koyar.
    (Küçültülmüş pencere çizilmediği için görüntüsü okunamaz; arkada açık pencere ise okunabilir.)"""
    SW_SHOWNOACTIVATE = 4
    HWND_BOTTOM = 1
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def find_window(hint: str, restore: bool = False) -> int | None:
    """Eşleşen görünür pencerelerden EN BÜYÜĞÜNÜ seçer (Remote Play bağlanınca oyunu ayrı pencerede açar).
    restore=True: hepsi küçültülmüşse en sonuncusunu arka planda geri açar."""
    allw = [(h, t) for h, t in list_windows() if "trçeviri" not in t.lower() and "brolis" not in t.lower() and "toolbar" not in t.lower()]
    if restore:
        h0 = (hint or "").lower().strip()
        match = [w for w in allw if (h0 and h0 in w[1].lower()) or any(x in w[1].lower() for x in REMOTE_HINTS)]
        if match and all(user32.IsIconic(h) for h, _ in match):
            restore_in_background(match[0][0])
    wins = [(h, t) for h, t in allw if not user32.IsIconic(h)]
    h = (hint or "").lower().strip()
    cands = [w for w in wins if h and h in w[1].lower()]
    if not cands:
        cands = [w for w in wins if any(x in w[1].lower() for x in REMOTE_HINTS)]
    if not cands:
        return None
    return max(cands, key=lambda w: _area(w[0]))[0]


def is_valid(hwnd: int | None) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


def is_minimized(hwnd: int) -> bool:
    return bool(user32.IsIconic(hwnd))


def client_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Ekran koordinatlarında istemci alanı (x, y, w, h) — fiziksel piksel."""
    r = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(r)):
        return None
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    w, h = r.right - r.left, r.bottom - r.top
    if w < 50 or h < 50:
        return None
    return pt.x, pt.y, w, h


def fit_16_9(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Siyah bantlı (letterbox) görüntüde ortalanmış 16:9 oyun alanı."""
    x, y, w, h = rect
    if w * 9 > h * 16:            # geniş: yanlarda bant
        nw = h * 16 // 9
        return x + (w - nw) // 2, y, nw, h
    nh = w * 9 // 16              # uzun: üst/altta bant
    return x, y + (h - nh) // 2, w, nh


PW_CLIENTONLY_RENDERFULL = 0x3


def capture_window(hwnd: int, w: int, h: int):
    """Pencerenin istemci alanını, önünde başka pencere olsa bile yakalar (PrintWindow).
    Başarısızsa None döner."""
    import numpy as np
    import win32gui
    import win32ui

    hdc = win32gui.GetWindowDC(hwnd)
    if not hdc:
        return None
    src = dst = bmp = None
    try:
        src = win32ui.CreateDCFromHandle(hdc)
        dst = src.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(src, w, h)
        dst.SelectObject(bmp)
        ok = user32.PrintWindow(hwnd, dst.GetSafeHdc(), PW_CLIENTONLY_RENDERFULL)
        if not ok:
            return None
        buf = bmp.GetBitmapBits(True)
        img = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)[:, :, :3]
        return np.ascontiguousarray(img)
    finally:
        if bmp is not None:
            win32gui.DeleteObject(bmp.GetHandle())
        if dst is not None:
            dst.DeleteDC()
        if src is not None:
            src.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)


def make_overlay(hwnd: int) -> bool:
    """Tıklama geçirgen, odak almayan ve ekran yakalamada görünmeyen pencere."""
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))


def exclude_from_capture(hwnd: int) -> bool:
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
