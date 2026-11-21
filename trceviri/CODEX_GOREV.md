# Codex görevi: TRÇeviri TV (Android TV uygulaması) — kumandayla hizalama + kendini güncelleme

Bu görev **yalnızca Android TV uygulamasıyla** ilgilidir. Bilgisayar (Python) tarafına **dokunma**; o tarafı başka bir geliştirici (Claude) eşzamanlı yazıyor.

## Depo
- GitHub: `https://github.com/batuhankartalbc-SD/trtv` (public, `main` dalı)
- Klonla ve `app/` klasöründe çalış. Sadece `app/` altındaki dosyaları değiştir.
- **Değiştirme:** `.github/workflows/build.yml`, `debug.p12`, `settings.gradle.kts`, `build.gradle.kts` (kök) ve `app/build.gradle.kts` içindeki imzalama ayarları.
- `main`'e push edince GitHub Actions APK'yı derler ve `latest` sürümüne `a.apk` olarak yükler. `versionCode` = GitHub run numarasıdır. Release adı `Build <run>` olur.
- Paket adı `com.trtv` aynı kalmalı. Böylece mevcut kurulumun üstüne kurulabilir.

## Mevcut mimari (bozma)
- `OverlayService.kt`: ön plan servisi. TCP **47800** portunu dinler. Bilgisayar bağlanır ve satır başına bir JSON gönderir:
  - `hello`, `style`, `items`, `clear`, `visible`, `ping`.
  - TV, `hello` ve `pong` ile cevap verir.
  - Ana bağlantının yazıcısı `send(w, JSONObject)` ile kullanılabilir.
- `OverlayView.kt`: `TYPE_APPLICATION_OVERLAY` katmanı. Odak almaz, dokunulmaz. Çevirileri HDMI görüntüsünün üstüne çizer.
  - Hizalama değerleri `style` mesajında gelir: `dx`, `dy` (ekranın kesri), `sx`, `sy` (ölçek), `calib` (bool).
  - `calib=true` iken algılanan İngilizce yazıların çevresine mavi çerçeve çizer.
- `MainActivity.kt`: durum ekranı. Servisi başlatır, "Oyuna dön" düğmesiyle kapanır.
- `BootReceiver.kt`: TV açılınca servisi başlatır.

## Görev 1 — Kumandayla hizalama (TV'den, klavye gerekmeden)

1. **Yeni aktivite.** `CalibrateActivity.kt` ekle.
   - **Saydam tema:** `@android:style/Theme.Translucent.NoTitleBar`. Arkada PS5'in HDMI görüntüsü görünmeye devam etmeli.
   - Açılınca bilgisayara `{"t":"cal","a":"CAL_MODE_ON"}` gönder. Bilgisayar hizalama modunu açar ve TV'ye `calib=true` stili yollar.
   - **Kumanda tuşları:**

     | Tuş | Gönderilen |
     |---|---|
     | DPAD_LEFT / RIGHT / UP / DOWN | `{"t":"cal","a":"CAL_LEFT"}` / `CAL_RIGHT` / `CAL_UP` / `CAL_DOWN` |
     | DPAD_CENTER (OK) | Kaydırma ↔ ölçek modu arasında geçiş |
     | Ölçek modunda yukarı / aşağı | `CAL_BIGGER` / `CAL_SMALLER` |
     | Uzun OK veya MENU | `CAL_RESET` |
     | BACK | `{"t":"cal","a":"CAL_MODE_OFF"}` gönder ve aktiviteyi kapat |

   - Tuş basılı tutulunca tekrar gönder (~8/sn).
   - **Ekran yazısı:** Üstte küçük, yarı saydam bir şerit göster. Örnek: "Hizalama — Oklar: kaydır · OK: ölçek modu · Geri: bitti". Ayrıca o anki modu göster. Değerleri bilgisayar gönderir; şerit mesajla güncellenebilir, ama zorunlu değil.
2. **Mesajı bilgisayara iletme.** `OverlayService` içine statik bir fonksiyon ekle, örneğin `fun sendToPc(o: JSONObject): Boolean`.
   - Fonksiyon mevcut ana bağlantının (`client`) writer'ı ile gönderir.
   - Bağlantı yoksa `false` döner. Bu durumda aktivite "Bilgisayar bağlı değil" yazar.
   - Writer'ı thread-safe sakla.
3. **Giriş noktaları.**
   - `MainActivity`'ye büyük bir **"Kumandayla hizala"** düğmesi ekle.
   - `CalibrateActivity`'yi ayrı bir launcher kısayolu olarak **ekleme**; sadece MainActivity'den açılsın.
4. **Bilgisayar tarafı (bilgin olsun; sen yazma).** Bilgisayar `{"t":"cal","a":...}` mesajını alınca:
   - `CAL_MODE_ON` / `CAL_MODE_OFF` ile hizalama modunu açıp kapatır,
   - diğer eylemleri uygular,
   - TV'ye yeni `style` mesajı gönderir.

## Görev 2 — TV uygulamasının kendini güncellemesi

1. **Sürüm denetimi.**
   - Servis başladığında ve sonra 6 saatte bir şu adrese bak: `https://api.github.com/repos/batuhankartalbc-SD/trtv/releases/tags/latest`.
   - Gelen JSON'da `name` = `"Build N"` olur. `N > BuildConfig.VERSION_CODE` (ya da `packageManager` ile okunan `versionCode`) ise güncelleme vardır.
   - **İzin:** `INTERNET` zaten var.
2. **Güncelleme varsa.**
   - Katmanda (`OverlayView.banner`) 6 saniyelik bir bildirim göster: "Güncelleme var — TRÇeviri TV'yi açıp Güncelle'ye basın".
   - MainActivity'de **"Güncelle (Build N)"** düğmesi görünsün.
3. **Güncelle düğmesi.**
   - `a.apk`'yı indir. Adres: `browser_download_url` alanı ya da `https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk`. Dosyayı `cacheDir`'e kaydet.
   - **FileProvider** ile (`androidx` olmadan; `android.support` da yok) sistem yükleyicisini aç. AndroidX eklemek istemiyorsan iki seçenek var:
     - kendi minimal `ContentProvider`'ını yaz,
     - ya da `PackageInstaller` session API'sini kullan. **Önerilen bu**, FileProvider gerektirmez.
   - Gereken izin: `REQUEST_INSTALL_PACKAGES`.
   - Kullanıcı "bilinmeyen kaynak" iznini vermemişse `Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES` ekranını aç.
4. **İndirme sırasında.** MainActivity'de ilerleme yüzdesini göster.
5. **Ağ yoksa ya da hata olursa.** Sessizce geç; uygulama çalışmaya devam etsin.

## Kurallar
- Kotlin. `minSdk 28`, `targetSdk 36`. **Yeni bağımlılık ekleme** (AndroidX dahil); sadece Android SDK kullan.
- Bütün arayüz metinleri **Türkçe** olmalı.
- Mevcut katman davranışını **bozma**. Katman odak almamalı, kumanda tuşları normalde oyuna gitmeli; tuşları yalnızca CalibrateActivity açıkken yakala.
- Ağ işleri ana thread'de yapılmamalı.
- Kodu derlenebilir bırak. `main`'e push et. GitHub Actions'ın **başarılı** bittiğini kontrol et: `gh run list -R batuhankartalbc-SD/trtv`.
- Bittiğinde kısa bir özet ver:
  - eklediğin mesaj türleri,
  - değiştirdiğin dosyalar,
  - build numarası.
