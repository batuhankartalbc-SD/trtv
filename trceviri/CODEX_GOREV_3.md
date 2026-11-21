# Codex görevi 3 — TRÇeviri TV: konuşma geçmişi, akıcı görünüm, testler

Önceki iki görevi (hizalama, güncelleme, Ayarlar ekranı) başarıyla tamamladın, teşekkürler.

## Kurallar (öncekiyle aynı)
- Sadece `app/` ve `.github/workflows/` altında çalış. Depo: `https://github.com/batuhankartalbc-SD/trtv`, dal `main`. Başlamadan önce `git pull` yap.
- Bilgisayar (Python) koduna dokunma; o tarafı Claude yazıyor.
- Mevcut mesaj protokolünü değiştirme. Bu görev için yeni bir mesaj türü **gerekmiyor**.
- Yeni çalışma zamanı bağımlılığı ekleme (AndroidX dahil). Arayüz metinleri **Türkçe** olsun.
- Katman (`OverlayView`) odak almamaya devam etmeli. Oyun sırasında kumanda tuşları oyuna gitmeli.
- `debug.p12` ve imzalama ayarlarına, paket adına (`com.trtv`) ve `latest` release / `a.apk` adına dokunma. Kendini güncelleme buna bağlı.
- `main`'e push et ve GitHub Actions derlemesinin **başarılı** bittiğini doğrula.

## Görev 1 — Konuşma geçmişi ekranı (TV'de)
Kaçırılan konuşmaları TV'den kumandayla okumak için.

1. **Geçmişi tutma.** `OverlayService`, bilgisayardan gelen `items` mesajlarından **`k == "subtitle"`** olanların Türkçesini (`tr`, varsa konuşmacı `s`) sırayla saklasın.
   - Son **50** satırı bellekte tutsun.
   - Arka arkaya gelen aynı metni tekrar eklemesin.
   - Bilgisayar `items` mesajını aynı satır için birkaç kez gönderebilir (konum güncellemesi, iyileştirilmiş çeviri). Aynı konuşmacı ve çok benzer metin gelirse **son kaydı güncellesin**, yeni satır eklemesin.
2. **Ekran.** `MainActivity`'ye **"Konuşma geçmişi"** düğmesi ekle. Düğme `HistoryActivity`'yi açar.
   - Tema: yarı saydam, `@android:style/Theme.Translucent.NoTitleBar`. Ekranın sol yarısında koyu panel olsun.
   - En yeni satır üstte, büyük yazıyla. Konuşmacı adı kendi renginde: `items` içindeki `sc` alanı (varsa).
   - D-pad ile kaydırılır, **Geri** ile kapanır.
   - Liste boşsa "Henüz konuşma yok" yazsın.
3. **Kalıcılık.** Geçmiş uygulama kapanınca silinebilir; kalıcı olması gerekmez.

## Görev 2 — Akıcı görünüm (titreme ve ani belirme olmasın)
1. **Geçişler.** `OverlayView`'da her çeviri kutusu **~120 ms içinde belirsin**, kalkarken **~120 ms içinde kaybolsun** (alpha animasyonu).
   - Aynı kutu yerinde kalıp sadece metni değişirse (iyileştirilmiş çeviri) animasyon **olmadan** anında güncellensin.
2. **Önbellek.** Her `onDraw`'da metin satırlara bölünüp ölçülmesin. Her öğenin yerleşimi (satırlar, yazı boyutu, kutu) öğe değişene kadar önbellekte tutulsun.
   - Anahtar olarak `tr` + kutu koordinatları + stil değerleri yeterli.
   - Amaç: 4K TV'de bile akıcı çizim.
3. **Değişmeyecekler.** Çizim kuralları aynı kalsın:
   - birebir boyut,
   - siyah zemin varsayılanı,
   - hizalama dönüşümü (`dx`, `dy`, `sx`, `sy`).

## Görev 3 — Testler ve CI
1. **Saf Kotlin fonksiyonları.** Android'e bağımlı olmayan saf fonksiyonları ayrı bir dosyaya taşı, örneğin `Layout.kt` / `Protocol.kt`:
   - metni satırlara bölme (`wrap`),
   - kalibrasyon dönüşümü (`mx` / `my` mantığı),
   - `items` JSON ayrıştırma,
   - geçmişte "aynı satır mı" karşılaştırması.
2. **JVM birim testleri.** `app/src/test/` altına bu fonksiyonlar için **JVM birim testleri** yaz. Sadece JUnit kullan; `testImplementation("junit:junit:4.13.2")` test bağımlılığı olarak eklenebilir.
3. **CI.** `.github/workflows/build.yml`'e `gradle testDebugUnitTest` adımını **APK derlemesinden önce** ekle. Test kırılırsa APK yayınlanmasın.
   - Mevcut adımları ve release kısmını bozma.

## Bittiğinde
Kısa bir özet ver:
- eklediğin/değiştirdiğin dosyalar,
- test sayısı,
- build numarası.
