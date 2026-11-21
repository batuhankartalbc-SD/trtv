# Codex görevi 6 — TV'den oyun profili ve çeviri motoru seçimi + Yardım ekranı

## 0. Önce
- `git pull`, sonra `GELISTIRME_NOTLARI.md`'yi oku.
- `CODEX_GOREV_5` bitmediyse önce onu bitir:
  - PC testleri CI (`pc-tests.yml`),
  - kökteki `README.md`,
  - TV'de Tanılama ekranı.
- **Alanın:** `app/`, `.github/workflows/`, `brand/`, kökteki `README.md`.
- **Dokunma:** `trceviri/` (Claude yönetiyor).
- **Bitince:** `GELISTIRME_NOTLARI.md` → "Codex" günlüğüne yaz.

## 1. Ayarlar ekranına iki satır
Bilgisayar tarafı **hazır** (Claude yazdı, canlı sürüm 2.3.1 ile çıkıyor).

**Bilgisayarın gönderdiği bilgi.** Bilgisayar `style` mesajında şu alanları gönderiyor:

| Alan | Örnek |
|---|---|
| `profiles` | `["GTA 6","GTA 5","Red Dead Redemption 2", …]` |
| `profile` | `"GTA 6"` |
| `engine` | `"local"` \| `"gemini"` \| `"free"` |
| `engines` | `["local","gemini","free"]` |

Bu alanları `OverlayService`'teki ayar anlık görüntüsüne (`TvSettings`) ekle.

**Satırlar:**

| Satır | Değer ve mesaj |
|---|---|
| **Oyun profili** | `profiles` listesinde sol/sağ ile gezilir. OK (ya da değer değişince) `{"t":"set","k":"profile","v":"<ad>"}` gönderilir. |
| **Çeviri motoru** | Gösterilen adlar: `local` → "Yerel (anlık)", `gemini` → "Gemini (en doğal)", `free` → "Ücretsiz (internet)". Gönderilen: `{"t":"set","k":"engine","v":"local"}` |

**Uyarı:** Motor değişince bilgisayar çeviriyi yeniden başlatır. Satırın altına küçük bir not ekle: "Değişince çeviri 1–2 sn durur".

**Liste boş ya da bilgisayar bağlı değilse:** Satırlar pasif görünsün.

## 2. Yardım ekranı (TV)
- **Yer:** `MainActivity`'ye **"Yardım"** düğmesi ekle. Düğme `HelpActivity`'yi açar. Düz koyu tema, büyük yazı, D-pad ile kaydırılır, **Geri** ile kapanır.
- **İçerik (Türkçe, kısa):**
  1. Bilgisayara **Brolis Game Translate**'i kur: `github.com/batuhankartalbc-SD/trtv` → Releases → `TRCeviri-Kurulum.exe`.
  2. PS Remote Play'i aç, PS5'e bağlan. Oyunda **altyazıları aç**.
  3. Bilgisayar ve TV **aynı modemde** olsun. Bilgisayardaki uygulama TV'yi kendisi bulur.
  4. **Türkçe kayıyorsa:** Ana ekran → **Kumandayla hizala**.
  5. **Bir şey çalışmıyorsa:** Ana ekran → **Tanılama** (görev 5).
- **Ek bilgiler:** Altta TV'nin IP adresini ve uygulama sürümünü göster.

## 3. Bitti kriteri
- `main`'e push et.
- `build.yml` (ve görev 5'te eklediysen `pc-tests.yml`) **başarılı** bitsin.
- `GELISTIRME_NOTLARI.md` günlüğüne yaz:
  - eklediğin satırlar,
  - dosyalar,
  - build numarası.
- Protokole **yeni mesaj türü eklemiyorsun**; sadece var olan `set` mesajının yeni anahtarlarını (`profile`, `engine`) kullanıyorsun.
