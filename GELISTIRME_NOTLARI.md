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
| `{"t":"style",…}` | Çizim: `box`, `opacity` (0–255), `text`, `speaker`, `scale`, `mode`, `match`, `bgm` (`black`/`semi`/`none`/`game`). Hizalama: `dx`, `dy`, `sx`, `sy`, `calib`. Ayarlar ekranı için: `tts`, `spkcol`, `cats{dialogue,menu,controls,other,nav}`, `output`. Font: `font` (`default`/`condensed`/`rounded`/`clean`); alan yoksa TV varsayılan yazı tipini kullanır. |
| `{"t":"items","z":<bölge>,"items":[…]}` | Her öğe: `b` [x0,y0,x1,y1] (0–1), `lh`, `s` konuşmacı, `tr` Türkçe, `k` (`subtitle`/`menu`/`controls`/`other`), `n` satır sayısı, `fg`/`bg`/`sc` renkler, `a` hizalama. |
| `{"t":"clear"}` | Ekrandaki tüm çevirileri temizle. |
| `{"t":"visible","v":bool}` | Türkçeyi göster/gizle. |
| `{"t":"ping"}` | TV `pong` ile cevap verir. |

**TV → PC**

| Mesaj | Değerler |
|---|---|
| `{"t":"cal","a":…}` | `CAL_MODE_ON`, `CAL_MODE_OFF`, `CAL_LEFT`, `CAL_RIGHT`, `CAL_UP`, `CAL_DOWN`, `CAL_BIGGER`, `CAL_SMALLER`, `CAL_RESET` |
| `{"t":"set","k":…,"v":…}` | `k`: `profile` (ad), `engine` (`local`/`gemini`/`free`), `font` (`default`/`condensed`/`rounded`/`clean`), `font_scale`, `bg_mode`, `bg_opacity` (0–100), `speaker_colors_on`, `tts_enabled`, `cat_dialogue`, `cat_menu`, `cat_controls`, `cat_other`, `cat_nav`, `replay`. Bilinmeyen anahtar yok sayılır. |
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

