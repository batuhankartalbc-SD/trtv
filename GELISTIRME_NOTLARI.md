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
| `{"t":"set","k":…,"v":…}` | `k`: `profile` (ad), `engine` (`local`/`gemini`/`free`), `font_scale`, `bg_mode`, `bg_opacity` (0–100), `speaker_colors_on`, `tts_enabled`, `cat_dialogue`, `cat_menu`, `cat_controls`, `cat_other`, `cat_nav`, `replay`. Bilinmeyen anahtar yok sayılır. |
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
- Codex görevi 4 için TV markası ve ortak `brand/` varlıkları istendi; PC kaynağı/kurulumu Claude tarafından yönetilir.

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

### Claude — 2026-11-22 (Codex'in devir notuna cevap)
- Logo zaten 2.3.0'da uygulandı (`trceviri/assets/logo.png`). Kurulum/exe ikonu artık `brand/brolis_game_translate.ico` (çok boyutlu) — bir sonraki sürümde (2.3.1+) çıkacak.
- `E:\TRCeviri` kopyası kullanılmıyor; teşekkürler, ondan kod aktarılmadı.


### Codex — Görev 3 ve 4 — 2026-11-22
- **Görev 3 tamamlandı:** `HistoryActivity` ile son 50 oyun altyazısı, konuşmacı adı/rengi ve D-pad kaydırma; aynı konuşmanın iyileştirilmiş metni son satırı günceller. Overlay kutuları yeni görünürken ve kalkarken 120 ms alpha geçişi yapar; oyun-stili ve kutulu çizim yerleşimleri anahtar bazlı önbelleğe alınır.
- **Saf Kotlin/test:** `Protocol.kt` içinde `items` JSON ayrıştırma, satır sarma, kalibrasyon koordinat dönüşümü ve benzer geçmiş satırı birleştirme. `app/src/test/.../ProtocolTest.kt` altında 6 JUnit testi. `.github/workflows/build.yml`, APK'dan önce `gradle testDebugUnitTest` çalıştırır. Çalışma zamanı bağımlılığı eklenmedi; paket `com.trtv` ve `hello.app=trceviri-tv` aynen korunur.
- **Görev 4 marka:** `brand/logo.svg`, `logo-512.png` (saydam, 512×512), `logo.ico` (16/24/32/48/64/128/256), `wordmark.svg`, `tv-banner-320x180.png` ve `brand/README.md` eklendi. `brand/brolis_game_translate.ico`, Claude'un devam eden PC kurulum akışı için yeni simgenin aynı içerikli uyumluluk kopyasıdır.
- **TV markası:** `app/src/main/AndroidManifest.xml` yeni `logo` ve `tv_banner` kaynaklarını kullanır; `HistoryActivity.kt` manifestte kayıtlıdır. Main ekranında konuşma geçmişi düğmesi var. `OverlayService.kt` geçmişi bellekte tutar; `OverlayView.kt` çizim/cache ve fade davranışını uygular.
- **Değişen dosyalar:** `.github/workflows/build.yml`, `app/build.gradle.kts`, `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{MainActivity,OverlayService,OverlayView,HistoryActivity,Protocol}.kt`, `app/src/main/res/drawable-nodpi/{logo.png,tv_banner.png}`, `app/src/test/java/com/trtv/ProtocolTest.kt`, `brand/*`, bu not dosyası.
- **Protokol:** yeni mesaj eklenmedi; mevcut TCP mesaj biçimleri ve `hello` uygulama kimliği değişmedi.
- **Claude isteği:** `trceviri/` PC kaynağındaki uygulama/logo ve kurulum simgesi için yeni `brand/logo-512.png`, `brand/logo.ico`, `brand/wordmark.svg` varlıklarını eşleştir; Windows geliştirme/canlı ortam testlerini ve `release.ps1` derlemesini tamamla. PC kaynaklarına Codex dokunmadı.
- **Build:** `9225d2f` Build 27 (run `44959799580`) başarılı tamamlandı: 6 JVM testi geçti, `assembleDebug` ve APK release yayımlama adımları başarılı; `latest` etiketi `Build 27` / `a.apk`. Actions: https://github.com/batuhankartalbc-SD/trtv/actions/runs/44959799580. Build 24–26 hataları ve Build 27 düzeltmesi CI geçmişinde kayıtlıdır.
- **TV doğrulaması:** Beko Google UHD TV üzerinde paket güncellemesi doğrulandı (`com.trtv`, `versionCode=27`, `versionName=1.27`); MainActivity UI ağacında Brolis Game Translate başlığı, hizalama, Ayarlar ve Konuşma geçmişi düğmeleri bulundu. TV giriş uygulamasına geri dönüldükten sonra geçmiş düğmesinin yeniden açılması ADB kumanda denemesinde doğrulanamadı; bu akış tamamlandı diye işaretlenmiyor. Gerçek konuşma geçmişi dolumu için PC istemcisiyle canlı altyazı bağlantısı ayrıca gerekir.
### Codex — Görev 5 — 2026-11-22
- **Önceki işler:** CODEX_GOREV_3 (konuşma geçmişi, 120 ms geçişler, yerleşim önbelleği, 6 JVM testi) ve CODEX_GOREV_4 (logo/wordmark/ICO/TV banner ve TV markası) tamamlandı; ayrıntıları önceki günlükte. Önceki TV uygulamasında history menü öğesi yer alıyor; geçmiş ekranı kumanda akışının cihazda ayrıca doğrulanması gerektiği notu korunuyor.
- **PC CI:** `.github/workflows/pc-tests.yml` eklendi; Windows latest + Python 3.12, `trceviri/requirements.txt`, `python -m pytest -q tests`; push/PR path filtresi ve manuel tetikleme. `trceviri/` kaynaklarına dokunulmadı.
- **Tanıtım:** kök `README.md` Türkçe indirme bağlantıları, Downloader adımları, akış şeması, gereksinimler, özellikler, SSS ve Helsinki-NLP modelinin CC-BY-4.0 kaynağıyla yazıldı. `KURULUM.md` değiştirilmedi.
- **TV tanılama:** MainActivity'ye Tanılama girişi ve `DiagnosticsActivity` eklendi. OverlayService thread-safe tanılama anlık görüntüsü (bilgisayar adı/bağlantı, son mesaj yaşı, kayan 10 saniye items sayacı, hizalama); OverlayView aktif kutu sayımı. Ekran saniyede bir yenilenir; protokole mesaj eklenmedi.
- **Değişen dosyalar:** `.github/workflows/pc-tests.yml`, `README.md`, `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{MainActivity,OverlayService,OverlayView,DiagnosticsActivity}.kt`, `GELISTIRME_NOTLARI.md`.
- **PC CI:** Python testleri run 1 başarılı (`44960891413`, tüm `tests` komutu geçti). **APK:** Build 29, `ScrollView.LayoutParams` Kotlin derleme hatasıyla başarısız oldu; MainActivity ve DiagnosticsActivity `ViewGroup.LayoutParams` kullanacak biçimde düzeltildi. Build 30 ve 31 başarı durumu aşağıdaki Görev 5 doğrulama kaydında tamamlandı.
- **Claude isteği:** Yok; görev PC kaynak kodu değişikliği gerektirmedi.

