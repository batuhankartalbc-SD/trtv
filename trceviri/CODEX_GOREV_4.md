# Codex görevi 4 — Ortak notlar + "Brolis Game Translate" markası (logo + TV)

## 0. Önce oku
- `git pull`, ardından deponun kökündeki **`GELISTIRME_NOTLARI.md`** dosyasını baştan sona oku.
  - Mimari, PC↔TV protokolü ve iş bölümü orada.
  - **Bilgisayar uygulamasının kaynağı artık depoda:** `trceviri/` klasörü. Tek doğru kaynak budur; `E:\TRCeviri` / "BrolisCeviri.exe" gibi eski kopyalarda **çalışma**.
- **İş bölümü:**
  - **Senin alanın:** `app/` (TV uygulaması), `.github/workflows/` ve yeni `brand/` klasörü.
  - **Dokunma:** `trceviri/` (bilgisayar uygulaması). Claude yönetiyor. PC'de ne değişmesi gerekiyorsa `GELISTIRME_NOTLARI.md` günlüğüne **istek** olarak yaz, Claude uygular.
- **İş bitince:** `GELISTIRME_NOTLARI.md` → "Codex" bölümüne şunları yaz:
  - ne yaptığın,
  - değiştirdiğin dosyalar,
  - build numarası,
  - protokole eklediğin mesajlar,
  - Claude'dan istediklerin.
- **Önceki görevlerinden kalanlar:** `CODEX_GOREV_3` (konuşma geçmişi, akıcı görünüm, testler) bittiyse günlüğe yaz. Bitmediyse önce onları tamamla.

## 1. Logo ve marka dosyaları (`brand/`)
**Yeni ad:** **Brolis Game Translate**. Kısa ad: **Brolis**.

**Tasarım:**
- Koyu temaya uyan, sade, modern bir logo.
- Renkler: zemin `#0A0E13`, vurgu nane yeşili `#3EE6A0`, ikincil mor `#B79CFF`.
- Konu: oyun kumandası + konuşma balonu ya da "EN→TR" fikri.
- **Telif / marka uyarısı:** Gerçek oyun ya da şirket logolarını (PlayStation, Rockstar vb.) kullanma veya taklit etme.

Şu dosyaları **`brand/`** klasörüne koy:

| Dosya | Ne için |
|---|---|
| `logo.svg` | Kare simge, vektör, saydam zemin |
| `logo-512.png` | Kare, saydam zemin |
| `logo.ico` | Windows simgesi: 16/24/32/48/64/128/256 boyutları tek dosyada |
| `wordmark.svg` | Simge + "Brolis Game Translate" yazısı, yatay |
| `tv-banner-320x180.png` | Android TV launcher banner'ı (xhdpi için 320×180 px; istersen `tv-banner-640x360.png` da ekle) |

Ayrıca kısa bir `brand/README.md` yaz:
- renk kodları,
- yazı tipi önerisi (açık lisanslı olsun, örneğin Inter / Manrope; **OFL** lisanslı font kullanacaksan lisans dosyasını da koy),
- logonun kullanım kuralları.

## 2. TV uygulamasında marka (`app/`)
1. **Ad:** Uygulama adını **"Brolis Game Translate"** yap: `android:label`.
   - **Paket adı `com.trtv` değişmesin.** Kendini güncelleme buna bağlı.
2. **Banner ve ikon:** `@drawable/banner` yerine `brand/tv-banner` görselini kullan. Uygulama ikonunu da yeni logo yap.
3. **Metinler:** `MainActivity`'de görünen başlık metinlerini "TRÇeviri TV" yerine **"Brolis Game Translate"** yap. Katmandaki bildirimlerde (banner, bağlantı uyarısı) kısa ad **"Brolis"** kullanılabilir.
4. **Protokolü bozma:** `hello` cevabındaki `"app":"trceviri-tv"` **aynı kalmalı**. Bilgisayar TV'yi bununla tanıyor. Değiştirmek istersen önce notlara yaz.

## 3. Bitti kriteri
- `main`'e push et, GitHub Actions derlemesi **başarılı** olsun.
- `GELISTIRME_NOTLARI.md` günlüğünü güncelle.
- Kısa özet ver: dosyalar, build numarası.
