# TRÇeviri / Brolis Game Translate — ortak geliştirme notları

Bu dosya **Claude** ile **Codex (ChatGPT)** arasındaki devir notudur. İkimiz de işe başlamadan önce bu dosyayı okuyup `git pull` yaparız. İş bitince **en alttaki günlüğe** ne yaptığımızı yazarız. Böylece birbirimizin yaptığından haberimiz olur ve aynı dosyada çakışmayız.

## Ürün
PS5 oyunlarındaki İngilizce yazıları (konuşma, menü, kontrol) anında Türkçeye çevirir. Türkçeyi İngilizcenin **tam üstüne, aynı boyutta** yazar.

| Parça | Ne yapar | Kod | Dil |
|---|---|---|---|
| Bilgisayar uygulaması | PS Remote Play penceresini okur → OCR (RapidOCR, tespit DirectML) → çeviri (yerel CTranslate2 opus-mt + isteğe bağlı Gemini iyileştirme) → PC'de katman ve TV'ye gönderim | `trceviri/` | Python 3.12 + PySide6 |
| TV uygulaması **TRÇeviri TV** | Android TV / Google TV. TCP 47800'ü dinler, çevirileri PS5'in HDMI görüntüsünün üstüne çizer | `app/` | Kotlin, paket `com.trtv` |

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

### Codex
- (Codex: yaptıklarını buraya yaz — dosyalar, build numarası, protokole eklediğin mesajlar.)
