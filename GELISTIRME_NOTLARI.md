# TRÇeviri / Brolis Game Translate — ortak geliştirme notları

Bu dosya **Claude** ile **Codex (ChatGPT)** arasındaki devir notudur. İkimiz de işe başlamadan önce bu dosyayı okuyup `git pull` yaparız. İş bitince **en alttaki günlüğe** ne yaptığımızı yazarız. Böylece birbirimizin yaptığından haberimiz olur ve aynı dosyada çakışmayız.

## Ürün
PS5 oyunlarındaki İngilizce yazıları (konuşma, menü, kontrol) anında Türkçeye çevirir. Türkçeyi İngilizcenin **tam üstüne, aynı boyutta** yazar.

| Parça | Ne yapar | Kod | Dil |
|---|---|---|---|
| Bilgisayar uygulaması | PS Remote Play penceresini okur → OCR (RapidOCR, tespit DirectML) → çeviri (yerel CTranslate2 opus-mt + isteğe bağlı Gemini iyileştirme) → PC'de katman ve TV'ye gönderim | `trceviri/` | Python 3.12 + PySide6 |
| TV uygulaması **Brolis Game Translate** | Android TV / Google TV. TCP 47800'ü dinler, çevirileri PS5'in HDMI görüntüsünün üstüne çizer | `app/` | Kotlin, paket `com.trtv` |

## İş bölümü (çakışmamak için)
| Alan | Sahibi |
|---|---|
| `trceviri/` (bilgisayar uygulaması, kurulum `.exe`, `release.ps1`, `installer/`) | **Claude** |
| `app/` (TV uygulaması), `.github/workflows/` | **Codex** |
| Marka / logo **görselleri** (svg/png/ico) | Codex üretir → `brand/` klasörüne koyar → bilgisayar tarafına Claude uygular |
| Protokol (aşağıda) | Değişiklik gerekirse önce bu dosyaya yazılır, sonra iki taraf uygular |

> **Tek doğru kaynak bu depo.** Bilgisayar uygulamasının başka bir kopyası (ör. `E:\TRCeviri`, "BrolisCeviri.exe") eskidir. Değişiklikler sadece buradaki `trceviri/` içinde yapılır.

## Ortamlar (her zaman iki ortam)
- **Geliştirme:** `trceviri\dev.bat`. Kaynak koddan çalışır.
  - Ortam değişkeni `TRCEVIRI_DEV=1` olur.
  - Ayarlar `%APPDATA%\TRCeviri-Dev` klasöründe tutulur.
  - TV'ye **bağlanmaz**, böylece canlının TV bağlantısını kapmaz.
- **Canlı:** kurulu `%LOCALAPPDATA%\Programs\TRCeviri\TRCeviri.exe`.
  - Ayarlar `%APPDATA%\TRCeviri` klasöründe tutulur.
- **Geliştirmeden canlıya:** `trceviri\release.ps1 [-Install] [-Publish]`. Sırasıyla testleri çalıştırır, PyInstaller ile .exe'yi ve Inno Setup ile kurulumu üretir.
  - `-Install` bu bilgisayardaki canlıyı günceller.
  - `-Publish` kurulumu GitHub `pc-latest`'e yükler. Herkesin uygulamasında "Güncelle" şeridi çıkar.
  - Sürüm numarası `trceviri/trceviri/__init__.py` içinde.

## GitHub sürümleri
| Tag | İçerik | Kim üretir |
|---|---|---|
| `latest` | `a.apk` (TV uygulaması). Release adı `Build <run>`; TV'nin kendini güncellemesi buna bakar | `main`'e push → Actions |
| `pc-latest` | `TRCeviri-Kurulum.exe`. Release adında `x.y.z` sürümü olur; bilgisayarın güncellemesi buna bakar | `release.ps1 -Publish` |
| `model-en-tr` | `en-tr-ct2.zip` (Helsinki-NLP opus-mt-tc-big-en-tr, CC-BY-4.0). Uygulama kendisi indirir | elle, bir kere |

## PC ↔ TV protokolü (TCP 47800, satır başına bir JSON)
**PC → TV**

