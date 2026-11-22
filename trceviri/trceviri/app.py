"""Uygulama kurulumu ve yaşam döngüsü."""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from . import applog, winutil
from .cache import TranslationCache
from .config import CACHE_FILE, Profile, Settings, load_profile
from .hotkeys import Hotkeys
from .main_window import MainWindow
from .overlay import Overlay
from .pipeline import Pipeline
from .theme import QSS
from .tvlink import TvLink

log = logging.getLogger("uygulama")


class AppContext:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.settings = Settings.load()
        self.profile = load_profile(self.settings.profile)
        self.cache = TranslationCache(CACHE_FILE)
        self.pipeline = Pipeline(self.settings, self.profile, self.cache)
        self.overlay = Overlay(self.settings, self.pipeline)
        self.tv = TvLink(self.settings)
        self.pipeline.listeners.append(self.tv.send_items)
        self.tv.calib_request.connect(self.calibrate_from_tv)
        self.tv.setting_request.connect(self.setting_from_tv)
        self.tv.ocr_request.connect(self.translate_for_tv)
        from .tts import Speaker
        self.pipeline.tts = Speaker(self.settings)
        self.window = MainWindow(self)
        self.window.show()
        self.hotkeys = Hotkeys(qapp, int(self.window.winId()))
        self.hotkeys.pressed.connect(self.on_hotkey)
        if self.hotkeys.failed:
            log.warning("Bu kısayollar başka bir program tarafından kullanılıyor: %s", ", ".join(self.hotkeys.failed))
        log.info("Brolis Game Translate hazır. Profil: %s, motor: %s", self.profile.name, self.settings.engine)

    def set_profile(self, p: Profile) -> None:
        running = self.pipeline.running.is_set()
        if running:
            self.pipeline.stop()
        self.profile = p
        self.pipeline.profile = p
        self.overlay.zone_items.clear()
        self.overlay.update()
        self.tv.clear()
        if running:
            self.pipeline.start()

    def on_hotkey(self, name: str) -> None:
        if name == "F8":
            self.overlay.toggle()
            self.tv.set_visible(self.overlay.visible_flag)
            log.info("Çeviri katmanı %s", "açık" if self.overlay.visible_flag else "gizli")
        elif name == "F9":
            self.pipeline.paused = not self.pipeline.paused
            log.info("Çeviri %s", "duraklatıldı" if self.pipeline.paused else "devam ediyor")
        elif name == "F10":
            self.window.showNormal(); self.window.activateWindow()
            self.window.open_zone_editor()
        elif name == "F11":
            if self.pipeline.manager:
                self.pipeline.retranslate_last()
        elif name == "F6":
            self.show_history()
        elif name.startswith("CAL_"):
            self.calibrate(name)
        elif name == "F7":
            self.settings.debug_boxes = not self.settings.debug_boxes
            self.window.dbg_chk.setChecked(self.settings.debug_boxes)
            self.overlay.update()

    def show_history(self) -> None:
        """F6: son konuşmayı birkaç saniye tekrar göster; arka arkaya basınca daha eskilere gider."""
        from PySide6.QtCore import QTimer
        h = list(self.pipeline.history)
        if not h:
            log.info("Geçmişte konuşma yok")
            return
        import time as _t
        now = _t.monotonic()
        self._hist_i = (getattr(self, "_hist_i", 0) + 1) if now - getattr(self, "_hist_t", 0) < 4 else 1
        self._hist_t = now
        it = h[-min(self._hist_i, len(h))].copy()
        it.src = it.src + " "               # takipçiyle karışmasın
        self.pipeline.publish("history", [it])
        if not hasattr(self, "_hist_timer"):
            self._hist_timer = QTimer(); self._hist_timer.setSingleShot(True)
            self._hist_timer.timeout.connect(lambda: self.pipeline.publish("history", []))
        self._hist_timer.start(4500)

    def open_wizard(self) -> None:
        from .wizard import SetupWizard
        self.wizard = SetupWizard(self, self.window)
        self.wizard.show()

    def translate_for_tv(self, rid: int, lines: list, src: str) -> None:
        """TV bağımsız mod: TV'nin okuduğu İngilizce satırları bilgisayarın motoru, oyun paketi ve önbelleğiyle çevirir.
        Hazır olanlar hemen, kalanlar çevrildikçe aynı id ile tekrar gönderilir (Gemini iyileştirmesi de)."""
        p = self.pipeline
        try:
            mgr = p.ensure_manager()
        except Exception as e:
            log.warning("TV çevirisi başlatılamadı: %s", e)
            return
        from .pipeline import film_clean
        from .textproc import normalize
        out = [""] * len(lines)
        pending: dict[str, list[int]] = {}
        for i, en in enumerate(lines):
            en = film_clean(normalize(str(en)))
            if not en or "♪" in en or "♫" in en:
                continue
            hit = p.lookup(en)
            if hit:
                out[i] = hit
            else:
                pending.setdefault(en, []).append(i)
        self.tv.send_tr(rid, out)
        for en, idxs in pending.items():
            def done(text, tr, engine, ms, idxs=idxs):
                if not tr:
                    return
                p.cache.put(p.scope, text, tr, engine)
                p.record(text, tr, engine, ms)
                for i in idxs:
                    out[i] = tr
                self.tv.send_tr(rid, out)
            mgr.submit(en, 0, True, done)

    def setting_from_tv(self, key: str, value) -> None:
        """TV kumandasından ayar değişikliği (Brolis Game Translate (TV) → Ayarlar). Sadece güvenli, bilinen ayarlar."""
        s = self.settings
        try:
            if key == "font_scale":
                s.font_scale = max(0.6, min(2.5, round(float(value), 2)))
            elif key == "bg_opacity":                       # TV Ayarlar: yazı arkası opaklığı (%0–100)
                s.box_opacity = max(0, min(255, round(float(value) * 255 / 100)))
            elif key == "bg_mode" and value in ("black", "semi", "none", "game"):
                s.display_mode = "match"; s.bg_mode = value
            elif key == "visible":
                if bool(value) != self.overlay.visible_flag:
                    self.overlay.toggle()
                self.tv.set_visible(bool(value))
            elif key in ("tts_enabled", "speaker_colors_on", "cat_dialogue", "cat_menu", "cat_controls", "cat_other", "cat_nav"):
                setattr(s, key, bool(value))
                if key.startswith("cat_"):
                    self.overlay.zone_items.clear(); self.tv.clear(); self.pipeline.reload_zones()
            elif key == "profile" and isinstance(value, str):
                from .config import list_profiles
                if value in list_profiles():
                    self.window.change_profile(value)
                    self.window.prof_combo.blockSignals(True); self.window.prof_combo.setCurrentText(value)
                    self.window.prof_combo.blockSignals(False)
            elif key == "engine" and value in ("local", "gemini", "free"):
                s.engine = value
                s.save()
                self.window.restart_if_running()
            elif key == "font" and value in ("default", "condensed", "rounded", "clean"):
                from .fonts import available
                s.font_choice = value if value in available() else "default"
                if hasattr(self.window, "font_combo"):
                    self.window.font_combo.blockSignals(True)
                    self.window.font_combo.setCurrentIndex(max(0, self.window.font_combo.findData(s.font_choice)))
                    self.window.font_combo.blockSignals(False)
            elif key == "replay":
                self.show_history()
                return
            elif key == "fps":
                s.fps = max(5, min(60, int(value)))
                self.window.sync_from_settings()
            elif key == "instant":
                s.instant = bool(value)
                self.window.sync_from_settings()
            elif key == "output" and value in ("pc", "tv", "both"):
                self.window.set_output(value)
                return
            else:
                log.info("TV'den bilinmeyen ayar: %s", key)
                return
        except Exception as e:
            log.warning("TV ayarı uygulanamadı (%s=%s): %s", key, value, e)
            return
        s.save()
        self.tv.send_style()
        self.overlay.update()
        log.info("TV kumandasından ayar: %s = %s", key, value)

    def calibrate_from_tv(self, action: str) -> None:
        """TV kumandasından gelen hizalama komutları (CalibrateActivity)."""
        if action == "CAL_MODE_ON":
            if not self.tv.calib:
                self.calibrate("CAL_MODE")
        elif action == "CAL_MODE_OFF":
            if self.tv.calib:
                self.calibrate("CAL_MODE")
        elif action.startswith("CAL_"):
            self.calibrate(action)

    def calibrate(self, action: str) -> None:
        """TV hizalaması: kaydırma %0.2, ölçek %0.5 adımlarla; değişiklik anında TV'ye gider ve kaydedilir."""
        s = self.settings
        if action == "CAL_MODE":
            self.tv.calib = not self.tv.calib
            log.info("TV hizalama modu %s", "AÇIK: çerçeveleri İngilizcenin üstüne oturtun" if self.tv.calib else "kapalı")
        elif action == "CAL_RESET":
            s.tv_dx = s.tv_dy = 0.0
            s.tv_sx = s.tv_sy = 100.0
        else:
            step, sstep = 0.2, 0.5
            if action == "CAL_LEFT": s.tv_dx = round(s.tv_dx - step, 2)
            if action == "CAL_RIGHT": s.tv_dx = round(s.tv_dx + step, 2)
            if action == "CAL_UP": s.tv_dy = round(s.tv_dy - step, 2)
            if action == "CAL_DOWN": s.tv_dy = round(s.tv_dy + step, 2)
            if action == "CAL_BIGGER": s.tv_sx = round(s.tv_sx + sstep, 2); s.tv_sy = round(s.tv_sy + sstep, 2)
            if action == "CAL_SMALLER": s.tv_sx = round(s.tv_sx - sstep, 2); s.tv_sy = round(s.tv_sy - sstep, 2)
        s.save()
        self.tv.send_style()
        self.window.sync_calib()

    def shutdown(self) -> None:
        try:
            self.pipeline.stop()
            self.tv.clear()
            self.tv.stop()
        finally:
            self.hotkeys.unregister()
            self.settings.save()
            self.overlay.close()


