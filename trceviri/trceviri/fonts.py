"""Yazı tipi seçimi: 'default' (Segoe UI) ya da OFL lisanslı paket fontları (assets/fonts ya da depodaki brand/fonts).

Anahtarlar TV ile ortaktır: default | condensed | rounded | clean  (protokol: style.font, set font)."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("font")
KEYS = {"default": "Varsayılan", "condensed": "Oyun stili (dar)", "rounded": "Yuvarlak", "clean": "Sade"}
_ROOT = Path(__file__).resolve().parent.parent
_DIRS = [_ROOT / "assets" / "fonts", _ROOT.parent / "brand" / "fonts"]   # paket içi, sonra depo (geliştirme)
_families: dict[str, str] = {}
_loaded = False


def font_file(key: str) -> Path | None:
    for d in _DIRS:
        f = d / f"{key}.ttf"
        if f.exists():
            return f
    return None


def load() -> dict[str, str]:
    """Bulunan fontları Qt'ye kaydeder (QApplication oluşturulduktan sonra çağrılmalı)."""
    global _loaded
    if _loaded:
        return _families
    _loaded = True
    try:
        from PySide6.QtGui import QFontDatabase
    except Exception:
        return _families
    for key in ("condensed", "rounded", "clean"):
        f = font_file(key)
        if not f:
            continue
        fid = QFontDatabase.addApplicationFont(str(f))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if fams:
            _families[key] = fams[0]
            log.info("Yazı tipi yüklendi: %s → %s", key, fams[0])
    return _families


def available() -> dict[str, str]:
    """Seçilebilir anahtarlar → görünen ad (dosyası olmayanlar gösterilmez)."""
    load()
    return {k: v for k, v in KEYS.items() if k == "default" or k in _families}


def family(settings) -> str:
    """Çizimde kullanılacak aile adı; seçilen font yoksa varsayılan."""
    load()
    return _families.get(getattr(settings, "font_choice", "default"), settings.font_family)
