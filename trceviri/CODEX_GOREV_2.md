# Codex görevi 2 — TRÇeviri TV: kumandayla Ayarlar ekranı + bağlantı göstergesi

Önceki görevi (kumandayla hizalama + kendini güncelleme) başarıyla yaptın, teşekkürler. Aynı kurallar geçerli:
- Sadece `app/` altında çalış. Depo: `https://github.com/batuhankartalbc-SD/trtv`, dal `main`.
- Önce `git pull` yap; Claude, senin güncelleyicine `STATUS_PENDING_USER_ACTION` desteği ekledi.
- Bilgisayar (Python) koduna dokunma; o tarafı Claude yazıyor. Aşağıdaki mesajları bilgisayar tarafı **zaten karşılıyor**.
- Yeni bağımlılık ekleme (AndroidX dahil). Arayüz metinleri **Türkçe** olsun. Ağ işleri ana thread'de yapılmasın.
- Katman (`OverlayView`) odak almamaya devam etmeli. Oyun sırasında kumanda tuşları oyuna gitmeli.
- `main`'e push et ve GitHub Actions derlemesinin **başarılı** bittiğini doğrula.

## Görev 1 — "Ayarlar" ekranı (kumandayla)

**Yer:** `MainActivity`'ye **"Ayarlar"** düğmesi ekle. Düğme yeni `SettingsActivity`'yi açar.

**Tema:** `@android:style/Theme.Translucent.NoTitleBar`. Arkada oyun görünsün. Ekranın sağ tarafında yarı saydam koyu bir panel olsun.

**Kullanım:** D-pad ile gezilen, büyük yazılı bir liste.
- OK değiştirir.
- Sol/sağ değer artırır/azaltır.
- Geri kapatır.

**Satırlar ve bilgisayara giden mesajlar:**

Her değişiklikte `OverlayService.sendToPc(...)` çağrılır. Mesaj biçimi:

```json
{"t":"set","k":"<anahtar>","v":<değer>}
```

| Satır | Anahtar (`k`) | Değer (`v`) |
|---|---|---|
| Türkçe yazılar: Açık / Kapalı | `visible` | `true` / `false` |
| Yazı boyutu: %60 … %250, adım %5 | `font_scale` | `0.6` … `2.5` |
| Yazı arkası | `bg_mode` | `"black"` Simsiyah / `"semi"` Yarı saydam / `"none"` Kutu yok / `"game"` Oyun rengi |
| Konuşmacı renkleri: Açık / Kapalı | `speaker_colors_on` | bool |
| Türkçe seslendirme: Açık / Kapalı | `tts_enabled` | bool |
| Konuşmalar | `cat_dialogue` | bool |
| Menüler | `cat_menu` | bool |
| Kontroller | `cat_controls` | bool |
| Diğer yazılar | `cat_other` | bool |
| GPS / yön | `cat_nav` | bool |
| **"Son konuşmayı tekrar göster"** (eylem) | `replay` | `true` |

"Son konuşmayı tekrar göster" satırına basılınca:
- mesaj gönderilir,
- ekran kapanır, böylece oyunda Türkçe görünür.

**Mevcut değerleri gösterme.** Bilgisayar, bağlanınca ve her ayar değişikliğinde `style` mesajı gönderir. Bu mesajda şu alanlar var:

| Alan | Anlamı |
|---|---|
| `scale` | yazı boyutu |
| `bgm` | yazı arkası |
| `tts` | seslendirme (bool) |
| `spkcol` | konuşmacı renkleri (bool) |
| `cats` | `{"dialogue":bool,"menu":bool,"controls":bool,"other":bool,"nav":bool}` |
| `output` | `"pc"` / `"tv"` / `"both"` |

Görünürlük ayrı bir mesajla gelir: `{"t":"visible","v":bool}`.

Yapılacaklar:
- Bu değerleri `OverlayService` içinde son durum olarak sakla (thread-safe). Settings ekranı açılınca oradan oku.
- Değer değişince ekranı güncelle. Bir broadcast ya da basit bir listener kullanabilirsin.

**Bilgisayar bağlı değilse:** Ekranın üstünde "Bilgisayar bağlı değil — ayarlar uygulanamaz" yaz.

## Görev 2 — Küçük bağlantı göstergesi

**Bağlantı kopunca:** Bilgisayar bağlantısı 10 saniyeden uzun süre koparsa, katmanın sağ üst köşesinde küçük bir gösterge çıksın. Gösterge 5 saniye kalsın.
- **İçerik:** kırmızı nokta ve "TRÇeviri: bilgisayar bağlı değil" yazısı.
- **Boyut:** ekran yüksekliğinin ~%2'si, yarı saydam.
- **Tekrar:** 2 dakikada bir en fazla bir kez görünsün; ekranı rahatsız etmesin.

**Yeniden bağlanınca:** Mevcut yeşil "TRÇeviri bağlandı" banner'ı yeterli.

**Kapatma seçeneği:** Ayarlar ekranına **"Bağlantı uyarısı: Açık / Kapalı"** satırı ekle.
- Bu ayar TV'de yerel olarak saklanır (`SharedPreferences`), bilgisayara gönderilmez.
- Varsayılan değeri **Açık**.

## Bittiğinde
Kısa bir özet ver:
- eklediğin/değiştirdiğin dosyalar,
- build numarası,
- `sendToPc` ile giden mesaj türleri.
