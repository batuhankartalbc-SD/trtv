# Codex — Toplu görev (9 + 10) — Brolis Game Translate

Kullanıcı uyuyor; sabaha kadar hepsini sırayla bitir. Her alt görev ayrı commit olsun, her birinden sonra push et.
Önce `git pull`, sonra `GELISTIRME_NOTLARI.md` dosyasını oku.

**Kurallar**
- Senin alanın: `app/`, `.github/workflows/`, `brand/`, kök `README.md`, `contrib/`.
- `trceviri/` klasörüne dokunma. Claude aynı anda orada çalışıyor (PC 2.3.4: tam ekran düzeni).
- Push öncesi her zaman `git pull --rebase`.
- Bitince notların "Günlük" bölümüne her görev için kısa kayıt ekle: değişen dosyalar, TV build numarası, test sonucu.

PC 2.3.3 yayında. `style` mesajında yeni alanlar var:
- `pcver`: PC sürümü (ör. "2.3.3").
- `refine`: `null` ise Gemini kapalı. Değilse Türkçe durum metni: "hazır", "çalışıyor", "kota doldu (10 dk ara)", "geçersiz istek/anahtar (5 dk ara)".

---

## A. TV Ayarlar: durum satırı
- Ayarlar menüsünün en altına küçük gri bir satır ekle: `PC 2.3.3 · TV 1.xx · Gemini: <durum>`.
- `refine` null ise "Gemini: kapalı" yaz.
- Metin "kota" ya da "geçersiz" içeriyorsa sarı renkte göster.
- `pcver` yoksa ya da "2.3.0"dan küçükse sarı uyarı göster: "Bilgisayardaki uygulamayı güncelleyin".

## B. TV: kumanda yardım ekranı
- Ayarlar'a "Kumanda tuşları" satırı ekle. Açılınca kodda tanımlı gerçek tuşları tek sayfada listelesin: hizalama, boyut, göster/gizle, tekrar oku vb.
- Hizalama modu ilk kez açılınca üstte 5 sn ipucu şeridi göster.
- Şerit bir kez gösterildikten sonra bunu SharedPreferences'a kaydet; bir daha gösterme.

## C. TV: bağlantı dayanıklılığı
- Kullanıcıda PC "TV bulunamadı" dedi, oysa TV uygulaması kuruluydu. Muhtemelen APK güncellemesinden sonra servis kendiliğinden başlamadı.
- Uygulama güncellenince `MY_PACKAGE_REPLACED` ile servisi otomatik başlat. BootReceiver'a bu action'ı ekle.
- Servis öldürülürse `START_STICKY` ile geri gelsin. Bunu kontrol et ve gerekirse düzelt.
- TV uygulaması ön plandayken ekranda "PC bekleniyor… IP: 192.168.x.x port 47800" yazsın; kullanıcı neyi kontrol edeceğini bilsin.

## D. CI: PC testleri
- `.github/workflows/pc-tests.yml` ekle: `windows-latest`, Python 3.11, `pip install pytest PySide6 numpy`, `pytest trceviri/tests -q`.
- Sadece `trceviri/**` değişince çalışsın.
- Eksik paket yüzünden test kırılırsa hangi paket olduğunu notlara yaz; `trceviri/` içine yazma, Claude ekler.

## E. contrib: GTA 6 çeviri paketi
- `contrib/gta6_extra.json` dosyasına 150+ yeni satır ekle:
  - görev hedefleri ("Get in the car.", "Lose the cops.", "Go to the ...")
  - telefon ve menü metinleri (Map, Brief, Settings, Resume, Quit Game ...)
  - kontrol ipuçları ("Press X to ...", "Hold R2 to ...")
- Biçim: `{"İngilizce": "Türkçe"}`.
- Kısa ve doğal oyun dili kullan. Tırnak ya da emoji olmasın. TAMAMI BÜYÜK HARF olan satır büyük harf kalsın.

## F. README: arkadaşlar için "İlk 5 dakika"
- Kök README'nin en üstüne şu adımları ekle:
  1. PC kurulum dosyası (`pc-latest` sürümündeki `TRCeviri-Kurulum.exe`)
  2. TV APK (`latest` sürümündeki `a.apk`) ve TV'ye yükleme yolu (Downloader ya da USB)
  3. PC ile TV aynı Wi-Fi'da olmalı
  4. Kurulum sihirbazını sonuna kadar izle
  5. Kısayollar: F8 katman, F9 duraklat, F6 son konuşma, F10 bölgeler, F11 yeniden çevir
- Altına sorun giderme tablosu ekle. Satırlar: "TV bulunamadı", "Türkçe gelmiyor", "Yazılar kayıyor", "Gemini kota doldu", "Pencere bulunamadı". Her biri için çözümü yaz.

## G. brand: mağaza görselleri
- `brand/store/` klasörüne 1280x720 iki tanıtım görseli koy:
  1. Önce/sonra: İngilizce altyazı → Türkçe altyazı
  2. "PC + TV" bağlantı şeması
- README bunları göstersin.

Son adımda notlara özet yaz: hangi görevler tamam, hangileri yarım kaldı ve neden.
