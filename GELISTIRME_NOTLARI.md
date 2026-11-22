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
- **Test sonucu:** Güncel PC test run 5 (`44966364847`) başarılıdır; bu, Claude'un PC 2.3.3 commit'inde eski Python 3.12 workflow tanımıyla çalıştı. Bu workflow-only değişiklik yeni PC test koşusu tetiklemediğinden Python 3.11 CI sonucu henüz yoktur.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10E — GTA 6 öneri paketi — 2026-11-22
- Görev 8C'de eklenen `contrib/gta6_extra.json` bu isteği de karşılıyor: 298 yeni, kısa oyun arayüzü/kontrol/görev/telefon/durum/mağaza/araç/silah metni içeriyor. Büyük harfli kaynak satırlar büyük harf olarak çevrildi; ana paketle çakışma ve tekrar denetimleri temizdi. Asıl `trceviri/` paketine dokunulmadı.
- **Dosyalar:** `contrib/gta6_extra.json`, `contrib/README.md` (görev 8C'de eklendi), bu günlük.
- **Test sonucu:** JSON parse, yinelenen anahtar ve mevcut `gta6.json` anahtar çakışması kontrolleri geçti.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10F — README ilk 5 dakika — 2026-11-22
- README'nin üstüne beş dakikalık kurulum adımları ve F6 dahil kısayollar eklendi. İstenen beş sorun için çözüm tablosu ve iki mağaza görseli eklendi.
- **Dosyalar:** `README.md`, bu günlük.
- **Test sonucu:** Markdown ve görsel yolları gözle kontrol edildi; görseller G bölümünün ayrı commit'inde eklenecek.
- **TV build:** Uygulama kodu değişmedi; yeni TV build'i gerekmez.

### Codex — Toplu görev 9/10G — Mağaza görselleri — 2026-11-22
- Telifsiz, soyut oyun sahnesi tarzında 1280×720 iki vektör tanıtım görseli hazırlandı: önce/sonra altyazısı ve PC→TV akış şeması. README görselleri gösteriyor.
- **Dosyalar:** `brand/store/once-sonra.svg`, `brand/store/pc-tv-akis.svg`, `README.md` (görsel bağlantıları), bu günlük.
- **Test sonucu:** SVG/XML biçimi ve 1280×720 viewBox doğrulanacak.
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