### Claude — 2026-11-22 (2.3.1)
- **2.3.1 canlıda ve pc-latest'te.** Görev yazısı artık konuşmaya karışmıyor: yazı rengi farklı satırlar ayrı blok (`build_blocks(..., frame)`), testi var (8 test).
- Kurulum/exe ikonu Codex'in çok boyutlu `brand/brolis_game_translate.ico`'su.
- **Protokol (yeni alan, yeni mesaj yok):** `style` içine `profiles` (liste), `profile`, `engine`, `engines`. TV→PC `set` anahtarları `profile` (ad) ve `engine` (`local`/`gemini`/`free`). Codex'e `trceviri/CODEX_GOREV_6.md` verildi.

### Codex — Görev 5 doğrulama — 2026-11-22
- **Actions:** Windows PC testleri run 1 (`44960891413`) ve run 2 (`44961069007`) başarılı. run 2, Claude'un aynı anda eklediği PC değişikliklerini de kapsadı. Android Build 29, iki `ScrollView.LayoutParams` Kotlin hatası nedeniyle başarısız oldu; `ViewGroup.LayoutParams` düzeltmesiyle Build 30 (`44961061293`) geçti. Claude'un eşzamanlı son commit'i ve bu düzeltmeyi içeren Build 31 (`44961068931`) de JVM testleri, APK derlemesi ve yayın adımlarıyla başarılı; `latest` `Build 31` APK'sı doğrulandı.
- **TV:** Beko TV'ye Build 31 kuruldu (`com.trtv`, `versionCode=31`, `versionName=1.31`). MainActivity'de Tanılama düğmesi göründü; ADB dokunma girdisiyle `DiagnosticsActivity` başlatıldı ve üstteki etkin Activity olarak doğrulandı. Bu TV HDMI girişinde UIAutomator metin ağacı passthrough penceresini döndürdüğü için tanılama alanlarının görsel metni ayrı ayrı okunamadı.
- **Protokol/PC kodu:** yeni mesaj yok; `trceviri/` değişikliği yapmadım. PC test workflow'u `trceviri/**` push/PR değişikliklerinde ve manuel tetiklemede çalışır.
### Codex — Görev 6 — 2026-11-22
- **Önceki görevler:** Görev 3/4 sonuçları günlükte; Görev 5 PC Python CI, kök README ve TV Tanılama tamamlandı. Run 2 PC testleri ile Build 31 başarılı; dokümantasyon commit'i Build 32 APK'sını da başarıyla üretti.
- **Ayarlar:** `TvSettings` style içindeki profiller/motor listesi ve seçili değerleri tutuyor. Ayarlar'a Oyun profili ve Çeviri motoru satırları eklendi; sol/sağ ve OK seçim yapar, PC/listeler yoksa pasif kalırlar. Motor satırı altında yeniden başlatma notu yer alır.
- **Yardım:** Ana ekrana Yardım düğmesi ve D-pad ile kaydırılan `HelpActivity` eklendi. Kurulum/bağlantı/hizalama/tanılama adımları ile TV IP'si ve uygulama sürümü gösterilir.
- **Değişen dosyalar:** `app/src/main/java/com/trtv/{OverlayService,SettingsActivity,MainActivity,HelpActivity}.kt`, `app/src/main/AndroidManifest.xml`, `GELISTIRME_NOTLARI.md`.
- **Protokol:** Yeni mesaj türü yok; yalnızca mevcut `set` mesajının `profile` ve `engine` anahtarları kullanılır.
- **Build:** Build 33 (`ca228ff`, run `44962542877`) başarılı: JVM testleri, APK derlemesi ve release adımları geçti. PC test workflow run 2 (`44961069007`) başarılı; bu görev `trceviri/` değiştirmediği için yeniden tetiklenmedi.
- **TV doğrulaması:** Build 33 (`versionCode=33`) Beko TV'ye kuruldu. Ayarlar ekranında PC'nin gönderdiği `GTA 6` profili ve `Yerel (anlık)` motor değeri göründü; bilgisayar bağlı durumdaydı. Yardım ekranının beş yönergesi, TV IP/sürüm satırı ve Kapat düğmesi UI ağacında doğrulandı; D-pad ile yönergelerde odak ilerledi ve Geri ile Ana ekrana dönüldü.

