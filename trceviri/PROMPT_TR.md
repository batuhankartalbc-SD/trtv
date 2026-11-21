# TRÇeviri — Oyun İçi Anlık İngilizce→Türkçe Ekran Çevirmeni (Windows) — Geliştirme Promptu

Sen kıdemli bir full‑stack / masaüstü yazılım mühendisisin. Aşağıda tarif edilen uygulamayı **eksiksiz, çalışır, üretim kalitesinde** yazmanı istiyorum. "Örnek kod", "TODO", "buraya kendi kodunu ekle" kabul edilmez. Her dosyayı tam olarak yaz. Kararsız kaldığın yerde bu belgedeki varsayılanları uygula, bana soru sorma.

---

## 1. Amaç

PS5 oyunları (öncelik: **Grand Theft Auto VI**) bilgisayarda **PS Remote Play** ya da **chiaki‑ng** penceresinde oynanıyor. Uygulama bu pencereyi canlı olarak okuyacak, kullanıcının işaretlediği bölgelerdeki **İngilizce yazıları** (diyalog altyazıları, konuşan kişinin adı, görev hedefi yazıları, oyun içi telefon/mesaj ekranı, yardım/ipucu kutuları, menüler) **OCR ile okuyacak**, **Türkçeye çevirecek** ve İngilizce yazının **tam üstünü kapatan** bir kutuda Türkçesini **anlık** gösterecek.

