"""Bilgisayar uygulaması güncellemesi + Windows ile başlatma.

GitHub'daki 'pc-latest' sürümüne bakar; daha yeni sürüm varsa kurulum dosyasını indirip sessizce kurar
(Inno Setup: /SILENT, kurulum bitince uygulamayı yeniden açar)."""
from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from . import __version__

log = logging.getLogger("guncelleme")
API = "https://api.github.com/repos/batuhankartalbc-SD/trtv/releases/tags/pc-latest"
ASSET = "TRCeviri-Kurulum.exe"


def _ver(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3]) or (0,)


def check() -> dict | None:
    """Yeni sürüm varsa {'version','url','notes'} döner. Geliştirme ortamında denetlenmez."""
    from .config import DEV
    if DEV:
        return None
    try:
        r = httpx.get(API, timeout=8, headers={"Accept": "application/vnd.github+json"}, follow_redirects=True)
        if r.status_code != 200:
            return None
        d = r.json()
        ver = re.search(r"\d+\.\d+\.\d+", d.get("name", "") + " " + d.get("tag_name", "") + " " + (d.get("body") or ""))
        if not ver or _ver(ver.group(0)) <= _ver(__version__):
            return None
        url = next((a["browser_download_url"] for a in d.get("assets", []) if a["name"] == ASSET), None)
        return {"version": ver.group(0), "url": url, "notes": d.get("body") or ""} if url else None
    except Exception as e:
        log.info("güncelleme denetlenemedi: %s", e)
        return None


def install(url: str, progress=None) -> bool:
    """Kurulumu indir ve sessiz başlat; çağıran uygulama hemen kapanmalı."""
    dst = Path(tempfile.gettempdir()) / ASSET
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(30, read=60)) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0)) or 1
            got = 0
            with open(dst, "wb") as f:
                for ch in r.iter_bytes(1 << 20):
                    f.write(ch); got += len(ch)
                    if progress:
                        progress(int(got * 100 / total))
        subprocess.Popen([str(dst), "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS", "/NOCANCEL"],
                         creationflags=0x00000008)   # DETACHED_PROCESS
        return True
    except Exception as e:
        log.error("güncelleme indirilemedi: %s", e)
        return False


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# ---------------------------------------------------------------- Windows ile başlat
def _startup_lnk() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "TRÇeviri.lnk"


def autostart_enabled() -> bool:
    return _startup_lnk().exists()


def set_autostart(on: bool) -> None:
    """Başlangıç klasörüne kısayol koyar/kaldırır (sadece bu kullanıcı; yönetici izni gerekmez)."""
    lnk = _startup_lnk()
    if not on:
        lnk.unlink(missing_ok=True)
        return
    import win32com.client
    if frozen():
        target, args, cwd = sys.executable, "--baslat", str(Path(sys.executable).parent)
    else:
        pyw = Path(sys.executable).with_name("pythonw.exe")
        target, args, cwd = str(pyw), "-m trceviri --baslat", str(Path(__file__).resolve().parent.parent)
    sh = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(lnk))
    sh.TargetPath = target
    sh.Arguments = args
    sh.WorkingDirectory = cwd
    sh.Description = "TRÇeviri — canlı Türkçe çeviri"
    sh.Save()
