"""API anahtarlarını Windows DPAPI ile şifreler (sadece bu kullanıcı çözebilir)."""
from __future__ import annotations

import base64


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    import win32crypt
    blob = win32crypt.CryptProtectData(plain.encode("utf-8"), "TRCeviri", None, None, None, 0)
    return base64.b64encode(blob).decode("ascii")


def decrypt(enc: str) -> str:
    if not enc:
        return ""
    try:
        import win32crypt
        _, data = win32crypt.CryptUnprotectData(base64.b64decode(enc), None, None, None, 0)
        return data.decode("utf-8")
    except Exception:
        return ""