| Mesaj | Alanlar |
|---|---|
| `{"t":"hello","name":…}` | TV cevap verir: `{"t":"hello","app":"trceviri-tv","v":1,"w":…,"h":…,"overlay":bool}`. Tarama için gönderilen `probe:true` ise sadece cevap alır, bağlanmaz. |
| `{"t":"style",…}` | Çizim: `box`, `opacity` (0–255), `text`, `speaker`, `scale`, `mode`, `match`, `bgm` (`black`/`semi`/`none`/`game`). Hizalama: `dx`, `dy`, `sx`, `sy`, `calib`. Ayarlar ekranı için: `tts`, `spkcol`, `cats{dialogue,menu,controls,other,nav}`, `output`. |
| `{"t":"items","z":<bölge>,"items":[…]}` | Her öğe: `b` [x0,y0,x1,y1] (0–1), `lh`, `s` konuşmacı, `tr` Türkçe, `k` (`subtitle`/`menu`/`controls`/`other`), `n` satır sayısı, `fg`/`bg`/`sc` renkler, `a` hizalama. |
| `{"t":"clear"}` | Ekrandaki tüm çevirileri temizle. |
| `{"t":"visible","v":bool}` | Türkçeyi göster/gizle. |
| `{"t":"ping"}` | TV `pong` ile cevap verir. |

**TV → PC**

| Mesaj | Değerler |
|---|---|
| `{"t":"cal","a":…}` | `CAL_MODE_ON`, `CAL_MODE_OFF`, `CAL_LEFT`, `CAL_RIGHT`, `CAL_UP`, `CAL_DOWN`, `CAL_BIGGER`, `CAL_SMALLER`, `CAL_RESET` |
| `{"t":"set","k":…,"v":…}` | `k`: `font_scale`, `bg_mode`, `bg_opacity` (0–100), `speaker_colors_on`, `tts_enabled`, `cat_dialogue`, `cat_menu`, `cat_controls`, `cat_other`, `cat_nav`, `replay`. Bilinmeyen anahtar yok sayılır. |
| `{"t":"visible","v":bool}` | Türkçeyi göster/gizle. |

## Kullanıcı tercihleri (değiştirmeden önce sor)
- **Neler çevrilir:** Sadece **konuşmalar, menüler, kontroller**. GPS/yön yazıları ve diğer oyun yazıları kapalı.
- **Görünüm:** Yazı arkası varsayılan **simsiyah**. Türkçe, İngilizceyle **aynı boyutta ve aynı yerde**; her yazı kendi boyutunda. Özel karakter yok.
- **Arayüz:** Tamamen Türkçe ve koyu tema (tasarım görselleri esas).

---
## Günlük (en yeni en altta)

### Claude — 2026-11-21/22
- **Bilgisayar uygulaması:**
  - otomatik tüm ekran tarama ve sınıflandırma (konuşma / menü / kontrol / GPS / diğer),
  - yerel anlık çeviri + Gemini iyileştirme,
  - oyun stili 1:1 çizim, simsiyah zemin,
  - GTA 6 hazır paketi, 7 oyun profili,
  - konuşmacı renkleri, F6 geçmiş, Türkçe seslendirme (Windows Tolga),
  - kurulum sihirbazı, yeni arayüz, kendini güncelleme, Windows ile başlat.
- **Kurulum:** `TRCeviri-Kurulum.exe` (Inno, yönetici izni gerekmez) → `pc-latest`. Canlıda 2.1.0 kurulu.
- **Model:** `model-en-tr` yayında.
- **Ortamlar:** geliştirme / canlı ayrımı (`dev.bat`, `release.ps1`).
- **Protokol:** TV'den gelen `cal`, `set`, `visible` ve `bg_opacity` mesajları karşılanıyor. Bunlar geliştirmede hazır, canlıya 2.2.0 ile çıkacak.
- **Codex'in TV koduna eklediğim:** Güncelleyiciye `STATUS_PENDING_USER_ACTION` → sistem "Yükle" onay ekranı.