_MUTEX = None


def single_instance() -> bool:
    """Aynı ortamda ikinci kopya açılmasın (kısayol tuşları ve TV bağlantısı çakışır). Açıksa onu öne getir."""
    global _MUTEX
    import ctypes
    from .config import DEV
    name = "Local\\BrolisGameTranslate" + ("-Dev" if DEV else "")
    _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    if ctypes.windll.kernel32.GetLastError() != 183:      # ERROR_ALREADY_EXISTS değil
        return True
    for h, t in winutil.list_windows():
        if t.startswith(("Brolis Game Translate —", "[GELİŞTİRME] Brolis Game Translate")):
            winutil.user32.ShowWindow(h, 9)                  # SW_RESTORE
            winutil.user32.SetForegroundWindow(h)
            break
    return False


def main() -> int:
    winutil.set_dpi_aware()
    if not single_instance():
        return 0
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("Brolis Game Translate")
    qapp.setStyle("Fusion")
    qapp.setStyleSheet(QSS)
    applog.setup()
    ctx = AppContext(qapp)
    qapp.aboutToQuit.connect(ctx.shutdown)
    if not ctx.settings.setup_done and "--baslat" not in sys.argv:   # ilk açılış: kurulum sihirbazı
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, ctx.open_wizard)
    if "--baslat" in sys.argv:   # açılır açılmaz çeviriyi başlat (pencere çıkana kadar bekler)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, ctx.window.toggle_run)
    if "--hizala" in sys.argv:   # TV hizalama modunda başla
        ctx.tv.calib = True
        ctx.window.sync_calib()
    return qapp.exec()
