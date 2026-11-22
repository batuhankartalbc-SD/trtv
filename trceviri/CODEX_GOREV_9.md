# Codex Görev 9 — Brolis Game Translate

Önce `git pull`, sonra `GELISTIRME_NOTLARI.md` dosyasını oku. Senin alanın: `app/`, `.github/workflows/`, `brand/`, kök `README.md`, `contrib/`. `trceviri/` klasörüne dokunma (Claude'un alanı). Bitince notların "Günlük" bölümüne kısa kayıt ekle, commit + push.

PC 2.3.3 yayında: fontlar artık PC'de de çiziliyor (Nunito/Inter için `wght` ekseni ayarlanıyor). `style` mesajında yeni alanlar var:
- `pcver` (ör. "2.3.3")
- `refine`: `null` (Gemini kapalı) ya da Türkçe metin: "hazır", "çalışıyor", "kota doldu (10 dk ara)", "geçersiz istek/anahtar (5 dk ara)"
- `font`, `fonts` (zaten kullanıyorsun)

## 1. TV Ayarlar: durum satırı
- Ayarlar menüsünün en altına küçük gri bir satır: `PC 2.3.3 · TV 1.xx · Gemini: açık / beklemede / kapalı`.
- `refine` null ise "Gemini: kapalı" yaz, değilse metni olduğu gibi göster; "kota" ya da "geçersiz" içeriyorsa sarı renkte.
- PC sürümü TV'nin beklediğinden eskiyse (`pcver` < "2.3.0") sarı uyarı: "Bilgisayardaki uygulamayı güncelleyin".

## 2. TV: kumanda yardım ekranı
- Ayarlar'a "Kumanda tuşları" satırı: açılınca tek sayfalık liste (hizalama modu tuşları, büyüt/küçült, göster/gizle, son çeviriyi tekrar oku).
- Hizalama modu ilk kez açıldığında ekranın üstünde 5 sn kısa ipucu şeridi göster (kodda tanımlı gerçek tuşları yaz, ör. "Yön tuşları: kaydır · ... · Geri: bitir"), bir kez gösterildikten sonra kaydet ve tekrar gösterme.

## 3. CI: PC testleri
- `.github/workflows/pc-tests.yml`: `windows-latest`, Python 3.11, `pip install -r trceviri/requirements.txt pytest`, `pytest trceviri/tests -q`.
- Sadece `trceviri/**` değişince çalışsın. Ağır paketler (onnxruntime-directml, ctranslate2) kurulmazsa testler zaten atlıyor; kurulum çok uzun sürerse bunları atlayan `requirements-ci.txt` öner ama `trceviri/` içine yazma — notlara yaz, ben eklerim.

## 4. contrib: GTA 6 çeviri paketi büyütme
- `contrib/gta6_extra.json` dosyasına 100+ yeni satır: görev hedefleri ("Get in the car.", "Lose the cops.", "Go to ..."), telefon/menü metinleri, kontrol ipuçları ("Press X to ...").
- Biçim: `{"İngilizce": "Türkçe"}`. Kısa, doğal, oyun dili. Özel karakter yok (tırnak, emoji). Büyük harf satırları büyük harf kalsın.
- Ben iyi olanları `profiles/packs/gta6.json` içine alacağım.

## 5. README: arkadaşlar için "İlk 5 dakika"
- Kök README'ye en üste kısa bölüm: 1) PC kurulum exe linki (`pc-latest`), 2) TV APK linki (`latest`), 3) aynı Wi-Fi, 4) Kurulum sihirbazını sonuna kadar izle, 5) F6 son çeviriler, F9 göster/gizle.
- Sorun giderme tablosu: "TV bulunamadı", "Türkçe gelmiyor", "Yazılar kayıyor" → çözüm.

Bitince bana (Claude'a) notlardan haber ver: hangi dosyalar değişti, TV build numarası.
