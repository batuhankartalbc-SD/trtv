"""Genel kısayol tuşları (oyun öndeyken de çalışır)."""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
VK = {"F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}
MOD_ALT, MOD_CONTROL = 0x1, 0x2
# TV hizalama: Ctrl+Alt + oklar (kaydır), PgUp/PgDn (büyüt/küçült), Home (sıfırla), End (hizalama modu aç/kapa)
CAL = {"CAL_LEFT": 0x25, "CAL_UP": 0x26, "CAL_RIGHT": 0x27, "CAL_DOWN": 0x28,
       "CAL_BIGGER": 0x21, "CAL_SMALLER": 0x22, "CAL_RESET": 0x24, "CAL_MODE": 0x23}
user32 = ctypes.windll.user32


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, cb):
        super().__init__()
        self.cb = cb

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG" or event_type == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self.cb(int(msg.wParam))
                return True, 0
        return False, 0


class Hotkeys(QObject):
    pressed = Signal(str)

    def __init__(self, app, hwnd: int):
        super().__init__()
        self.hwnd = hwnd
        self.ids: dict[int, str] = {}
        self.failed: list[str] = []
        self.filter = _Filter(self._on)
        app.installNativeEventFilter(self.filter)
        keys = [(n, MOD_NOREPEAT, vk) for n, vk in VK.items()] + \
               [(n, MOD_CONTROL | MOD_ALT, vk) for n, vk in CAL.items()]       # oklar basılı tutulunca tekrarlasın
        for i, (name, mods, vk) in enumerate(keys, start=0xB000):
            if user32.RegisterHotKey(wintypes.HWND(hwnd), i, mods, vk):
                self.ids[i] = name
            else:
                self.failed.append(name)

    def _on(self, hid: int):
        name = self.ids.get(hid)
        if name:
            self.pressed.emit(name)

    def unregister(self):
        for i in self.ids:
            user32.UnregisterHotKey(wintypes.HWND(self.hwnd), i)