- Oyuna hiçbir şekilde müdahale yok: bellek okuma, DLL enjeksiyonu, hook yok. Sadece ekran görüntüsü.
- Kullanıcı arayüzü tamamen **Türkçe**.
- Uygulama bilgisayarda çalışır. Kullanıcı oyunu bilgisayar ekranında (ya da bilgisayarı HDMI ile bağladığı TV'de) Remote Play penceresinde izler.

## 2. Teknoloji yığını (zorunlu)

- **Python 3.12**, Windows 10 2004+ / Windows 11, x64.
- Arayüz: **PySide6** (Qt 6).
- Ekran yakalama: **mss** (GDI) ile pencere istemci alanı. Overlay penceresi `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE=0x11)` ile **yakalamadan hariç** tutulur. Böylece kendi çevirimizi tekrar okumayız. Pencere konumu/boyutu `pywin32` / `ctypes` ile `GetClientRect` + `ClientToScreen`, DPI farkındalığı `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)`.
- OCR: **RapidOCR** (`rapidocr-onnxruntime`, PP‑OCR modelleri, CPU). Varsa `onnxruntime-directml` ile GPU (DirectML) kullanımı ayarlardan açılabilir. Ön işleme **OpenCV** + **numpy**.
- Benzerlik/eşleştirme: **rapidfuzz**.
- Çeviri: `httpx` ile REST. Motorlar:
  1. **Google Gemini** (varsayılan; model ayarlanabilir, varsayılan `gemini-3.5-flash-lite`),
  2. **OpenAI**,
  3. **Anthropic Claude**,
  4. **DeepL**,
  5. **Ücretsiz MyMemory API** (`api.mymemory.translated.net/get?langpair=en|tr`): anahtar yoksa ya da ana motor hata verirse yedek. Günlük kotalıdır; 429 ya da kota hatasında bekleme süresi uygula. `translate.googleapis.com` gayriresmî uç noktasını kullanma, Python isteklerini 429 ile engelliyor.
- Önbellek: **SQLite** (`sqlite3`).
- API anahtarları Windows **DPAPI** (`win32crypt.CryptProtectData`) ile şifreli saklanır. Asla log'a yazılmaz.
- Paketleme: `run.bat`: venv oluşturur, `requirements.txt` kurar, başlatır. `build.bat`: **PyInstaller** ile tek klasör exe.
- Testler: **pytest**.

## 3. Klasör yapısı

```
trceviri/
  run.bat, build.bat, requirements.txt, README.md
  trceviri/
    __main__.py          # giriş noktası
    app.py               # QApplication, servislerin kurulumu, yaşam döngüsü
    config.py            # dataclass ayarlar, JSON kaydet/yükle, profil yönetimi
    secrets.py           # DPAPI ile anahtar saklama
    winutil.py           # pencere bulma, istemci dikdörtgeni, DPI, capture‑exclude, click‑through
    capture.py           # yakalama iş parçacığı (hedef FPS, kare zaman damgası)
    zones.py             # bölge modeli (normalize koordinat), türler, varsayılan profiller
    ocr.py               # RapidOCR sarmalayıcı, ön işleme, satır birleştirme
    detect.py            # değişim algılama, kararlılık, boş bölge algılama
    textproc.py          # normalizasyon, konuşmacı ayırma, HUD/gürültü filtreleri
    translate/
      base.py            # Translator arayüzü, hata türleri
      gemini.py, openai_.py, claude.py, deepl.py, free.py
      manager.py         # öncelik kuyruğu, toplu gönderim, yedek motor, bağlam, sözlük
    cache.py             # SQLite çeviri önbelleği
    pipeline.py          # yakala→algıla→OCR→çevir→göster orkestrasyonu
    overlay.py           # şeffaf, tıklama geçirgen, her zaman üstte overlay
    ui/
      main_window.py     # kontrol paneli
      zone_editor.py     # dondurulmuş kare üstünde bölge çizme
      glossary_editor.py
      widgets.py
    hotkeys.py           # RegisterHotKey ile genel kısayollar
    log.py               # dönen dosya log + panelde canlı log
  profiles/gta6.json     # hazır GTA 6 profili
  tests/ ...
```

## 4. Bölgeler (Zones)

Her bölge: `id`, `ad`, `tür`, `x,y,w,h` (**Remote Play istemci alanına göre 0–1 normalize**), `aktif`, `kararlılık_ms`, `min_güven`, `kapatma_stili`, `yazı_boyutu_ölçeği`, `hizalama`.

Türler ve davranışları:

| Tür | Örnek (GTA 6) | Davranış |
|---|---|---|
| `subtitle` | Alt ortadaki diyalog: `Lucia: Where are you?` | En yüksek öncelik. `Ad: metin` biçimini ayır, adı çevirme, renkli göster. Kararlılık 120 ms. Yazı kaybolunca 250 ms içinde overlay'i kaldır. Uzayan satırda (yazı yazılarak beliriyorsa) önceki çevirinin üzerine güncelle. |
| `objective` | Ekran altındaki sarı/beyaz görev yazısı `Go to the safehouse.` | Kararlılık 250 ms, satır değişene kadar ekranda kalır. |
| `phone` | Oyun içi telefon: kişiler, mesajlar, uygulama adları | Çok satırlı. Her OCR satırını ayrı kutu olarak kapat. Kısa UI kelimelerini (`Contacts`, `Messages`) sözlükten çevir. |
| `help` | Sol üst ipucu kutusu `Press ⓧ to...` | Buton simgelerini koru (OCR'da simge yerine çıkan tek harfleri `[X]` gibi işaretle). |
| `menu` | Duraklatma menüsü, ayarlar | İsteğe bağlı, varsayılan kapalı. |
| `free` | Kullanıcının çizdiği herhangi bir alan | Genel davranış. |

`profiles/gta6.json` hazır gelsin (16:9 için):
- subtitle: x 0.12, y 0.80, w 0.76, h 0.15
- objective: x 0.15, y 0.70, w 0.70, h 0.08 (varsayılan kapalı; kullanıcı açar)
- help: x 0.01, y 0.02, w 0.30, h 0.20
- phone: x 0.66, y 0.30, w 0.20, h 0.55 (varsayılan kapalı)

Profil sistemi: birden çok oyun profili, panelden seçilir, kopyalanır, içe/dışa aktarılır.

## 5. İşlem hattı (pipeline): anlık olması için ayrıntılar

1. **Yakalama iş parçacığı**: hedef pencerenin istemci alanını 20 FPS (ayarlanabilir 5–30) yakalar. Pencere küçültülmüşse ya da kapandıysa bekler ve tekrar bulur. Pencere seçimi: başlıkta `PS Remote Play` / `chiaki` geçenler otomatik önerilir, listeden elle seçilebilir.
2. **Değişim algılama** (bölge başına): bölgeyi 1/4 ölçeğe indir → gri → bulanıklaştır → önceki kareyle ortalama mutlak fark. Eşik altındaysa OCR yapma. Ayrıca kenar yoğunluğu (Canny) ile "bölge boş mu?" kontrolü: yazı yoksa ve overlay görünüyorsa kaldır.
3. **OCR iş havuzu** (en fazla 2 eşzamanlı, subtitle önceliği): ön işleme: 2× büyütme (INTER_CUBIC), CLAHE, gerekirse ters çevirme (açık zemin/koyu yazı tespiti). RapidOCR sonuçlarını y'ye göre satırlara grupla, güveni `min_güven` altında olan kutuları at. Her satır için **piksel kutusu** sakla (overlay kapatması bunun için gerekli).
4. **Metin işleme**: Unicode normalize, fazla boşluk, OCR hataları (`|`→`I`, `0`/`O` bağlamsal, `rn`→`m` gibi küçük düzeltmeler), konuşmacı ayırma `^([A-Z][\w .'-]{0,24}):\s*(.+)$`. Gürültü filtresi: <2 harf, sadece sayı/simge, HUD sabitleri (para `$1,234`, mesafe `120 m`, saat). Kullanıcı tanımlı "çevirme" listesi.
5. **Kararlılık**: aynı bölgede ardışık iki OCR sonucu `rapidfuzz.ratio ≥ 90` ise ya da `kararlılık_ms` geçtiyse metni "kararlı" say. Önceki kararlı metinle ≥ 92 benzerse yeni çeviri isteme (OCR titremesi).
6. **Önbellek**: anahtar = `(oyun_profili, normalize_metin, hedef_dil, motor)`. İsabet varsa **0 gecikme** ile göster. Bulanık arama: önbellekte ≥ 95 benzerlikteki girişi kullan.
7. **Çeviri yöneticisi**:
   - Öncelik kuyruğu: subtitle > objective > help/phone > menu.
   - 40 ms toplu gönderim penceresi: aynı anda gelen birden çok satırı tek istekte JSON dizi olarak çevir.
   - LLM motorlarında sistem talimatı: "Video oyunu altyazısı çevirmenisin. Doğal, kısa, konuşma dili Türkçe. Argo ve küfrü yumuşatmadan karşılığıyla çevir. Özel isimleri, marka ve yer adlarını çevirme. Sadece JSON dizi döndür." + oyun adı + **son 6 diyalog satırı bağlam olarak** + **sözlük** (kullanıcı düzenler; GTA 6 için hazır: `Vice City`, `Leonida`, `Jason`, `Lucia` çevrilmez; `cops`→`polisler`, `heat`→`aranma seviyesi` vb.).
   - Zaman aşımı 2.5 s. Hata ya da zaman aşımında **ücretsiz MyMemory** yedeğine düş, başarısızsa İngilizceyi değiştirmeden bırak (overlay gösterme).
   - Akış (streaming) destekleyen motorlarda ilk tam cümleyi hemen göster.
   - Yanıt kısaltılmış/eksikse tek satır tekrar dene.
8. **Gösterim**: sonuç geldiğinde bölgedeki metin hâlâ aynı mı diye kontrol et (geç gelen çeviriyi eski satıra basma). Aynıysa overlay'e gönder.

Gecikme hedefleri: önbellekte varsa yazının ekrana gelmesinden itibaren **≤ 150 ms**; yeni satırda (Gemini flash‑lite) **≤ 900 ms**. Panelde son 50 satırın ortalama OCR, çeviri ve toplam süreleri gösterilsin.

## 6. Overlay

- Çerçevesiz, `Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint`, `WA_TranslucentBackground`, `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE` (tıklama geçirgen, odak çalmaz), `WDA_EXCLUDEFROMCAPTURE`.
- Remote Play penceresinin istemci alanını **sürekli takip eder** (taşıma, yeniden boyutlandırma, tam ekran, farklı DPI'lı monitör). Remote Play penceresi öne değilse/küçültülmüşse gizlenir.
- Her çevrilmiş satır için: OCR piksel kutusunun **birleşimini 6 px genişlet**, arka planı **opak** boya. Renk: kutunun dış kenarından örneklenen ortalama renk ya da ayardan sabit (varsayılan `#101010`, opaklık %92). Böylece İngilizce tamamen kapanır.
- Türkçe metni kutuya **otomatik sığdır**: yazı tipi `Segoe UI Semibold`. Satır sarmalı, gerekirse yazı boyutunu düşür (alt sınır), gerekirse kutuyu aşağı/yukarı büyüt. 2 px siyah dış çizgi. Konuşmacı adı sarı/renkli ve kalın.
- Girişte 80 ms opaklık geçişi, çıkışta anında kaldırma (titreme yok).
- Hata ayıklama modu (F7): bölge sınırlarını ve OCR kutularını renkli çerçeveyle çiz.

## 7. Kontrol paneli (Türkçe)

Sekmeler:
- **Ana**: pencere seçimi (otomatik bul + liste + yenile), Başlat/Durdur, durum ışıkları (Pencere ✓, OCR ✓, Çeviri ✓), canlı gecikme istatistikleri, son çeviriler listesi (İngilizce → Türkçe, kopyalanabilir).
- **Bölgeler**: "Kareyi dondur" ile anlık görüntü al, üstünde fareyle dikdörtgen çiz/taşı/boyutlandır/sil, tür ve ayarları sağ panelde düzenle, canlı önizleme (o bölgenin OCR sonucu). Profil kaydet/yükle/içe‑dışa aktar.
- **Çeviri**: motor seçimi, model, API anahtarı (maskeli, "Test et" düğmesi), yedek motor, bağlam satır sayısı, üslup (resmi/samimi), sözlük düzenleyici (tablo: İngilizce, Türkçe, "çevirme" işareti).
- **Görünüm**: yazı boyutu, renkler, opaklık, kapatma stili (opak kutu / yarı saydam / sadece altında göster), konuşmacı rengi.
- **Gelişmiş**: FPS, OCR iş sayısı, GPU (DirectML), değişim eşiği, kararlılık süreleri, log seviyesi, önbelleği temizle/dışa aktar.

Genel kısayollar (`RegisterHotKey`): **F8** overlay aç/kapa, **F9** duraklat/devam, **F10** bölge düzenleyiciyi aç, **F11** son satırı yeniden çevir (önbelleği atla), **F7** hata ayıklama çerçeveleri.

Ayarlar `%APPDATA%\TRCeviri\config.json`, profiller `%APPDATA%\TRCeviri\profiles\`, önbellek `cache.sqlite`, log `logs\trceviri.log` (5 MB × 3 dönen).

## 8. Sağlamlık

- Tüm iş parçacıkları kapanışta düzgün durur. Hiçbir istisna arayüzü çökertmez: global `sys.excepthook` + Qt mesaj işleyicisi log'a yazar ve panelde gösterir.
- Remote Play kopar/yeniden bağlanırsa otomatik toparlanır.
- İnternet yoksa önbellek + yerel davranış devam eder ve panelde uyarı gösterilir.
- 4K/1080p/720p ve %100–%200 ölçeklerde doğru konumlama.
- CPU kullanımı hedefi: 11. nesil i5'te ortalama < %25.

## 9. Testler (pytest)

- `textproc`: konuşmacı ayırma, gürültü filtresi, OCR düzeltmeleri.
- `detect`: değişim eşiği, kararlılık mantığı (sahte kare dizileri).
- `cache`: ekleme/bulma/bulanık eşleşme.
- `translate.manager`: sahte motorla öncelik, toplu gönderim, yedeğe düşme, geç gelen sonucun atılması.
- `ocr`: PIL ile üretilmiş "Lucia: Where are you going?" görselinde metnin doğru okunduğu entegrasyon testi.
- `overlay` yerleşim fonksiyonu: metnin kutuya sığdırılması (saf fonksiyon olarak).

## 10. Teslim

1. Tüm dosyaların tam içeriği.
2. `README.md` (Türkçe): kurulum (`run.bat`), Remote Play'i açma, pencere seçme, bölge çizme, API anahtarı alma (Gemini için Google AI Studio), sorun giderme (siyah kare → Remote Play donanım hızlandırması, OCR boş → bölge/çözünürlük, yazılar gelmiyor → oyunda altyazının açık olması gerektiği).
3. Kabul kriterleri, her biri gösterilmeli:
   - Remote Play penceresinde GTA 6 diyaloğu çıktığında ≤ 1 sn içinde İngilizce tamamen kapanır ve Türkçesi görünür.
   - Diyalog kalkınca Türkçe de ≤ 300 ms içinde kalkar.
   - Overlay kendi yazısını tekrar okumaz (sonsuz döngü yok).
   - Pencere taşınınca/yeniden boyutlandırılınca kutular doğru yerde kalır.
   - API anahtarı yokken ücretsiz MyMemory ile çalışır.
   - Aynı satır ikinci kez geldiğinde önbellekten anında gelir.

Kodu yazmaya başla. Önce kısa bir mimari özeti ver, sonra dosyaları sırayla, eksiksiz yaz.
