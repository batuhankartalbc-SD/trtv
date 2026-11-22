"""İlk kurulum sihirbazı: adım adım ilerler, son adımda canlı çeviriyi başlatır."""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from . import keystore, winutil
from .icons import pixmap
from .theme import ACCENT, MUTED, TEXT
from .translate import local_model_dir
from .widgets import Toggle, card, ibtn, iconlabel, sep

RP_EXE = Path(r"C:\Program Files (x86)\Sony\PS Remote Play\RemotePlay.exe")
RP_URL = "https://remoteplay.dl.playstation.net/remoteplay/lang/tr/index.html"
APK = Path(__file__).resolve().parent.parent / "TRCeviri-TV.apk"


def streaming() -> bool:
    """Remote Play PS5'e bağlı ve görüntü akıyor mu? (bağlıyken 'StreamingToolBar' penceresi oluşur)"""
    import ctypes
    from ctypes import wintypes
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _):
        n = winutil.user32.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            winutil.user32.GetWindowTextW(h, buf, n + 1)
            if buf.value == "StreamingToolBar":
                found.append(h)
        return True

    winutil.user32.EnumWindows(proc(cb), 0)
    return bool(found)


class Step(QWidget):
    def __init__(self, title: str, sub: str, ic: str):
        super().__init__()
        self.v = QVBoxLayout(self); self.v.setContentsMargins(0, 0, 0, 0); self.v.setSpacing(16)
        h = QHBoxLayout(); h.addWidget(iconlabel(ic, ACCENT, 40))
        col = QVBoxLayout(); col.setSpacing(2)
        t = QLabel(title); t.setObjectName("h2"); s = QLabel(sub); s.setObjectName("sub"); s.setWordWrap(True)
        col.addWidget(t); col.addWidget(s); h.addLayout(col, 1)
        self.v.addLayout(h); self.v.addWidget(sep())

    def text(self, html: str) -> QLabel:
        l = QLabel(html); l.setTextFormat(Qt.RichText); l.setWordWrap(True); l.setStyleSheet("font-size:15px;line-height:150%;")
        l.setOpenExternalLinks(True)
        self.v.addWidget(l)
        return l

    def status(self) -> tuple[QLabel, QLabel]:
        row = QHBoxLayout(); ic = QLabel(); lb = QLabel(); lb.setStyleSheet("font-size:16px;font-weight:700;")
        row.addWidget(ic); row.addWidget(lb); row.addStretch()
        self.v.addLayout(row)
        return ic, lb


