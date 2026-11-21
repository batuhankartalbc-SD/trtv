# Brolis Game Translate: oyun içi anlık Türkçe çeviri

PS5 oyunlarını bilgisayarda **PS Remote Play** (ya da chiaki‑ng) penceresinde oynarken ekrandaki İngilizce yazıların üstünü kapatır ve Türkçesini anında gösterir. Çevirdiği yazılar:

- diyalog altyazıları,
- görev yazıları,
- oyun içi telefon,
- ipucu kutuları.

Oyuna hiçbir şekilde dokunmaz, sadece ekranı okur.

## Kurulum ve başlatma

1. **`run.bat`** dosyasına çift tıklayın. İlk açılışta kendi kendine kurulur (birkaç dakika). Sonraki açılışlar hızlıdır.
2. Bilgisayarda **PS Remote Play** uygulamasını açıp PS5'e bağlanın.
   - **CouchSubs kapalı olmalı.** PS5 aynı anda tek bir uzaktan bağlantıya izin verir.
3. Brolis Game Translate'de **Oyun penceresi** listesinden `PS Remote Play` seçin, sonra **▶ Başlat**'a basın.
4. Oyunda **altyazıları açın.** Program yazıyı ekrandaki İngilizce altyazıdan okur; altyazı kapalıysa çevirecek bir şey olmaz.

## Çeviri motoru

| Motor | Anahtar | Not |
|---|---|---|
| Ücretsiz (MyMemory) | Gerekmez | Hazır ayar; günlük kotası var |
| **Google Gemini** | Google AI Studio'dan ücretsiz anahtar | **Önerilen**: en doğal çeviri, bağlamı ve argoyu anlar |
| OpenAI / Claude / DeepL | Kendi anahtarı | İsteğe bağlı |

Anahtarı **Çeviri** sekmesine yapıştırın, **Test et** ile deneyin, ardından **Kaydet**'e basın. Anahtar bilgisayarınızda Windows şifrelemesiyle saklanır.

## Otomatik mod (varsayılan)

**Ana** sekmesindeki "Otomatik mod" açıkken bölge çizmenize gerek yok. Program her karede ekranın tamamını tarar ve İngilizce yazıları kendisi bulur:

- **Altyazılar:** alt ortada, konuşmacı adıyla gösterilir.
- **Diğer yazılar:** ipucu kutuları, görev yazıları, telefon/menü öğeleri, GPS yazıları. Hepsinin üstü kapatılıp Türkçesi aynı yere yazılır.

Para, mesafe ve saat gibi sayılar ile zaten Türkçe olan yazılar çevrilmez. Çok küçük yazıları kaçırırsa **Gelişmiş → Otomatik tarama genişliği** değerini büyütün; daha yavaş ama daha hassas tarar.

## Bölgeler (otomatik mod kapalıyken)

GTA 6 profili hazır gelir:

| Bölge | Varsayılan |
|---|---|
| Alt ortadaki diyalog | Açık |
| Sol üst ipucu kutusu | Açık |
| Görev yazısı | Kapalı |
| Oyun içi telefon | Kapalı |

Değiştirmek için:

1. **Bölgeler → Bölge düzenleyiciyi aç** (ya da oyun sırasında **F10**).
2. Boş alanda fareyle sürükleyerek yeni kutu çizin.
3. Kutuyu sürükleyip taşıyın, sağ alt köşesinden boyutlandırın.
4. Sağdan türünü seçin (Diyalog, Görev, Telefon, İpucu…) ve **Kaydet**'e basın.

## Kısayollar (oyun açıkken de çalışır)

| Tuş | İşlev |
|---|---|
| F8 | Türkçe katmanı göster/gizle |
| F9 | Duraklat / devam |
| F10 | Bölge düzenleyici |
| F11 | Son satırı yeniden çevir |
| F7 | Bölge çerçevelerini göster (ayar yaparken) |

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Hiç Türkçe çıkmıyor | Oyunda altyazı açık mı? **F7** ile çerçeveleri açıp altyazının kutunun içinde kaldığını kontrol edin. |
| "Pencere bulunamadı" | Remote Play açık ve simge durumunda değil mi? **Pencereleri yenile**'ye basın. |
| Soldaki GPS / mesafe yazısı karışıyor | Diyalog kutusunu düzenleyicide biraz daraltın. |
| Ücretsiz motor durdu | Günlük kota dolmuştur; Gemini anahtarı girin. |
| Yazılar küçük ya da büyük | **Görünüm → Yazı boyutu çarpanı**. |

Kayıtlar: `%APPDATA%\TRCeviri\logs\trceviri.log`
