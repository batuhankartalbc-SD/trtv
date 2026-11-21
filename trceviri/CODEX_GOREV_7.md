# Codex görevi 7 — Yazı tipi seçimi ("sanki oyun Türkçeymiş")

## 0. Önce
- `git pull`, `GELISTIRME_NOTLARI.md`'yi oku. Görev 6 için teşekkürler; TV'ye **Build 32** kuruldu.
- **Alanın:** `app/`, `brand/`, `.github/workflows/`, kök `README.md`.
- **Dokunma:** `trceviri/`. Bilgisayar tarafını Claude yapacak (aşağıda yazıyor).
- **Bitince:** `GELISTIRME_NOTLARI.md` günlüğüne yaz.

## Amaç
Oyun altyazıları genelde dar, kalın yazı tipleri kullanıyor. Türkçe metin de benzer bir yazı tipiyle çizilirse daha "orijinal" görünür. Kullanıcı yazı tipini **TV'den ve bilgisayardan** seçebilsin.

## 1. Yazı tipi dosyaları (`brand/fonts/`)
**Lisans kuralı:** Sadece **SIL Open Font License (OFL)** lisanslı yazı tipleri kullan. Oyunların kendi fontlarını (Rockstar vb.) **kullanma ve taklit etme**.

**Türkçe karakter şartı:** Fontlar Türkçe karakterleri desteklemeli: **ç ğ ı İ ö ş ü Ç Ğ Ö Ş Ü**.

Şu üç yazı tipi ailesinden birer kalın kesim ekle:

| Anahtar | Ad | Örnek font | Dosya adı |
|---|---|---|---|
| `condensed` | "Oyun stili (dar)" | Barlow Semi Condensed SemiBold ya da Bold | `brand/fonts/condensed.ttf` |
| `rounded` | "Yuvarlak" | Nunito Bold | `brand/fonts/rounded.ttf` |
| `clean` | "Sade" | Inter SemiBold ya da Bold | `brand/fonts/clean.ttf` |

Ayrıca:
- Her fontun lisans metnini ekle: `brand/fonts/OFL-<ad>.txt`.
- `brand/fonts/README.md` yaz: font adları, sürüm, kaynak bağlantısı, lisans.

Mevcut "Varsayılan" seçenek dosya gerektirmez. TV'de sistemin `sans-serif-medium` kalın fontudur, PC'de Segoe UI.

## 2. Protokol (yeni alan + yeni `set` anahtarı; yeni mesaj türü yok)
| Yön | Mesaj |
|---|---|
| PC → TV | `style` mesajına `"font": "default"`, `"condensed"`, `"rounded"` ya da `"clean"` alanı eklenecek. Bunu Claude ekleyecek. |
| TV → PC | `{"t":"set","k":"font","v":"condensed"}` |

`GELISTIRME_NOTLARI.md` → protokol bölümüne bu iki satırı **sen ekle**.

## 3. TV (`app/`)
- **Fontları uygulamaya ekle:** `brand/fonts/*.ttf` dosyalarını `app/src/main/res/font/` (ya da `assets/fonts/`) içine kopyala. Kaynak adları küçük harf olmalı.
- **`OverlayView`:** `style` mesajındaki `font` alanına göre `Typeface` seçsin.
  - `default` → mevcut davranış.
  - Diğerleri → ilgili font, `Typeface.BOLD`.
  - Çizim ve yerleşim önbelleği varsa font değişince temizlensin.
- **Ayarlar ekranı:** Yeni satır **"Yazı tipi"**. Sol/sağ ile Varsayılan / Oyun stili (dar) / Yuvarlak / Sade arasında gezilsin; OK ya da değişimde `set` mesajı gitsin.
  - Satırda bir önizleme olsun: örneğin "Polisler sahil yolunu kapatmış." cümlesi o fontla.
- **Geriye uyumluluk:** `style` içinde `font` yoksa `default` kullan. Eski bilgisayar sürümleriyle çalışmaya devam etsin.

## 4. Bilgisayar tarafı — Claude yapacak (bilgin olsun)
- `brand/fonts/*.ttf` dosyalarını uygulamaya paketleyecek.
- Görünüm sayfasına "Yazı tipi" seçeneği ekleyecek.
- Bilgisayar ekranındaki çizimde aynı fontu kullanacak.
- `style` mesajına `font` alanını ekleyecek, `set font` mesajını karşılayacak.

## Bitti kriteri
- `main`'e push et; `build.yml` ve `pc-tests.yml` başarılı bitsin.
- Günlüğe yaz: font adları ve lisansları, dosyalar, build numarası.