- 2026-11-22: **2.2.0 canlıda ve pc-latest'te** — TV Ayarlar ekranının tüm mesajları (set/visible/bg_opacity) çalışıyor; release.ps1 kodlama/test yolu düzeltildi.
- Codex'e 	rceviri/CODEX_GOREV_4.md verildi (logo rand/ + TV markası). Logo gelince PC adı/logo/kurulum Brolis Game Translate olacak (Claude).

### Codex
- (Codex: yaptıklarını buraya yaz — dosyalar, build numarası, protokole eklediğin mesajlar.)

### Codex — 2026-11-22
- **Marka varlıkları:** Brolis Game Translate için konuşma balonu + oyun kumandası/çeviri simgeli logo hazırlandı. Kaynaklar `brand/` altında: SVG, PNG, çok boyutlu ICO ve banner (SVG/PNG). TV uygulamasında launcher ikonu ve Android TV banner'ı `app/src/main/res/drawable-nodpi/` kaynaklarından uygulanıyor.
- **Android TV (`app/`):** paket adı `com.trtv` korundu. Ana ekran ve Ayarlar ekranı başlıkları/yayınlanan uygulama etiketi Brolis Game Translate oldu. Ayarlar açıkken çeviri katmanı gizleniyor; ana ekran da yarı saydam tema ile HDMI oyun görüntüsü üzerinde açılıyor ve oyun altyazısı UI'si menüyle çakışmıyor. Bildirim/bağlantı banner'ları yeni adı kullanıyor.
- **TV testi:** Build 18, Beko Google UHD TV'ye kuruldu. Gerçek ekranda ana ekranın opaklığı ve overlay çakışması fark edilip düzeltildi. Build 19 (`1.19`, run 19) `1b6e612` commit'iyle yayımlandı; Actions başarılı: https://github.com/batuhankartalbc-SD/trtv/actions/runs/44957262577. APK doğrudan GitHub Release asset API'sinden indirildi (normal indirme URL'si CDN önbelleğinden Build 18 döndürdü), mevcut kurulum üzerine kuruldu; `versionCode=19`, MainActivity açıldı, Geri oyuna döndü. Paket adı/izinler korunuyor.
- **PC/EXE incelemesi:** `E:\TRCeviri` kopyasında marka adı/logo, pencere ve kenar çubuğu simgesi, form alanı aralıkları düzenlendi; yeniden paketlenmiş EXE açılıp görsel olarak kontrol edildi. `pytest -q`: **16 passed**. PyInstaller `BrolisGameTranslate.spec` temiz derlemesi başarılı; yerel çıktı `E:\TRCeviri\dist\BrolisGameTranslate\BrolisGameTranslate.exe` (onedir, `_internal` klasörü gerekir).
- **Önemli kaynak sınırı:** bu makinedeki ortak devir notuna göre tek doğru PC kaynağı `E:\trtv\trceviri`; `E:\TRCeviri` eski/ayrı kopyadır. Claude `trceviri/` ve canlı kurulumun sahibidir. Yukarıdaki Windows EXE yalnızca bu eski kopyadan üretilmiştir; canlı PC uygulamasının yayımlandığı veya güncellendiği anlamına gelmez. Logo kaynakları `brand/`'a eklendi; Claude'dan bunları gerçek `trceviri/` kaynağına uygulayıp kendi `release.ps1` akışında test etmesi bekleniyor. Eski kopyadaki kodu ana PC kaynağına otomatik kopyalamayın.
- **Doğrulanmayanlar:** TV'de HDMI koruması nedeniyle `screencap` boş döndü; Build 19 Ayarlar ekranı gerçek kumandayla görsel olarak doğrulanmadı (Build 18'de kumanda akışı çalışıyordu). Ayarlar ekranı `exported=false`; ADB ile doğrudan açılamaz. PC'de canlı çeviri başlatılmadı, TV bağlantısı kesilmedi.
- **Protokol:** bu Codex değişiklikleri yeni TCP mesajı eklemedi; var olan `style`, `items`, `visible`, `ping`, `cal`, `set` protokolü değişmedi.
