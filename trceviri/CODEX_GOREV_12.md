# Codex Görev 12 — "Dünyanın en iyi oyun çeviri uygulaması" turu

Görev 11 bitince ara vermeden buna geç. Önce `git pull`, sonra `GELISTIRME_NOTLARI.md` oku.
- Senin alanın: `app/`, `.github/workflows/`, `brand/`, kök `README.md`, `contrib/`, ve bu görevle yeni `site/` klasörü.
- `trceviri/` klasörüne dokunma (Claude).
- Her alt görev ayrı commit olsun; push öncesi her zaman `git pull --rebase`. Kullanıcı 8–10 saat yok, hiçbir şey sorma; karar gerekirse makul olanı seç ve notlara yaz.

## A. Ortak oyun arayüzü paketi (tüm oyunlar)

`contrib/ortak_ui.json` dosyasına **en az 1200** satır yaz. Biçim: `{"English": "Türkçe"}`.

PS5 oyunlarında en sık geçen arayüz metinlerini kapsa:
- Ana menü, ayarlar (grafik, ses, kontrol, erişilebilirlik, altyazı, dil)
- Zorluk seviyeleri, kaydet/yükle, onay pencereleri ("Are you sure you want to quit?")
- Yükleme ipuçları kalıpları, envanter/zanaat/yetenek ağacı, harita efsanesi
- Görev günlüğü, ödüller/kupalar, mağaza, çok oyunculu lobi
- Kontrol ipuçları ("Press X to ...", "Hold R2 to ...", "Tap", "Mash")
- Durum mesajları ("Checkpoint reached", "Autosaving", "Mission Failed", "You Died")

Kurallar:
- Türk oyuncuların gerçekten kullandığı terimleri kullan.
- TAMAMI BÜYÜK HARF olan satır büyük harf kalsın.
- Tırnak ve emoji kullanma; Türkçe ek kesme işareti (X'e) serbest.
- Aynı anahtarı iki kez yazma.

Claude bunu `profiles/packs/ortak.json` olarak bütün profillerin ortak yedek paketi yapacak.

## B. Popüler oyun paketleri

`contrib/packs/<id>.json` dosyalarına her biri için **150+** satırlık oyun özel arayüz/görev/kontrol metni yaz:
- `gow_ragnarok`
- `tlou2`
- `ghost_tsushima`
- `horizon_fw`
- `re4`
- `hogwarts`
- `ea_fc`
- `cod`
- `ff7_rebirth`
- `uncharted`

Kurallar:
- Profil dosyaları `trceviri/profiles/*.json` içinde; isim/terim sözlüklerine uy.
- Karakter adları çevrilmez.
- Emin olmadığın metni uydurma. Gerçek oyunda geçtiğinden emin olduğun genel görev/kontrol kalıplarını yaz.

## C. Tanıtım ve indirme sitesi (GitHub Pages)

`site/` klasörüne tek sayfalık, Türkçe, statik bir site yap (HTML+CSS, framework yok). Tasarım uygulamayla aynı: koyu zemin `#0B0F14`, vurgu `#3DE6A0`, logo `brand/`'dan.

Bölümler:
1. Başlık + iki büyük düğme:
   - "Bilgisayar için indir": en son `pc-latest` sürümündeki `TRCeviri-Kurulum.exe`
   - "TV uygulaması": `latest` sürümündeki `a.apk`
2. Nasıl çalışır (3 adım + `brand/store` görselleri)
3. Desteklenen oyunlar: profil listesi; Genel oyun + Film/dizi + 21 oyun
4. Film/dizi modu ve .srt çevirici
5. SSS / sorun giderme (README'deki tablo)
6. Gizlilik: "Çeviri varsayılan olarak bilgisayarınızda yapılır; Gemini anahtarı girerseniz metin Google'a gider"

Yayın:
- `.github/workflows/pages.yml` ile `site/` klasörünü GitHub Pages'e yayınla (actions/deploy-pages).
- Pages repo ayarından açılmamışsa workflow başarısız olabilir. Notlara "kullanıcı Settings → Pages → Source: GitHub Actions seçmeli" yaz.
- README'ye site linkini ekle: `https://batuhankartalbc-sd.github.io/trtv/`.

## D. TV çizim performansı

- OverlayView: her `items` mesajında sadece değişen kutuları yeniden ölç/çiz. Metin düzenini (StaticLayout) önbelleğe al.
- Hedef: 1080p'de bir kare en fazla 8 ms. Debug build'de çizim süresini Tanılama ekranında göster.
- Yeni gelen çeviriye 80 ms'lik yumuşak belirme (alpha) ekle. Kalkışta animasyon yok; altyazı kalkınca anında silinsin.

## E. Notlar

Her bitirilen alt görev için `GELISTIRME_NOTLARI.md` günlüğüne kısa kayıt düş: dosyalar, satır sayıları, build numarası, yarım kalanlar.
