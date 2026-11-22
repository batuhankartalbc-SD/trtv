# Codex görevi 8 — TV'de ilk kurulum rehberi + Tanılama'ya PC bilgisi + GTA 6 çeviri paketi önerileri

## 0. Önce
- `git pull`, `GELISTIRME_NOTLARI.md`'yi oku.
- **Görev 7 bitmediyse önce onu bitir:** `brand/fonts/{condensed,rounded,clean}.ttf` + OFL lisansları + TV'de "Yazı tipi" satırı.
  - Bilgisayar tarafı **hazır** (geliştirme ortamında). Fontlar `brand/fonts/` içine gelince Claude yayınlayacak.
  - **Dosya adları tam olarak `condensed.ttf`, `rounded.ttf`, `clean.ttf` olmalı.**
- **Alanın:** `app/`, `brand/`, `.github/workflows/`, kök `README.md` ve yeni **`contrib/`** klasörü.
- **Dokunma:** `trceviri/`.
- **Bitince:** Günlüğe yaz.

## 1. TV'de ilk kurulum rehberi
Arkadaşlar TV uygulamasını ilk kez açtığında ne yapacağını bilsin.

**Ne zaman:** `MainActivity` ilk açılışta, yani `SharedPreferences`'ta `onboarding_done` yoksa, **3–4 adımlık** bir tanıtım göstersin. Tam ekran, koyu tema, büyük yazı. D-pad sağ/OK ile ilerlesin, Geri ile geri gitsin.

**Adımlar:**
1. **"Brolis Game Translate'e hoş geldin"**: Logo + bir cümle: "Bilgisayardaki uygulamanın çevirilerini oyunun üstünde gösterir."
2. **Ekran üstü izni:**
   - İzin **varsa** ✓ göster ve geç.
   - **Yoksa** "İzin ver" düğmesi olsun; `Settings.ACTION_MANAGE_OVERLAY_PERMISSION` açsın. Geri dönünce izni tekrar kontrol et.
3. **Bilgisayar bağlantısı:**
   - "Bilgisayarda Brolis Game Translate'i aç; TV'yi kendisi bulur."
   - Canlı durum: "Bekleniyor…" ya da "✓ Bağlandı: <bilgisayar adı>".
   - TV'nin IP adresini de göster.
4. **Hazır:** "Oyuna dön"e basınca PS5 girişine dönülsün. `onboarding_done` kaydedilsin.

**Tekrar açma:** Ana ekranda **"Rehberi tekrar göster"** düğmesi olsun.

## 2. Tanılama ekranına bilgisayar bilgisi
Bilgisayar `style` mesajında artık şu alanları da gönderiyor:
- `pcver`: bilgisayar uygulamasının sürümü, örneğin `"2.3.3"`.
- `refine`: Gemini iyileştirmesinin durumu. Örnek değerler: `"hazır"`, `"çalışıyor"`, `"kota doldu (10 dk ara)"`. İyileştirme kapalıysa `null`.
- `font`, `fonts`: seçili yazı tipi ve kullanılabilir yazı tipleri (görev 7).

Tanılama ekranına şu satırları ekle:
- "Bilgisayar sürümü"
- "Gemini durumu"
- "Çeviri motoru" (`engine`)
- "Oyun profili" (`profile`)

Alan yoksa "—" yaz. Eski PC sürümleriyle uyumlu kalmalı.

## 3. GTA 6 çeviri paketi önerileri (`contrib/gta6_extra.json`)
Bilgisayar uygulaması, sık görülen oyun yazılarının hazır Türkçesini bir paketten alıyor (`trceviri/profiles/packs/gta6.json`, ~145 satır). Senden **öneri** istiyoruz. Asıl dosyaya **dokunma**; Claude önerileri inceleyip birleştirecek.

- **Biçim:** `{"İngilizce": "Türkçe", ...}`. Sadece JSON, UTF-8.
- **Kapsam:** **200–300 satır.** GTA serisinde ve açık dünya suç oyunlarında sık görülen kısa yazılar:
  - menü ve ayar seçenekleri,
  - tuş ipuçları ("Press X to …", "Hold L2 to …"),
  - görev hedefleri ("Go to …", "Lose the cops.", "Get to the car."),
  - telefon ve uygulama arayüzü,
  - durum mesajları ("Mission Passed", "Wasted", "Checkpoint reached"),
  - mağaza, araç, silah ve envanter terimleri.
- **Çeviri tarzı:** Doğal, kısa, oyun Türkçesi. Örnek: "Lose the cops." → "Polisleri ek." Resmî ve uzun olmasın. Tuş adları aynı kalsın: X, O, L2, R1, Kare, Üçgen, Daire, Options, Dokunmatik yüzey.
- **Yasaklar:**
  - Oyundan **birebir alıntı yapılmış uzun diyaloglar** ekleme; telif nedeniyle sadece kısa arayüz ve kontrol metinleri.
  - Mevcut `gta6.json`'daki satırları tekrar etme.
- **Doğrulama:** `contrib/README.md`'ye kısa bir not yaz: kaç satır, hangi kategoriler. Dosyanın geçerli bir JSON olduğunu doğrula. İstersen Python ya da jq ile kontrol eden küçük bir CI adımı ekleyebilirsin.

## Bitti kriteri
- `main`'e push et; `build.yml` ve `pc-tests.yml` başarılı bitsin.
- Günlüğe yaz: dosyalar, build numarası, satır sayısı.