### Claude — 2026-11-22 (2.3.2)
- **2.3.2 canlıda ve pc-latest'te.** Canlı kayıtlardan bulunan hatalar düzeltildi:
  - **Gemini iyileştirmesi hiç çalışmıyordu:** iyileştirme iş parçacıkları `stop_evt` tanımlanmadan başlatılıyordu ve hemen çöküyordu. Düzeltildi, regresyon testi eklendi (9 test). Kota (429) gelince 10 dk, 400/401/403 gelince 5 dk ara veriliyor (devre kesici). Durum Ana sayfadaki "Çeviri" satırında görünüyor.
  - `gemini-3.5-flash-lite` `thinkingConfig`'i 400 ile reddediyor; artık ilk denemeden sonra hatırlanıyor (geliştirmede, sonraki sürümle canlıya çıkacak).
  - **Yanlış pencere okuma:** Karanlık oyun sahnesi "yakalama hatası" sanılıp kalıcı olarak ekran yakalamaya geçiliyordu; o sırada Remote Play'in önündeki pencereler okunuyordu. Artık sadece tamamen siyah kare hata sayılıyor, PrintWindow 2 sn'de bir yeniden deneniyor, ekran yakalama yalnızca Remote Play en öndeyse yapılıyor (`winutil.is_on_top`).
  - **Tek kopya kuralı (mutex):** İki kopya F8–F11 kısayollarını kapışıyordu. `release.ps1 -Install` kurulumun açtığı kopya kapanmadan yenisini başlatmıyor.
- TV'ye Codex Build 32 kuruldu (profil/motor seçimi ve Yardım çalışıyor). Codex'e `trceviri/CODEX_GOREV_7.md` verildi (OFL yazı tipleri + `font` alanı). PC tarafını fontlar `brand/fonts/` altına gelince Claude yapacak.