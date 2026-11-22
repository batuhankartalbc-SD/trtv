<p align="center">
  <img src="brand/wordmark.svg" alt="Brolis Game Translate" width="560">
</p>

# Brolis Game Translate

PS5 oyunlarındaki İngilizce konuşma, menü ve kontrolleri anında Türkçeye çevirir; Türkçe yazı TV'de oyunun tam üstünde, aynı boyutta görünür.

## İlk 5 dakika

1. [PC kurulum dosyasını indirin](https://github.com/batuhankartalbc-SD/trtv/releases/download/pc-latest/TRCeviri-Kurulum.exe) (`pc-latest`) ve Windows bilgisayarınıza kurun.
2. [TV APK'sını indirin](https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk) (`latest`); Android TV'ye Downloader ile bağlantıyı açarak veya USB bellekten yükleyin.
3. Bilgisayar ve TV'nin aynı Wi-Fi ağına bağlı olduğundan emin olun.
4. PC'deki kurulum sihirbazını sonuna kadar izleyin; TV uygulamasını açıp ekran üstü iznini verin.
5. Kısayollar: **F8** katman, **F9** duraklat, **F6** son konuşma, **F10** bölgeler, **F11** yeniden çevir.

| Sorun | Çözüm |
|---|---|
| TV bulunamadı | PC ve TV'nin aynı Wi-Fi'da olduğunu, TV uygulamasının açık kaldığını ve ağın cihazlar arası iletişimi engellemediğini kontrol edin. |
| Türkçe gelmiyor | Oyunda altyazıları açın; PC uygulamasının çalıştığını ve TV'de ekran üstü izninin verildiğini doğrulayın. |
| Yazılar kayıyor | TV'de **Kumandayla hizala** ekranını açın; oklarla kaydırıp OK ile boyut moduna geçin. |
| Gemini kota doldu | Kota bekleme süresi bitene kadar yerel çeviriyle devam edin. |
| Pencere bulunamadı | PS Remote Play'i açıp PS5'e bağlanın, oyun görüntüsünü görünür tutun ve PC uygulamasında pencereyi yenileyin. |

## İndir

- **Bilgisayar (Windows):** [TRCeviri-Kurulum.exe](https://github.com/batuhankartalbc-SD/trtv/releases/download/pc-latest/TRCeviri-Kurulum.exe)
- **Android TV / Google TV:** [Brolis Game Translate TV (APK)](https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk)

### TV'ye Downloader ile kurulum

1. Android TV'de Play Store'dan **Downloader** uygulamasını yükleyin.
2. TV ayarlarında Downloader için bilinmeyen uygulama yükleme iznini açın.
3. Downloader'da APK bağlantısını açın: `https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk`
4. İndirme bitince **Yükle**'yi seçin. Uygulama açıldığında ekran üstü iznini verin.

## Nasıl çalışır?

```text
PS5 → PS Remote Play → Bilgisayar (OCR + çeviri) → Aynı ağdaki Android TV → Oyun görüntüsünün üstünde Türkçe
```

Bilgisayarda PS Remote Play görüntüsü okunur ve çevrilir. TV uygulaması Türkçe metni PS5'in HDMI görüntüsünün üzerine yerleştirir. Bilgisayar ve TV aynı yerel ağa bağlı olmalıdır.

## Tanıtım görselleri

<p align="center">
  <img src="brand/store/once-sonra.svg" alt="İngilizce altyazıdan Türkçe altyazıya önce ve sonra" width="720">
</p>

<p align="center">
  <img src="brand/store/pc-tv-akis.svg" alt="PC'den TV'ye çeviri bağlantı şeması" width="720">
</p>

## Gerekenler

- Windows 10 veya Windows 11 bilgisayar
- PS5 ve bilgisayarda PS Remote Play
- Aynı yerel ağda Android TV veya Google TV
- Oyunda altyazıların açık olması

## Özellikler

- Yerel İngilizce→Türkçe anlık çeviri ve isteğe bağlı Gemini iyileştirmesi
- GTA 6 için hazır oyun paketi ve oyun profilleri
- TV kumandasıyla yazı ayarları ve hizalama
- İsteğe bağlı Türkçe seslendirme
- Bilgisayar ve TV uygulamaları için otomatik güncelleme

## Sık sorulanlar

**Türkçe yazılar çıkmıyor.** Oyunun ayarlarında altyazıların açık olduğunu, bilgisayar uygulamasının çalıştığını ve TV'de ekran üstü izninin verildiğini kontrol edin.

**TV bulunamadı.** Bilgisayar ile TV'nin aynı ağa bağlı olduğuna ve Brolis Game Translate TV uygulamasının açık olduğuna bakın. TV'deki Tanılama ekranı bağlantı durumunu gösterir.

**Çeviri kayıyor.** TV uygulamasında **Kumandayla hizala** ekranını açıp oklarla konumu, OK ile ölçek modunu ayarlayın.

## Lisans ve kaynak

Yerel çeviri modeli [Helsinki-NLP/opus-mt-tc-big-en-tr](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-en-tr) modelidir ve model kartında **CC-BY-4.0** olarak lisanslanmıştır. Kaynak gösterimi için [model kartına](https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-en-tr) bakın.