class SetupWizard(QDialog):
    model_prog = Signal(int, str)

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.s = ctx.settings
        self.setWindowTitle("Brolis Game Translate — Kurulum")
        self.resize(1060, 680)
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        side = QWidget(); side.setObjectName("sidebar"); side.setFixedWidth(270)
        sv = QVBoxLayout(side); sv.setContentsMargins(22, 26, 18, 18); sv.setSpacing(4)
        from .widgets import brand_logo
        sv.addWidget(brand_logo(56))
        lg = QLabel(f"Brolis<br><span style='color:{ACCENT};font-size:15px'>Game Translate</span>"
                    f"<br><span style='color:{MUTED};font-size:14px'>kurulum</span>")
        lg.setObjectName("logo"); lg.setTextFormat(Qt.RichText); sv.addWidget(lg); sv.addSpacing(20)
        self.titles = ["Hoş geldiniz", "PS Remote Play", "Oyun ayarı", "Çeviri motoru", "Nerede görünsün?",
                       "TV kurulumu", "Hizalama", "Hazır"]
        self.step_labels = []
        for i, t in enumerate(self.titles):
            l = QLabel(f"{i + 1}.  {t}"); l.setStyleSheet("font-size:15px;padding:8px 10px;border-radius:8px;")
            self.step_labels.append(l); sv.addWidget(l)
        sv.addStretch()
        root.addWidget(side)

        main = QVBoxLayout(); main.setContentsMargins(34, 30, 34, 24); main.setSpacing(16)
        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)
        nav = QHBoxLayout()
        self.b_skip = ibtn("Sihirbazı kapat", None); self.b_skip.clicked.connect(self.reject)
        self.b_back = ibtn("Geri", "chev_left"); self.b_back.clicked.connect(lambda: self.goto(self.i - 1))
        self.b_next = ibtn("İleri", "chev_right", "primary"); self.b_next.clicked.connect(self.next)
        self.b_next.setMinimumWidth(200); self.b_next.setMinimumHeight(44)
        nav.addWidget(self.b_skip); nav.addStretch(); nav.addWidget(self.b_back); nav.addWidget(self.b_next)
        main.addLayout(nav)
        mw = QWidget(); mw.setLayout(main); root.addWidget(mw, 1)

        self._build()
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(1000)
        self.i = 0
        self.goto(0)

    # ---------------------------------------------------------------- adımlar
    def _build(self):
        # 1 hoş geldiniz
        st = Step("Hoş geldiniz!", "Birkaç adımda kuralım; en sonda canlı çeviri başlayacak.", "logo")
        st.text("Brolis Game Translate, PS5 oyunlarındaki İngilizce <b>konuşmaları, menüleri ve kontrolleri</b> anında Türkçeye çevirir ve "
                "İngilizcenin <b>tam üstüne, aynı boyutta</b> yazar — sanki oyun Türkçeymiş gibi.<br><br>"
                "<b>Nasıl çalışır?</b> Bilgisayarınız oyunu <b>PS Remote Play</b> ile izler, yazıları okur ve çevirir. "
                "Türkçe yazılar ister bilgisayar ekranında, ister TV'de (PS5'in görüntüsünün üstünde), ister ikisinde görünür.<br><br>"
                "Oyuna hiçbir şey yüklenmez, PS5'e dokunulmaz; sadece ekran okunur.")
        st.v.addStretch(); self.stack.addWidget(st)

        # 2 remote play
        st = Step("PS Remote Play'i bağlayın", "Bilgisayar oyunu bu uygulamadan izler.", "gamepad")
        st.text("1. PS Remote Play kurulu değilse indirip kurun.<br>"
                "2. Uygulamayı açın, PSN hesabınızla <b>giriş yapın</b> ve <b>PS5</b>'inizi seçin.<br>"
                "3. Oyun görüntüsü bilgisayara gelince bu adım kendiliğinden ✓ olur. "
                "Pencereyi küçültebilirsiniz; Brolis Game Translate arka planda okumaya devam eder.<br>"
                "<span style='color:#8C98A6'>İpucu: CouchSubs gibi başka bir Remote Play programı açıksa kapatın — PS5 aynı anda tek bağlantıya izin verir.</span>")
        row = QHBoxLayout()
        b1 = ibtn("İndirme sayfası", "download"); b1.clicked.connect(lambda: webbrowser.open(RP_URL))
        b2 = ibtn("PS Remote Play'i aç", "play", "outlineGreen"); b2.clicked.connect(self.open_rp)
        row.addWidget(b1); row.addWidget(b2); row.addStretch(); st.v.addLayout(row)
        self.rp_ic, self.rp_lb = st.status()
        st.v.addStretch(); self.stack.addWidget(st)

        # 3 oyun ayarı
        st = Step("Oyunda altyazıları açın", "Program sesi değil, ekrandaki İngilizce yazıyı okur.", "message")
        st.text("Oyunda <b>Options → Ayarlar</b> menüsüne girin ve <b>Altyazılar (Subtitles)</b> seçeneğini <b>Açık</b> yapın. "
                "Seçenek bulunamazsa <b>Erişilebilirlik</b>, <b>Ses</b> veya <b>Ekran</b> bölümlerine bakın. "
                "Altyazı boyutu ayarı varsa <b>Büyük</b> seçmek okumayı kolaylaştırır.")
        r = QHBoxLayout(); self.subs_ok = Toggle(False); r.addWidget(self.subs_ok); r.addWidget(QLabel("Altyazıları açtım")); r.addStretch()
        st.v.addLayout(r)
        st.v.addWidget(sep())
        g = QHBoxLayout()
        g.addWidget(QLabel("<b>Hangi oyunu oynuyorsunuz?</b>"))
        from .config import list_profiles
        self.game_combo = QComboBox(); self.game_combo.addItems(list_profiles()); self.game_combo.setMinimumWidth(300)
        self.game_combo.setCurrentText(self.s.profile)
        g.addWidget(self.game_combo); g.addStretch(); st.v.addLayout(g)
        st.text("<span style='color:#8C98A6'>Listede yoksa <b>Genel oyun (her oyun)</b> seçin — her oyunda çalışır. "
                "Film/dizi izliyorsanız <b>Film / dizi</b>. Oyun sırasında karakter isimleri tanınırsa uygulama "
                "doğru profile geçmeyi kendisi önerir.</span>")
        st.v.addStretch(); self.stack.addWidget(st)

        # 4 motor
        st = Step("Çeviri motoru", "Önerilen: Yerel (anlık, internetsiz). İsterseniz Gemini ile daha doğal çeviri.", "translate")
        self.eng_grp = QButtonGroup(self)
        has_local = local_model_dir() is not None
        opts = [("local", "Yerel — anlık, internetsiz (önerilen)",
                 "Satır başına ~0,1 sn. " + ("Model hazır ✓" if has_local else "Model bulunamadı — ücretsiz motora geçilir.")),
                ("gemini", "Yerel + Google Gemini ile iyileştirme",
                 "Önce yerel çeviri anında çıkar, Gemini'nin daha doğal çevirisi gelince yerini alır. Ücretsiz anahtar: aistudio.google.com"),
                ("free", "Ücretsiz internet servisi (MyMemory)", "Anahtar gerekmez; günlük sınırı vardır, daha yavaştır.")]
        for i, (k, t, d) in enumerate(opts):
            rb = QRadioButton(); self.eng_grp.addButton(rb, i)
            rb.setChecked((k == "local" and self.s.engine == "local" and not self.s.api_keys_enc.get("gemini")) or
                          (k == "gemini" and self.s.engine == "local" and bool(self.s.api_keys_enc.get("gemini"))) or
                          (k == "free" and self.s.engine == "free"))
            box = QHBoxLayout(); box.addWidget(rb); col = QVBoxLayout(); col.setSpacing(0)
            col.addWidget(QLabel(f"<b>{t}</b>")); dl = QLabel(d); dl.setObjectName("muted"); dl.setWordWrap(True); col.addWidget(dl)
            box.addLayout(col, 1); st.v.addLayout(box)
        if not has_local:
            mr = QHBoxLayout()
            self.b_dl = ibtn("Yerel modeli indir (≈450 MB, bir kere)", "download", "primary")
            self.dl_lb = QLabel(""); self.dl_lb.setObjectName("muted")
            self.b_dl.clicked.connect(self._dl_model)
            mr.addWidget(self.b_dl); mr.addWidget(self.dl_lb, 1); st.v.addLayout(mr)
            self.model_prog.connect(lambda p, m: (self.dl_lb.setText(m), self.b_dl.setEnabled("hazır" not in m)))
        self.gkey = QLineEdit(); self.gkey.setEchoMode(QLineEdit.Password)
        self.gkey.setPlaceholderText("Gemini API anahtarını buraya yapıştırın (AIza…)" if not self.s.api_keys_enc.get("gemini")
                                     else "•••••• kayıtlı (değiştirmek için yapıştırın)")
        st.v.addWidget(self.gkey)
        self.eng_grp.idToggled.connect(lambda i, on: self.gkey.setVisible(i == 1) if on else None)
        self.gkey.setVisible(self.eng_grp.checkedId() == 1)
        st.v.addStretch(); self.stack.addWidget(st)

        # 5 çıkış
        st = Step("Türkçe yazılar nerede görünsün?", "İstediğiniz zaman Ana sayfadan değiştirebilirsiniz.", "monitor")
        self.out_grp = QButtonGroup(self)
        row = QHBoxLayout(); row.setSpacing(14)
        for i, (k, ic, t, d) in enumerate((("tv", "tv", "Sadece TV", "PS5 TV'ye bağlı; Türkçe, TV'de oyunun tam üstünde."),
                                            ("pc", "monitor", "Sadece bilgisayar", "Oyunu bilgisayar ekranında Remote Play penceresinde oynuyorum."),
                                            ("both", "copy", "İkisinde de", "Hem TV'de hem bilgisayarda gösterilsin."))):
            b = QPushButton(); b.setCheckable(True); b.setMinimumSize(230, 170)
            b.setStyleSheet("QPushButton{border-radius:14px;text-align:left;padding:16px;} QPushButton:checked{border:2px solid %s;background:#0F2A21;}" % ACCENT)
            lay = QVBoxLayout(b); lay.addWidget(iconlabel(ic, ACCENT, 36))
            tl = QLabel(f"<b style='font-size:17px'>{t}</b>"); dl = QLabel(d); dl.setWordWrap(True); dl.setObjectName("muted")
            lay.addWidget(tl); lay.addWidget(dl); lay.addStretch()
            self.out_grp.addButton(b, i); b.setProperty("key", k); row.addWidget(b)
            if self.s.output_target == k:
                b.setChecked(True)
        self.out_grp.setExclusive(True)
        st.v.addLayout(row)
        st.v.addStretch(); self.stack.addWidget(st)

        # 6 TV
        st = Step("TV'ye Brolis Game Translate (TV)'yi kurun", "Bir kere yapılır. Bilgisayar ve TV aynı modeme bağlı olmalı.", "tv")
        st.text("1. TV'de Google Play'den <b>Downloader</b> uygulamasını kurun.<br>"
                "2. TV <b>Ayarlar → Sistem → Hakkında</b>'da <b>Android TV OS derlemesi</b>ne 7 kez basın (geliştirici modu); "
                "<b>Ayarlar → Uygulamalar → Güvenlik → Bilinmeyen uygulamalar</b>'da Downloader'a izin verin.<br>"
                "3. Downloader'a şu adresi yazın ve kurun:<br>"
                "&nbsp;&nbsp;&nbsp;<b style='color:#3EE6A0'>github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk</b><br>"
                "4. TV'de <b>Brolis Game Translate (TV)</b>'yi açın, <b>ekran üstünde gösterme</b> iznini verin, <b>Oyuna dön</b>'e basın.<br>"
                "TV bulunduğunda bu adım kendiliğinden ✓ olur.")
        b = ibtn("APK dosyasının klasörünü aç", "folder"); b.clicked.connect(lambda: os.startfile(str(APK.parent)))
        st.v.addWidget(b, 0, Qt.AlignLeft)
        self.tv_ic, self.tv_lb = st.status()
        st.v.addStretch(); self.stack.addWidget(st)

        # 7 hizalama
        st = Step("Hizalama (isteğe bağlı)", "Türkçe, TV'de İngilizcenin tam üstüne otursun.", "target")
        st.text("Önce TV'nin görüntü ayarında <b>Ekran boyutu</b>nu <b>Tam piksel / Just Scan</b> yapın.<br>"
                "Sonra aşağıdan <b>Hizalama modu</b>nu açın: TV'de okunan İngilizce yazıların çevresinde mavi çerçeveler çıkar. "
                "Çerçeveler İngilizcenin tam üstüne oturana kadar oklarla kaydırın, gerekirse büyütün/küçültün. "
                "(Oyun sırasında klavyeden: <b>Ctrl+Alt+Oklar</b>, <b>Ctrl+Alt+PgUp/PgDn</b>.)<br>"
                "Zaten oturuyorsa bu adımı geçebilirsiniz.")
        row = QHBoxLayout()
        self.b_cal = ibtn("Hizalama modunu aç", "target", "outlineGreen"); self.b_cal.setCheckable(True)
        self.b_cal.toggled.connect(lambda on: (self.ctx.calibrate("CAL_MODE") if on != self.ctx.tv.calib else None,
                                               self.b_cal.setText("  Hizalama modunu kapat" if on else "  Hizalama modunu aç")))
        row.addWidget(self.b_cal)
        for ic, act in (("chev_left", "CAL_LEFT"), ("chev_up", "CAL_UP"), ("chev_down", "CAL_DOWN"), ("chev_right", "CAL_RIGHT"),
                        ("zoom_in", "CAL_BIGGER"), ("zoom_out", "CAL_SMALLER")):
            bb = ibtn("", ic); bb.setFixedWidth(52); bb.setAutoRepeat(True); bb.setAutoRepeatInterval(120)
            bb.clicked.connect(lambda _=False, a=act: self.ctx.calibrate(a)); row.addWidget(bb)
        row.addStretch(); st.v.addLayout(row)
        st.v.addStretch(); self.stack.addWidget(st)

        # 8 hazır
        st = Step("Her şey hazır!", "Canlı çeviriyi başlatın ve oynamaya başlayın.", "check")
        self.summary = st.text("")
        st.text("<span style='color:#8C98A6'>Kısayollar: <b>F8</b> Türkçeyi gizle/göster · <b>F9</b> duraklat · "
                "<b>F11</b> son satırı yeniden çevir. Bu sihirbazı istediğiniz zaman sol menüden yeniden açabilirsiniz.</span>")
        st.v.addStretch(); self.stack.addWidget(st)

    # ---------------------------------------------------------------- gezinme
    def _output(self) -> str:
        b = self.out_grp.checkedButton()
        return b.property("key") if b else "both"

    def _skip(self, i: int) -> bool:
        return i in (5, 6) and self._output() == "pc"

    def goto(self, i: int):
        i = max(0, min(len(self.titles) - 1, i))
        self.i = i
        self.stack.setCurrentIndex(i)
        for k, l in enumerate(self.step_labels):
            skip = self._skip(k)
            if k == i:
                l.setStyleSheet(f"font-size:15px;padding:8px 10px;border-radius:8px;background:#0F2A21;color:{ACCENT};font-weight:700;")
            else:
                l.setStyleSheet(f"font-size:15px;padding:8px 10px;color:{'#4A5664' if skip else (TEXT if k < i else MUTED)};")
        self.b_back.setEnabled(i > 0)
        last = i == len(self.titles) - 1
        self.b_next.setText("  Canlı çeviriyi başlat" if last else "  İleri")
        self.b_next.setIcon(self.b_next.icon())
        if last:
            self._fill_summary()
        self.poll()

    def next(self):
        if self.i == 3:
            self._apply_engine()
        if self.i == 4:
            self.s.set_output(self._output()); self.s.save()
            self.ctx.window.set_output(self.s.output_target)
        if self.i == len(self.titles) - 1:
            self.finish(); return
        j = self.i + 1
        while self._skip(j):
            j += 1
        self.goto(j)

    def _apply_engine(self):
        k = self.eng_grp.checkedId()
        if k == 2:
            self.s.engine = "free"
        else:
            self.s.engine = "local"
            self.s.refine = k == 1
            if k == 1 and self.gkey.text().strip():
                self.s.api_keys_enc["gemini"] = keystore.encrypt(self.gkey.text().strip()); self.gkey.clear()
        self.s.save()

    def _dl_model(self):
        import threading
        from .translate import download_model
        self.b_dl.setEnabled(False)
        threading.Thread(target=lambda: download_model(lambda p, m: self.model_prog.emit(p, m)), daemon=True).start()

    def open_rp(self):
        if RP_EXE.exists():
            os.startfile(str(RP_EXE))
        else:
            webbrowser.open(RP_URL)

    def poll(self):
        if not hasattr(self, "rp_ic"):
            return
        if self.i == 1:
            if streaming():
                self.rp_ic.setPixmap(pixmap("check", ACCENT, 26)); self.rp_lb.setText("PS5 bağlı, oyun görüntüsü geliyor")
            elif winutil.find_window(self.s.window_hint):
                self.rp_ic.setPixmap(pixmap("dot", MUTED, 26)); self.rp_lb.setText("Remote Play açık — giriş yapıp PS5'i seçin")
            else:
                self.rp_ic.setPixmap(pixmap("dot", MUTED, 26)); self.rp_lb.setText("PS Remote Play açık değil" +
                                                                                 ("" if RP_EXE.exists() else " (kurulu görünmüyor)"))
        if self.i == 5:
            ok = self.ctx.tv.connected
            self.tv_ic.setPixmap(pixmap("check" if ok else "dot", ACCENT if ok else MUTED, 26))
            self.tv_lb.setText(f"TV bağlı ({self.ctx.tv.host})" if ok else "TV aranıyor… (TV'de Brolis Game Translate (TV) açık mı?)")

    def _fill_summary(self):
        out = {"pc": "Bilgisayar ekranı", "tv": "TV", "both": "TV ve bilgisayar"}[self.s.output_target]
        eng = {"local": "Yerel (anlık)" + (" + Gemini iyileştirme" if self.s.refine and self.s.api_keys_enc.get("gemini") else ""),
               "free": "Ücretsiz internet servisi"}.get(self.s.engine, self.s.engine)
        rp = "bağlı ✓" if streaming() else "henüz bağlı değil — başlatınca bekler"
        tv = ("bağlı ✓" if self.ctx.tv.connected else "aranıyor") if self.s.output_target != "pc" else "kullanılmıyor"
        self.summary.setText(f"<b>Çeviri:</b> {eng}<br><b>Görüneceği yer:</b> {out}<br><b>PS Remote Play:</b> {rp}<br>"
                             f"<b>TV:</b> {tv}<br><b>Çevrilecekler:</b> konuşmalar, menüler, kontroller (GPS ve diğer yazılar kapalı — "
                             f"Çeviri sayfasından değiştirilebilir)")

    def finish(self):
        if self.ctx.tv.calib:
            self.ctx.calibrate("CAL_MODE")
        self.s.setup_done = True
        self.s.save()
        game = self.game_combo.currentText() if hasattr(self, "game_combo") else ""
        if game and game != self.s.profile:
            self.ctx.window.change_profile(game)
        self.accept()
        self.ctx.window.restart_if_running()
        self.ctx.window.start()
        self.ctx.window.go(0)