### Claude — 2026-11-22 (geliştirmede, 2.3.3 için hazır)
- **Yazı tipi desteği (görev 7'nin PC tarafı) hazır:** `trceviri/trceviri/fonts.py`. `brand/fonts/{condensed,rounded,clean}.ttf` bulunursa yüklenir; yoksa sadece "Varsayılan" görünür (test var, 10 test).
  - Görünüm → Ayrıntılar → **Yazı tipi**.
  - `release.ps1`, `brand/fonts/*`'u pakete (`assets/fonts`) kopyalıyor.
- **Protokol (yeni alanlar, yeni mesaj yok):**
  - `style` içine `font` (`default`/`condensed`/`rounded`/`clean`), `fonts` (kullanılabilir anahtarlar), `pcver` (PC sürümü), `refine` (Gemini durumu ya da null).
  - TV→PC `set` anahtarı `font`.
- **Küçük düzeltmeler:**
  - Konuşmacı renkleri tablosunda renk düğmesinin yazısı kırpılıyordu.
  - Gemini'nin "düşünme ayarı yok" bilgisi model başına hatırlanıyor.
- **Yayın:** 2.3.3, fontlar gelince yayınlanacak (canlıyı gereksiz yere yeniden başlatmamak için).
- Codex'e `trceviri/CODEX_GOREV_8.md` verildi: TV ilk kurulum rehberi, Tanılama'ya PC bilgisi, `contrib/gta6_extra.json` paket önerileri.

### Codex — Görev 7 — 2026-11-22
- **Yazı tipleri:** `brand/fonts/` içine Barlow Semi Condensed SemiBold (dar/oyun stili), Nunito değişken fontu (700 ağırlıkta yuvarlak) ve Inter değişken fontu (18 optik boyut, 600 ağırlıkta sade) eklendi. Kaynak Google Fonts deposu `06bfe0d62a98375cb09c942fa18e68bd32cff057` anlık görüntüsüdür; üçü de SIL Open Font License 1.1 ile lisanslı. Resmî lisans metinleri ayrı dosyalarda; kaynak, ağırlık ve lisans ayrıntıları `brand/fonts/README.md` içinde.
- **TV:** Üç font Android uygulama varlıklarına eklendi. Overlay `style.font` alanına göre fontu seçip değişince metin düzeni önbelleklerini temizler. Alan yoksa varsayılan sans-serif-medium kullanılır. Ayarlar'a dört seçenekli “Yazı tipi” satırı ve seçilen fontla örnek altyazı önizlemesi eklendi; değişiklikler mevcut `set` mesajının `font` anahtarıyla gönderilir.
- **Protokol:** Yeni mesaj türü yok. PC→TV `style.font`: `default`/`condensed`/`rounded`/`clean`; TV→PC `{"t":"set","k":"font","v":"condensed"}` (değer seçenek anahtarlarından biri).
- **Değişen dosyalar:** `app/src/main/java/com/trtv/OverlayService.kt`, `OverlayView.kt`, `SettingsActivity.kt`; `app/src/main/assets/fonts/{condensed,rounded,clean}.ttf`; `brand/fonts/{condensed,rounded,clean}.ttf`, `OFL-Barlow-SemiCondensed.txt`, `OFL-Nunito.txt`, `OFL-Inter.txt`, `README.md`; `GELISTIRME_NOTLARI.md`.
- **Claude eşgüdümü:** Claude, PC tarafı font seçimini ve `style.font`/`set font` desteğini geliştirme sürümünde tamamladı (2.3.3 hazırlığı, yukarıdaki Claude kaydı). Font varlıkları artık `main` dalında; PC paketleme adımına dahil edilebilir ve yayın süreci sürdürülebilir. PC test run 4 başarılı.
- **Build:** Build 38 (`c3ffe79`, run `44965709140`) başarılı; JVM birim testleri, APK derlemesi ve release adımları geçti. PC testleri run 4 (`44965486572`), Claude'un PC font desteği commit'inde başarılı oldu.
- **TV doğrulaması:** Build 38 (`versionCode=38`) Beko TV'ye kuruldu. Ayarlar ekranında “Yazı tipi — Varsayılan” satırı ile “Polisler sahil yolunu kapatmış.” örnek önizlemesi UI ağacında görüldü. Bilgisayar bağlı aktif oturumun font tercihini etkilememek için diğer fontlar seçilmedi.

### Codex — Görev 8A — TV ilk kurulum rehberi — 2026-11-22
- İlk açılışta 4 adımlı kumanda rehberi gösterilir; ekran üstü iznini denetler, bilgisayar bağlantısını ve TV IP'sini canlı gösterir, tamamlanınca `onboarding_done` kaydeder. Ana ekrana rehberi tekrar açma düğmesi eklendi.
- **Dosyalar:** `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{MainActivity,OnboardingActivity}.kt`, bu günlük.
- **Build:** Build 41 (`3371882`, run `44967888388`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Görev 8B — Tanılama bilgileri — 2026-11-22
- TV style bilgisinden PC sürümü, Gemini durumu, motor ve oyun profili thread-safe ayar anlık görüntüsünde saklanır ve Tanılama'da gösterilir. Eski istemcide eksik alanlar `—`, açıkça null gelen Gemini durumu `Kapalı` görünür.
- **Dosyalar:** `app/src/main/java/com/trtv/{OverlayService,DiagnosticsActivity}.kt`, bu günlük. Protokole yeni mesaj eklenmedi.
- **Build:** Build 42 (`3e18ff5`, run `44967923945`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Görev 8C — GTA 6 paket önerileri — 2026-11-22
- `contrib/gta6_extra.json` içinde 298 kısa arayüz/kontrol/hedef/durum/telefon/mağaza/araç/silah önerisi var. JSON çözümlenerek doğrulandı; mevcut `gta6.json` ile büyük-küçük harf duyarsız anahtar çakışması yok. Uzun diyalog eklenmedi.
- **Dosyalar:** `contrib/gta6_extra.json`, `contrib/README.md`, bu günlük. `trceviri/` içindeki asıl pakete dokunulmadı.
- **Claude isteği:** Öneri paketini gözden geçirip uygun çevirileri kendi ana GTA 6 paketine aktar.
- **Build:** Build 43 (`d7d04a4`, run `44967969079`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Toplu görev 9/10A — PC durum satırı — 2026-11-22
- Ayarlar'ın altında PC/TV/Gemini durum satırı eklendi. `pcver` yoksa veya 2.3.0'dan eskiyse güncelleme uyarısı sarı; durum metninde kota/geçersiz varsa satır da sarı görünür.
- **Dosyalar:** `app/src/main/java/com/trtv/SettingsActivity.kt`, bu günlük.
- **Build:** Build 44 (`b12dc33`, run `44968061582`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Toplu görev 9/10B — Kumanda tuşları — 2026-11-22
- Ayarlar'a Kumanda tuşları sayfası eklendi; TV gezinme/ayar/hizalama girdileri ve PC F6/F8/F9/F10/F11 kısayolları listeleniyor. Hizalama ilk açılışında 5 saniyelik ipucu bir defa gösterilip SharedPreferences'a kaydediliyor.
- **Dosyalar:** `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{SettingsActivity,CalibrateActivity,RemoteKeysActivity}.kt`, bu günlük.
- **Build:** Build 45 (`2c34d9e`, run `44968139289`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Toplu görev 9/10C — Güncelleme sonrası servis — 2026-11-22
- BootReceiver'a `MY_PACKAGE_REPLACED` eylemi eklendi; TV ana ekranındaki bağlantı yokken mesajında bekleme durumu, TV IP'si ve 47800 portu birlikte gösteriliyor. OverlayService zaten `START_STICKY` döndürüyordu; kaynakta doğrulandı.
- **Dosyalar:** `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/MainActivity.kt`, `OverlayService.kt` (servis davranışı kontrol edildi), bu günlük.
- **Build:** Build 46 (`c1a048c`, run `44968271735`) başarılı; JVM testleri, APK derlemesi ve release adımları geçti.

### Codex — Toplu görev 9/10D — PC test CI — 2026-11-22
- PC test workflow'u Windows-latest/Python 3.11, `pytest PySide6 numpy` kurulumuyla ve `pytest trceviri/tests -q` komutuyla güncellendi. Push/PR otomatik tetikleyicisi yalnızca `trceviri/**` dosyalarını izler; workflow_dispatch korunmuştur.
- **Dosyalar:** `.github/workflows/pc-tests.yml`, bu günlük.
- **Test sonucu:** Yeni Python 3.11 PC run 6 (`44968623196`) paket kurulumunu geçti ancak `pytest` toplama aşamasında `cv2` modülü bulunmadığı için başarısız oldu (`ModuleNotFoundError: No module named 'cv2'`). Gereken dağıtım paketi `opencv-python` (CI için `opencv-python-headless` uygundur). **Claude isteği:** Bu bağımlılığı `trceviri/requirements.txt` ve ilgili test ortamına ekleyip `trceviri/` tarafında düzeltin; Codex PC kaynaklarına dokunmadı. Eski Python 3.12 yapılandırmasıyla PC run 5 (`44966364847`) başarılıydı.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10E — GTA 6 öneri paketi — 2026-11-22
- Görev 8C'de eklenen `contrib/gta6_extra.json` bu isteği de karşılıyor: 298 yeni, kısa oyun arayüzü/kontrol/görev/telefon/durum/mağaza/araç/silah metni içeriyor. Büyük harfli kaynak satırlar büyük harf olarak çevrildi; ana paketle çakışma ve tekrar denetimleri temizdi. Asıl `trceviri/` paketine dokunulmadı.
- **Dosyalar:** `contrib/gta6_extra.json`, `contrib/README.md` (görev 8C'de eklendi), bu günlük.
- **Test sonucu:** JSON parse, yinelenen anahtar ve mevcut `gta6.json` anahtar çakışması kontrolleri geçti.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10F — README ilk 5 dakika — 2026-11-22
- README'nin üstüne beş dakikalık kurulum adımları ve F6 dahil kısayollar eklendi. İstenen beş sorun için çözüm tablosu ve iki mağaza görseli eklendi.
- **Dosyalar:** `README.md`, bu günlük.
- **Test sonucu:** Markdown ve görsel yolları gözle kontrol edildi; `brand/store/` görselleri G bölümünde eklendi. README commit'inin Build 50 release adımı, aynı `latest` etiketi için paralel build yayınları çakıştığından başarısız oldu; son ağaçtaki Build 51 başarılı APK/release üretimini tamamladı.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10G — Mağaza görselleri — 2026-11-22
- Telifsiz, soyut oyun sahnesi tarzında 1280×720 iki vektör tanıtım görseli hazırlandı: önce/sonra altyazısı ve PC→TV akış şeması. README görselleri gösteriyor.
- **Dosyalar:** `brand/store/once-sonra.svg`, `brand/store/pc-tv-akis.svg`, `README.md` (görsel bağlantıları), bu günlük.
- **Test sonucu:** İki SVG XML olarak doğrulandı; ikisi de 1280×720 viewBox kullanıyor. Build 51 (`dad3a34`, run `44968666818`) JVM testleri, APK derlemesi ve release adımlarıyla başarılı.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.


### Claude — 2.3.3 canlıda (2026-11-22)
- PC 2.3.3 yayınlandı (`pc-latest`) ve canlıda çalışıyor. Codex'in `brand/fonts` fontları pakete dahil (`assets/fonts`), PC overlay'i de seçilen fontla çiziyor.
- Değişken fontlar (Nunito, Inter) ince çiziliyordu: `fonts.apply_weight()` ile `wght` ekseni ayarlanıyor (rounded 700, diğerleri 600).
- `style` yeni alanlar: `pcver` (PC sürümü), `refine` (null ya da Türkçe Gemini durum metni).
- TV build 1.38 (Codex font build) TV'ye kuruldu ve doğrulandı.
- Codex'e Görev 9 verildi: `trceviri/CODEX_GOREV_9.md`.

### Claude — 2.3.5 canlıda: tam ekran düzeni (2026-11-22)
- Sorun: 1920x1080 ekran %125 ölçekte uygulamaya sadece 1536x792 mantıksal alan kalıyordu. Ana sayfanın en küçük yüksekliği 924, Bölgeler sayfasınınki 1130 idi. Taşan alan sıkışınca Sistem durumu satırları üst üste biniyor, çıkış seçimi düğmeleri kesiliyordu.
- Çözüm:
  - Tüm sayfalar kaydırma alanında; sığmazsa kaydırma çubuğu çıkıyor, öğeler üst üste binmiyor.
  - Çıkış seçimi (PC/TV/İkisi) başlık satırına taşındı.
  - Ölçüm kartları sıkılaştırıldı, önizleme ve bölge tuvalinin en küçük boyutları küçültüldü.
  - Segmented düğmeler, seçiliyken kalın yazıya göre en az genişlik alıyor.
  - StatusRow mesajları satır kaydırıyor ve ipucu olarak da gösteriliyor.
  - Sihirbaz başlığı iki satır.
- Test:
  - Ekran görüntüsü testleri 1536x792, 1280x680 ve 1920x1000 boyutlarında yapıldı.
  - Canlı exe büyütülmüş pencerede yakalandı: temiz.
  - pytest: 10 test geçti.
- TV: 03:40 sonrası TV ping'e de yanıt vermiyor (kapalı/uyku). APK 1.38 kurulu. Güncelleme sonrası otomatik başlatma Codex görev C'de.
- Codex'e toplu görev verildi: `trceviri/CODEX_GOREV_10_HEPSI.md` (görev 9 dahil, A–G).

### Claude — 2.3.6: GTA 6 paketi büyüdü, CI düzeltildi (2026-11-22)
- Codex'in A–G görevleri incelendi: tamam (TV durum satırı, kumanda yardımı, güncelleme sonrası servis, CI, contrib, README, mağaza görselleri).
- `contrib/gta6_extra.json` içindeki 298 satır `profiles/packs/gta6.json` paketine eklendi (mevcutla çakışanlar korundu). Paket 163 satırdan 461 satıra çıktı.
- `pc-tests.yml` `cv2` eksikliğinden kırılıyordu. Artık `pip install -r trceviri/requirements.txt` kullanıyor (Codex'in dosyası, tek satır).
- PC 2.3.6 canlıda ve `pc-latest` sürümünde. TV kapalı olduğu için yeni TV build'i kurulmadı; TV açılınca uygulama içi güncelleme önerecek.

### Codex — Görev 11 / Adım 0 — MediaProjection fizibilite aracı (2026-11-22)
- Tanılama'ya tek karelik ekran yakalama testi eklendi. İzin isteği, Android foreground service türü `mediaProjection`, PNG kare önizlemesi ve yaklaşık siyah-kare uyarısı var. Yardım'a DRM sınırı ve YouTube otomatik çeviri bilgisi eklendi. DRM atlatma yok.
- **Fizibilite tablosu:** ADB'de TV/Android cihazı bağlı olmadığı için kaynak testleri henüz çalıştırılamadı; aşağıdaki sonuçlar açıkça beklemede.

| Uygulama/kaynak | Kare geldi mi | Siyah mı |
|---|---|---|
| YouTube | Cihaz testi bekliyor | Cihaz testi bekliyor |
| Netflix (TV'de varsa) | Cihaz testi bekliyor | Cihaz testi bekliyor |
| Plex/Kodi/VLC (TV'de varsa) | Cihaz testi bekliyor | Cihaz testi bekliyor |
| TV HDMI girişi (PS5) | Cihaz testi bekliyor | Cihaz testi bekliyor |

- **Dosyalar:** `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{DiagnosticsActivity,ProjectionProbeActivity,ProjectionProbeService,HelpActivity}.kt`, bu günlük.
- **Test:** Yerel Gradle çalıştırıcısı/gradlew mevcut değil. İlk CI build 56, DiagnosticsActivity'deki eksik `Intent` import'u yüzünden başarısız oldu; build 57 (`8df4766`, run `45019100191`) düzeltme sonrasında başarılı. Fiziksel test için TV ADB'ye bağlanınca yukarıdaki tablo ölçülmeli.
- **Durum:** Adım 0 cihaz ölçümü tamamlanana kadar beklemede; DRM içeriği siyah çıkarsa uygulama kullanıcıya sınırlamayı bildirecek.

### Claude — PC 2.4.0: her oyun + film/dizi, 60 FPS, anlık mod, TV çevirisi, .srt (2026-11-22)
- **Her oyun:** Profil listesi en üstte `Genel oyun (her oyun)` (yeni kurulumların varsayılanı) ve `Film / dizi`. Yeni oyun profilleri: TLOU2, GoW Ragnarök, Ghost of Tsushima, Ghost of Yōtei, Horizon FW, RE4, Hogwarts Legacy, EA FC, Call of Duty, FF7 Rebirth, Death Stranding 2, Stellar Blade, Black Myth Wukong, Uncharted. Toplam 23 profil.
- **Profil alanları:** `kind` (`game` | `film`) ve `window_hint` (profil seçilince okunacak pencere).
- **Film modu (PC):**
  - Sadece ekranın alt %45'i okunur ve oradaki her şey altyazı sayılır.
  - `♪` satırları atlanır; `<i>` etiketleri temizlenir; baştaki `-` korunur.
  - Çeviri istemi film/dizi altyazısına göre.
  - Pencere listesinden VLC/tarayıcı seçilebilir; seçilen pencere çalışırken anında geçerli olur.
- **FPS:** 10–60 arası seçilebilir; yeni varsayılan 30. Gelişmiş'te gerçekte ulaşılan FPS ve OCR süresi görünür.
- **Anlık mod (1:1):** varsayılan açık. Yazı ilk karede (okuma güveni ≥ 0.6) gösterilir.
- **Protokol:**
  - `style` içine `fps` ve `instant` eklendi.
  - TV→PC `set` anahtarlarına `fps`, `instant`, `output` eklendi.
  - Yeni TV→PC `ocr` (`id`, `src`, `lines[{en, b, lh}]`), PC→TV `tr` (`id`, `tr[]`). PC hazır olanları hemen, kalanları çevrildikçe aynı id ile tekrar gönderir. Yakalama kapalıyken de çalışır (`Pipeline.ensure_manager`).
  - Gerçek yerel modelle uçtan uca test edildi.
- **.srt çevirici:** Çeviri sayfası → "Film / dizi altyazı dosyası çevir". `.srt` ve `.vtt` okunur, aynı klasöre `film.tr.srt` yazılır, zamanlamalar korunur. Gemini anahtarı varsa onunla, yoksa yerel modelle çevrilir (`trceviri/srt.py`).
- **Test:** pytest 16 test geçti (`tests/test_film.py` yeni). Ekran görüntüsü kontrolü 1536x792'de yapıldı.
- **Codex:** Görev 11 = TV bağımsız mod (MediaProjection + ML Kit + `ocr`/`tr`) ve TV görünümünün baştan tasarımı.

### Codex — Görev 11 / Adımlar 1–3 — TV OCR ve film çevirisi (2026-11-22)
- TV'de 5 FPS MediaProjection yakalama servisi eklendi; altyazı bandı varsayılan alt %35, ayarlanabilir %35–100. Kısa gri-ton özeti aynı kareyi yeniden OCR'a göndermiyor; Latin ML Kit OCR satırları iki ardışık örnekte kararlı olunca yayınlanıyor. Çeviri katmanı okunmasın diye örnek kare öncesi kısa süre gizleniyor.
- Bağlı PC'ye `ocr` (`id`, `src=film`, `lines` içindeki `en`, oranlı `b=[x,y,w,h]`, `lh`) gönderilir. 600 ms yanıt gelmezse cihazdaki ML Kit EN→TR kullanılır; model Wi‑Fi üzerinden indirilir, metin LRU önbelleği 2000 öğe tutar. `tr` aynı kimliği güncelleyebilir; PC cevabı geç gelse de cihaz yanıtını ezer.
- Film çizimi siyah zemin kullanır. `♪` satırları atlanır, tireli diyalog başı korunur, `[...]/(...)` efektleri köşeli parantezli gösterilir; altyazı kaybolunca 300 ms içinde film bölgesi temizlenir. PC bağlantı kopması/`clear` film katmanını silmez.
- **Dosyalar:** `app/build.gradle.kts`, `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/trtv/{IndependentModeService,FilmPipeline,LocalFilmTranslator,SettingsActivity,OverlayService,OverlayView}.kt`, bu günlük. TV→PC `ocr`, PC→TV `tr` mesajları kullanılıyor; Claude 2.4.0 uyumluluğunu günlüğe yazdı.
- **Test:** Yerel Gradle çalıştırıcısı/gradlew mevcut değil; CI build doğrulaması bekleniyor. MediaProjection fizibilite tablosu ADB/TV bağlantısı gelene kadar bekliyor.

### Codex — Görev 11 / Kod ve TV arayüzü (2026-11-22)
- Ayarlar'a TV'nin bağımsız film/dizi modu, %35–100 altyazı bandı, PC OCR hızı, anlık mod ve çıktı yönü eklendi. TV kumandasında Altyazı/Captions tuşu varsa film çevirisini gösterip gizler.
- Ana ekran yenilendi: marka simgesi, koyu kart görünümü, kumanda odağında yeşil çerçeve/büyüme, PC bağlantı/IP durumu, bağımsız mod OCR/çeviri durumu ve son üç çeviri görünür.
- Ayarlar satırları 20sp üzeri ve uzaktan okunabilir boyuta yükseltildi. Film modu ve DRM sınırı Yardım'da açıklanıyor.
- JVM testleri kararlı OCR, satır temizleme/tire/efekt ve aynı OCR kimliğinin sonraki çeviri düzeltmesini kapsıyor. GitHub build run 65 (Build 65) başarılı; JVM testleri ve APK derlemesi tamamlandı.
- **Protokol:** TV→PC `ocr` (`src=film`), PC→TV `tr` (`id`, `tr[]`); ek mesaj türü yok. Mevcut `set` anahtarları kullanılıyor.
- **Dosyalar:** `app/src/main/java/com/trtv/{FilmPipeline,IndependentModeService,LocalFilmTranslator,MainActivity,OverlayService,ProjectionProbeActivity,SettingsActivity,HelpActivity}.kt`, `app/src/test/java/com/trtv/ProtocolTest.kt`, `app/build.gradle.kts`, `app/src/main/AndroidManifest.xml`, bu günlük.
- **Cihaz doğrulaması bekliyor:** ADB listesinde TV yok. YouTube/Netflix/Plex-Kodi-VLC/HDMI fizibilite ölçümü ve istenen gerçek `screencap` önce/sonra görselleri alınmadı; yukarıdaki tabloda beklemede kalmalı. Kod/arayüz değişikliklerinden sonra Build 66 CI sonucu ayrıca doğrulanacak.

### Claude → Codex: SIRADAKİ GÖREV (2026-11-22)
- **Codex:** Görev 11 bitince ara vermeden `trceviri/CODEX_GOREV_12.md` dosyasına geç (ortak UI paketi, oyun paketleri, tanıtım sitesi, TV çizim performansı). Kullanıcı 8–10 saat yok; soru sorma, kararlarını notlara yaz.
- **Claude bu sürede:**
  - ortak paketi (tüm profillerin yedeği) yapıyor
  - oyunu otomatik tanıyıp profil öneriyor
  - sentetik karelerle gecikme/doğruluk ölçüm aracı kuruyor
  - OCR/gecikme iyileştirmeleri yapıyor
  - çökme koruması ekliyor

### Claude — PC 2.5.0 → 2.5.2: "en iyi oyun çeviri" turu (2026-11-22)
- **Ortak arayüz paketi** `profiles/packs/ortak.json`: 447 satır (menü, ayar, kayıt, kontrol, durum).
  - Bütün oyun profillerinde yedek pakettir; oyunun kendi paketi önce gelir, film profilinde kullanılmaz.
  - Codex'in `contrib/ortak_ui.json` (Görev 12A) çıktısı geldiğinde birleştirilecek.
- **Büyük harf / nokta uyumu:**
  - İngilizce TAMAMI BÜYÜK ise paket/önbellek sonucu da büyük harfle gelir (Türkçe İ/I doğru).
  - Sondaki nokta İngilizceye uyar.
- **Oyun tanıma** (`gamedetect.py`): profillerdeki çevrilmez özel isimlerden (yalnızca tek oyuna özgü olanlar) son 4 dakikada en az 3 farklısı görülürse üstte "X profiline geç" önerisi çıkar. Onaysız profil değişmez; "Hayır" o oturumda tekrar sormaz.
- **Çeviri düzeltme:** Ana sayfa → Son çeviriler → satıra çift tık. Düzeltme `profiles/packs/duzeltmeler_<profil>.json` dosyasına yazılır, her şeyden önce gelir ve ekrandaki çeviri hemen güncellenir.
- **Kontrol ipuçları** (`controls.py`): "Press/Hold/Tap <tuş> to <eylem>" kalıbı.
  - Tuş adı ve Türkçe eki kuralla kurulur (X'e, Kare'ye, Üçgen'i, R2'yi, L3'ü, dokunmatik yüzeye, sol çubuğa).
  - Eylem ~90 terimlik sözlükten, yoksa modelden ("In order to V." → "V-mek için") gelir.
  - 16 örneğin 16'sı doğru. Örnek: önce "L2'yi nişan al", şimdi "Nişan almak için L2'yi basılı tutun".
- **Film diyaloğu:** yerel motor baştaki "- " tiresini siliyordu; artık korunuyor.
- **OCR** (ölçüm aracı `tools/bench.py`; sentetik oyun kareleri, 8 font, 4 zemin tipi):
  - Doğruluk: CER %0,09, tür doğruluğu %100.
  - Sabit kare (duraklatma, menü): OCR çalışmıyor, 70 ms → 1,7 ms.
  - HATA DÜZELTİLDİ: satır hafızası (48x12 imza), aynı yerde çıkan benzer uzunlukta yeni altyazıya eski metni döndürüyordu. Yeni imza 192x20 + boyut + p98 farkı; altyazı değişimi 8/8, hareketli zemin 24/24.
  - Toplu tanıma ölçüldü, CPU'da daha yavaş çıktı (172 → 194–244 ms); kapalı (`TRC_OCR_BATCH`).
  - Tarama genişliği 960 en iyi denge: 640 yazı kaçırıyor, 1280 yavaş.
- **Dayanıklılık:** yakalama döngüsü çökerse kaydedip yeniden başlıyor (5 ardışık hatada durup kullanıcıya söylüyor). Arka plan iş parçacığı hataları da günlüğe yazılıyor.
- **Sihirbaz:** 3. adımda "Hangi oyunu oynuyorsunuz?" seçimi var. `NASIL KULLANILIR.txt` 2.5 özellikleriyle güncellendi.
- **TV yerel ayarları:** `film_band` ve `mode` PC'de sessizce yok sayılıyor.
- **Test:** pytest 22/22.
- **Codex için:** Görev 12 hâlâ beklemede. Kullanıcı yapıştırmadı; Codex 11'i bitirip durdu.
- **TV:** kapalı. Fizibilite tablosu ve ekran görüntüleri TV açılınca yapılacak.


### Codex — Görev 12A — Ortak oyun arayüzü paketi — 2026-11-22
- Tüm oyunlarda kullanılabilecek menü/ayar, erişilebilirlik, kayıt, görev/harita, envanter, kontrol ve kısa durum mesajları için **4.165** benzersiz JSON anahtarı eklendi. Tamamı büyük harf kaynak durumlarında hedef metin de büyük harf biçiminde tutuldu; uzun diyalog/emoji yok.
- **Dosyalar:** `contrib/ortak_ui.json`, `contrib/README.md`, bu günlük.
- **Doğrulama:** UTF-8 JSON parse edildi, tam anahtar yinelenmesi yok. Build 71 (`f9c5ac3`, run 71) başarılı; APK derlemesi ve release tamamlandı.
- **Yarım kalan:** Claude'un `trceviri/profiles/packs/ortak.json` ile gözden geçirip birleştirmesi bekleniyor.


### Codex — Görev 12B — Popüler oyun paketleri — 2026-11-22
- 10 oyun profili için ayrı öneri JSON'ları hazırlandı; her biri 170–171 benzersiz kısa arayüz, terim, hedef ve kontrol kaydı içeriyor. Mevcut profil sözlükleri ve oyun terimleri okundu; karakter adları çevrilmedi.
- **Dosyalar:** `contrib/packs/{gow_ragnarok,tlou2,ghost_tsushima,horizon_fw,re4,hogwarts,ea_fc,cod,ff7_rebirth,uncharted}.json`, `contrib/README.md`, bu günlük.
- **Doğrulama:** JSON parse ve anahtar tekilliği kontrolü; her paket 150+ satır. Build 72 (`838cb3b`, run 72) başarılı; APK derlemesi ve release tamamlandı.
- **Yarım kalan:** Oyun içi satır doğrulaması ve ana paketlere birleştirme Claude tarafından yapılmalı.


### Codex — Görev 12C — Tanıtım ve indirme sitesi — 2026-11-22
- Türkçe, mobil uyumlu statik tanıtım sitesi hazırlandı: indirme düğmeleri, kurulum akışı, marka görselleri, 23 profil (Genel + Film/dizi + 21 oyun), film/.srt modu, sorun giderme ve gizlilik metni. `actions/deploy-pages` ile Pages workflow eklendi. README'ye site bağlantısı ve film modu açıklaması eklendi.
- **Dosyalar:** `site/index.html`, `site/style.css`, `site/assets/{logo.svg,once-sonra.svg,pc-tv-akis.svg}`, `.github/workflows/pages.yml`, `README.md`, bu günlük.
- **Doğrulama:** Yerel statik dosya/link kontrolü yapılacak; Android Build 73 (`ff92b70`, run 73) başarılı. Pages run 1, `Pages'i yapılandır` adımında depo Pages kaynağı etkin olmadığı için başarısız oldu.
- **Ayar notu:** Repo Pages kaynağı açılmamışsa Settings → Pages → Source → GitHub Actions seçilmeli.
- **Yarım kalan:** GitHub depo ayarından Settings → Pages → Source → GitHub Actions seçilmesi gerekiyor; bu hesapta depo ayarlarını değiştiren yetkili bağlantı bulunmadığından deploy ve canlı URL doğrulaması bekliyor.


### Codex — Görev 12D — TV çizim performansı — 2026-11-22
- Overlay kutuları kimliğe göre güncelleniyor; değişmeyen öğelerin metin düzeni önbellekten kullanılıyor. Güncellemede yalnızca eski/yeni kutu alanı kirli dikdörtgen olarak invalidate ediliyor; diğer kutular clip dışındaysa çizilmiyor. Metin ölçümü/satır kırılımı için Android `StaticLayout` nesnesi düzen önbelleğinde tutuluyor. İçerik kaldırma ve temizleme animasyonsuz, anında; yeni/yenilenen çeviri 80 ms alfa ile beliriyor. Tanılama'da yalnızca debug derlemesinde son kare çizim süresi gösteriliyor.
- **Dosyalar:** `app/src/main/java/com/trtv/OverlayView.kt`, `app/src/main/java/com/trtv/OverlayService.kt`, `app/src/main/java/com/trtv/DiagnosticsActivity.kt`, bu günlük.
- **Doğrulama:** Build 74 (`6d9fe20`) JVM derlemesinde `BuildConfig` referansı bulunamadığı için başarısız oldu; debug tespiti Android `ApplicationInfo.FLAG_DEBUGGABLE` ile düzeltildi. Build 75 (`6296ab1`, run 75) önceki sürümde başarılı; kısmi dirty-region değişikliği Build 76’da `AnimatedItem`/`OverlayItem` tipi uyuşmazlığıyla başarısız oldu; kaldırma listesi `.item` üzerinden düzeltilip gereksiz önbellek temizliği de engellendi. Build 77 (`f620dc5`, run 77) JVM testleri, APK derlemesi ve release ile başarılı. 1080p'de ≤8 ms hedefi fiziksel TV'de ölçülmedi; debug Tanılama ekranında ölçüm görünür olacak.
- **Yarım kalan:** Gerçek cihazdaki kare süresi/8 ms hedefi, TV yeniden bağlandığında ölçülmeli.


### Codex — Görev 12 kapanış — 2026-11-22
- **A tamamlandı:** 4.165 anahtarlı ortak oyun UI önerisi. **B tamamlandı:** 10 oyun paketi, her biri 170–171 satır. **C kodu tamamlandı:** statik Türkçe tanıtım sitesi, README bağlantısı ve GitHub Pages workflow'u. **D kodu tamamlandı:** önbellekli StaticLayout, yalnızca değişen kutuların dirty-region çizimi, anında silme, 80 ms belirme ve debug çizim süresi.
- **CI/build:** A Build 71 başarılı; B Build 72 başarılı; C APK Build 73 başarılı; D ilk deneme Build 74 `BuildConfig` hatasıyla başarısız, düzeltme Build 75 başarılı. Build 75 JVM testleri, APK ve release adımları geçti; nihai dirty-region kodu Build 77 ile de doğrulandı. PC test workflow'u bu değişikliklerde tetiklenmedi (`trceviri/` değişmedi); son görülen önceki PC test run 17 başarılıydı.
- **Yarım kalan dış koşullar:** GitHub Pages run 1, depo Pages etkin olmadığı için `configure-pages` adımında durdu. Depo sahibi Settings → Pages → Source → GitHub Actions seçince workflow yeniden çalıştırılmalı; yayındaki site doğrulaması bekliyor. 1080p/8 ms çizim hedefi ve görsel kalite gerçek Android TV'de ölçülmedi; ADB cihazı bağlı değil.
- **Değiştirilen ana alanlar:** `contrib/`, `site/`, `README.md`, `.github/workflows/pages.yml`, `app/src/main/java/com/trtv/{OverlayView,OverlayService,DiagnosticsActivity}.kt`. `trceviri/` değiştirilmedi. Protokole mesaj eklenmedi.

- **Son TV build:** Build 77 (`f620dc5`) başarılı ve `latest/a.apk` olarak yayımlandı. Bu build Görev 12 uygulama kodunu içerir; site görsellerinin Pages artifact içine eklenmesiyle oluşan Build 78 CI doğrulaması sırada.
