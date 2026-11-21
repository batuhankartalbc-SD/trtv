"""Bilgisayar → Android TV bağlantısı.

TV'deki "Brolis Game Translate (TV)" uygulaması 47800 numaralı TCP portunu dinler. Bilgisayar ev ağını tarayıp onu
kendisi bulur ve bağlanır (giden bağlantı olduğu için Windows güvenlik duvarı izni gerekmez).
Her çeviri değişikliği tek satırlık JSON olarak anında gönderilir; TV bunu HDMI görüntüsünün üstüne çizer.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import queue
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal

log = logging.getLogger("tv")
PORT = 47800


def local_ipv4s() -> list[str]:
    ips = set()
    try:  # varsayılan ağ arayüzü (paket göndermez)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except Exception:
        pass
    return [i for i in ips if not i.startswith(("127.", "169.254."))]


def probe(host: str, timeout: float = 0.35) -> dict | None:
    try:
        with socket.create_connection((host, PORT), timeout=timeout) as s:
            s.settimeout(0.8)
            s.sendall(b'{"t":"hello","probe":true}\n')
            data = b""
            while not data.endswith(b"\n") and len(data) < 4096:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            msg = json.loads(data.decode("utf-8").strip() or "{}")
            if msg.get("app") == "trceviri-tv":
                return msg
    except Exception:
        return None
    return None


def scan() -> str | None:
    hosts: list[str] = []
    for ip in local_ipv4s():
        net = ipaddress.ip_network(f"{ip}/24", strict=False)
        hosts += [str(h) for h in net.hosts() if str(h) != ip]
    if not hosts:
        return None
    with ThreadPoolExecutor(max_workers=96) as ex:
        for host, res in zip(hosts, ex.map(probe, hosts)):
            if res:
                return host
    return None


class TvLink(QObject):
    status = Signal(bool, str)
    calib_request = Signal(str)            # TV kumandasıyla hizalama: CAL_LEFT, CAL_MODE_ON ...
    setting_request = Signal(str, object)  # TV kumandasıyla ayar: ("font_scale", 1.1) ...

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.q: queue.Queue[bytes] = queue.Queue()
        self.state: dict[str, list] = {}       # yeniden bağlanınca son durumu tekrar gönder
        self.visible = True
        self.calib = False
        self.connected = False
        self.host: str | None = None
        self.stop_evt = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name="tv-baglanti")
        self.thread.start()

    # --- dışarıdan çağrılanlar (herhangi bir iş parçacığından)
    def send_items(self, zone_id: str, items: list) -> None:
        payload = [{"b": [round(v, 4) for v in it.box], "lh": round(it.line_h, 4), "s": it.speaker,
                    "tr": it.tr or "", "k": getattr(it, "kind", "text"), "n": it.lines,
                    "fg": it.fg, "bg": it.bg, "sc": it.sc, "a": it.align} for it in items if it.tr]
        if payload:
            self.state[zone_id] = payload
        else:
            self.state.pop(zone_id, None)
        self._put({"t": "items", "z": zone_id, "items": payload})

    def send_style(self) -> None:
        s = self.settings
        self._put({"t": "style", "box": s.box_color, "opacity": s.box_opacity, "text": s.text_color,
                   "speaker": s.speaker_color, "scale": s.font_scale,
                   "mode": s.display_mode, "match": s.match_colors, "bgm": s.bg_mode,
                   "dx": s.tv_dx / 100, "dy": s.tv_dy / 100, "sx": s.tv_sx / 100, "sy": s.tv_sy / 100,
                   "calib": self.calib,
                   # TV ayar menüsü için mevcut değerler
                   "tts": s.tts_enabled, "spkcol": s.speaker_colors_on,
                   "cats": {"dialogue": s.cat_dialogue, "menu": s.cat_menu, "controls": s.cat_controls,
                            "other": s.cat_other, "nav": s.cat_nav},
                   "output": s.output_target,
                   # TV Ayarlar: oyun profili ve çeviri motoru seçimi
                   "profiles": self._profiles(), "profile": s.profile, "engine": s.engine,
                   "engines": ["local", "gemini", "free"]})

    @staticmethod
    def _profiles() -> list:
        try:
            from .config import list_profiles
            return list_profiles()
        except Exception:
            return []

    def set_visible(self, v: bool) -> None:
        self.visible = v
        self._put({"t": "visible", "v": v})

    def clear(self) -> None:
        self.state.clear()
        self._put({"t": "clear"})

    def reconnect(self) -> None:
        self.host = None
        self.settings.tv_host = ""
        self._put({"t": "__reconnect"})

    def stop(self) -> None:
        self.stop_evt.set()
        self._put({"t": "__stop"})

    def _put(self, obj: dict) -> None:
        if self.connected or obj["t"].startswith("__"):
            self.q.put((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))

    # --- arka plan
    def _find(self) -> str | None:
        cand = self.settings.tv_host
        if cand and probe(cand, 0.8):
            return cand
        self.status.emit(False, "TV aranıyor…")
        found = scan()
        if found:
            self.settings.tv_host = found
            try:
                self.settings.save()
            except Exception:
                pass
        return found

    def _run(self) -> None:
        while not self.stop_evt.is_set():
            if not self.settings.tv_enabled:
                self.status.emit(False, "TV çıkışı kapalı")
                time.sleep(2)
                continue
            host = self._find()
            if not host:
                self.status.emit(False, "TV bulunamadı (TV'de Brolis Game Translate (TV) açık mı?)")
                self.stop_evt.wait(5)
                continue
            try:
                self._session(host)
            except Exception as e:
                log.info("TV bağlantısı koptu: %s", e)
            self.connected = False
            self.status.emit(False, "TV bağlantısı koptu, yeniden deneniyor")
            self.stop_evt.wait(1.5)

    def _session(self, host: str) -> None:
        s = socket.create_connection((host, PORT), timeout=3)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(3)
        name = socket.gethostname()
        s.sendall((json.dumps({"t": "hello", "name": name}) + "\n").encode())
        f = s.makefile("rb")
        hello = json.loads(f.readline().decode() or "{}")
        if hello.get("app") != "trceviri-tv":
            raise ConnectionError("TV yanıtı beklenmedik")
        while not self.q.empty():          # eski kuyruk
            self.q.get_nowait()
        s.settimeout(10)   # TV her 2 sn pong döner
        self.connected = True
        self.host = host
        overlay_ok = hello.get("overlay", True)
        log.info("TV'ye bağlanıldı: %s (%sx%s)", host, hello.get("w"), hello.get("h"))
        self.status.emit(True, f"TV bağlı ({host})" + ("" if overlay_ok else " — TV'de ekran üstü izni yok!"))
        self.send_style()
        self._put({"t": "visible", "v": self.visible})
        for z, items in list(self.state.items()):
            self._put({"t": "items", "z": z, "items": items})

        def reader():
            try:
                while self.connected:
                    line = f.readline()
                    if not line:
                        break
                    if b"\"cal\"" in line or b"\"set\"" in line or b"\"visible\"" in line:
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            if msg.get("t") == "cal":
                                self.calib_request.emit(str(msg.get("a", "")))
                            elif msg.get("t") == "visible":          # TV Ayarlar: Türkçe yazılar aç/kapa
                                self.setting_request.emit("visible", bool(msg.get("v", True)))
                            elif msg.get("t") == "set":
                                self.setting_request.emit(str(msg.get("k", "")), msg.get("v"))
                        except Exception:
                            pass
            except Exception:
                pass
            self.connected = False
            self.q.put(b"")   # yazıcıyı uyandır

        threading.Thread(target=reader, daemon=True).start()
        last_ping = time.monotonic()
        try:
            while self.connected and not self.stop_evt.is_set():
                try:
                    data = self.q.get(timeout=1.0)
                except queue.Empty:
                    data = None
                if data:
                    if data.startswith(b'{"t": "__'):
                        break
                    s.sendall(data)
                if time.monotonic() - last_ping > 2.0:
                    s.sendall(b'{"t":"ping"}\n')
                    last_ping = time.monotonic()
        finally:
            self.connected = False
            try:
                s.close()
            except Exception:
                pass
