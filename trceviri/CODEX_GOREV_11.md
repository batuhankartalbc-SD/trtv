# Codex Görev 11 — TV bağımsız mod: film/dizi altyazılarını TV'nin kendisi okusun

Önce `git pull`, sonra `GELISTIRME_NOTLARI.md` dosyasını oku. Senin alanın: `app/`, `.github/workflows/`, `brand/`, kök `README.md`, `contrib/`. `trceviri/` klasörüne dokunma; PC tarafını Claude aynı anda yapıyor (PC 2.4.0).

## Hedef

Uygulama sadece GTA 6 için değil:
- PS5'teki **bütün oyunlarda** çalışmalı.
- PC hiç açık değilken, **TV'de oynatılan İngilizce altyazılı filmler** için de çalışmalı: YouTube, Plex, Kodi, VLC, tarayıcı vb.

Bugünkü yapıda PC, PS Remote Play'den görüntüyü okuyor ve TV sadece çiziyor. Yeni "bağımsız mod"da TV ekranı kendisi yakalar, yazıyı kendisi okur ve çeviriyi gösterir.

## 0. ÖNCE fizibilite testi (zorunlu, sonucu notlara yaz)

Android'de DRM'li içerik (Netflix, Disney+, Prime, çoğu zaman HDMI girişi) ekran yakalamada **siyah** gelir.
- Küçük bir test ekranı yap: `MediaProjection` ile 1 kare al ve DiagnosticsActivity'de göster.
- Sırasıyla şunlarda dene ve sonucu notlara tablo olarak yaz:
  - YouTube
  - Netflix (varsa)
  - Plex/Kodi/VLC (varsa)
  - TV'nin HDMI girişi (PS5)
- Sütunlar: uygulama | kare geldi mi | siyah mı.
- Siyah gelen kaynaklarda bağımsız mod çalışamaz. Uygulama bunu kullanıcıya dürüstçe söylemeli: "Bu uygulama ekran yakalamaya izin vermiyor (DRM). PS5 için PC + Remote Play kullanın." Gizli yollar arama, DRM atlatma YOK.

## 1. Yakalama + OCR (TV'de)

- Ayarlar'a "Bağımsız mod (film/dizi)" anahtarı ekle. İlk açılışta MediaProjection izni istenir. Android 14+ için foreground service türü `mediaProjection` olmalı.
- Saniyede 4–6 kare al. Sadece ekranın alt %35'ini (altyazı bandı) oku; ayarla %100'e çıkarılabilsin.
- OCR: ML Kit Text Recognition (Latin, cihazda, `com.google.mlkit:text-recognition`).
- Yazı kararlı olunca (2 ardışık karede aynı) satırları gönder. Değişmeyen kareyi tekrar işleme: küçük gri tonlu özet ile karşılaştır.
- Kendi çizdiğin overlay'i yakalayıp tekrar okuma. Ya yakalama anında overlay'i gizle, ya da kendi kutularının içindeki metni yok say.

## 2. Çeviri: önce PC, yoksa cihazda

**PC bağlıysa** (daha iyi çeviri: yerel model + oyun paketi + Gemini) yeni protokolü kullan.

TV→PC:
```
{"t":"ocr","id":17,"src":"film","lines":[{"en":"Where are you going?","b":[x,y,w,h],"lh":0.045}]}
```
- `b` ve `lh` ekran oranı (0–1).
- `src`: `film` ya da `game`.

PC→TV:
```
{"t":"tr","id":17,"tr":["Nereye gidiyorsun?"]}
```
- Aynı sırayla döner. Boş metin = çevirme/gösterme.
- PC aynı `id` ile ikinci kez daha iyi (Gemini) bir çeviri gönderebilir. Son gelen kazanır.

**PC yoksa** ya da 600 ms içinde cevap gelmezse:
- ML Kit Translation EN→TR (`com.google.mlkit:translate`) kullan.
- Model ilk açılışta Wi-Fi'da indirilsin; ilerleme gösterilsin.
- Çevirileri önbellekte tut: LRU, 2000 satır.

## 3. Çizim

- Çevirileri mevcut OverlayView ile, İngilizcenin tam üstüne aynı boyutta ve siyah kutulu çiz (oyundaki stil). Konuşmacı adı yoksa sadece metin.
- Film altyazısına özel:
  - `- Hey.` gibi tireli diyalog satırlarını koru.
  - `[door creaks]`, `(sighs)` gibi efekt yazılarını `[kapı gıcırdıyor]` biçiminde köşeli parantezle göster.
  - `♪` içeren şarkı satırlarını gösterme.
- Altyazı ekrandan kalkınca 300 ms içinde çeviriyi de kaldır.

## 4. Ayarlar / kullanım

- Ayarlar'a "Mod" seçimi ekle:
  - **PC'den (PS5 / Remote Play)**: bugünkü davranış, varsayılan.
  - **TV'nin kendisi (film/dizi)**: bağımsız mod.
- Bağımsız moddayken kumanda kısayolu: göster/gizle.
- Ana ekranda tek satır durum: `Bağımsız mod · OCR 45 ms · Çeviri: PC (Gemini)` ya da `Çeviri: cihazda`.
- Help/Onboarding'e kısa bölüm ekle: "Film izlerken". Netflix/Disney+ gibi DRM'li uygulamalarda çalışmadığını ve YouTube'un kendi "Otomatik çeviri → Türkçe" altyazısının da olduğunu yaz.

## 5. Test ve teslim

- JVM testleri:
  - satır kararlılık mantığı
  - film satırı temizleme: `♪`, `[...]`, tire
  - `tr` mesajında aynı id'ye ikinci cevabın öncekini ezmesi
- Build ve APK, CI'da `latest` sürümüne yüklensin.
- Notlara kayıt düş: fizibilite tablosu, değişen dosyalar, build numarası, protokol eklemeleri (`ocr` / `tr`).

Bu görev büyük. Sırayla 0 → 1 → 2 → 3 → 4 → 5 git; her adım ayrı commit olsun, her adımdan sonra push et.
