# Codex görevi 5 — Bilgisayar testleri CI'da, tanıtım sayfası, TV tanılama ekranı

## 0. Önce
- `git pull`, sonra **`GELISTIRME_NOTLARI.md`**'yi oku.
- `CODEX_GOREV_3` ve `CODEX_GOREV_4`'ten bitmeyen iş varsa **önce onları bitir.** Hangisinin bittiğini günlüğe yaz.
  - Görev 3: konuşma geçmişi, akıcı görünüm, JVM testleri.
  - Görev 4: `brand/` klasöründeki logo dosyaları.
- **Bilgin olsun:** Bilgisayar uygulaması **2.3.0** ile **"Brolis Game Translate"** adını ve senin logonu kullanmaya başladı (Claude). Kaynak: `trceviri/assets/logo.png`.
- **Alanın:** `app/`, `.github/workflows/`, `brand/` ve deponun kökündeki `README.md`.
- **Dokunma:** `trceviri/`. PC'de bir değişiklik gerekiyorsa `GELISTIRME_NOTLARI.md` günlüğüne istek olarak yaz.
- **Bitince:** `GELISTIRME_NOTLARI.md` → "Codex" bölümüne yaz: ne yaptın, dosyalar, build numarası.

## 1. Bilgisayar uygulamasının testleri CI'da
Yeni bir workflow yaz: **`.github/workflows/pc-tests.yml`**.

- **Ne zaman çalışır:** `trceviri/**` değiştiğinde `push` ve `pull_request`. Ayrıca elle çalıştırma (`workflow_dispatch`).
- **Nerede:** `runs-on: windows-latest`. Python 3.12.
- **Kurulum:** `pip install -r trceviri/requirements.txt`.
- **Çalıştırılacak:** `python -m pytest -q trceviri/tests`.
- **Çalışma klasörü:** Testler `trceviri/tests/conftest.py` sayesinde her klasörden çalışır.
- **Atlanacak test:** OCR testi `test_ocr_reads_subtitle` ilk çalıştırmada OCR modelini kullanır. CI'da yavaşsa ya da internet isterse sadece bu testi `-k "not ocr"` ile atlayabilirsin. Diğer testler mutlaka çalışsın.
- **Dokunma:** APK derleyen `build.yml` ve release adımları aynen kalsın.

## 2. Tanıtım sayfası: deponun kökündeki `README.md` (Türkçe)
Arkadaşların depoya girince ilk bunu görecek. Kısa ve anlaşılır olsun.

**İçerik:**
- **Başlık:** Logo (`brand/` ya da `trceviri/assets/logo.png`) + **Brolis Game Translate** + bir cümlelik açıklama: "PS5 oyunlarındaki İngilizce konuşma, menü ve kontrolleri anında Türkçeye çevirir; Türkçe yazı TV'de oyunun tam üstünde, aynı boyutta görünür."
- **İndir:**
  - Bilgisayar: `https://github.com/batuhankartalbc-SD/trtv/releases/download/pc-latest/TRCeviri-Kurulum.exe`
  - TV: `https://github.com/batuhankartalbc-SD/trtv/releases/download/latest/a.apk`
  - TV'ye Downloader ile nasıl kurulacağı: 3–4 adım.
- **Nasıl çalışır:** PS Remote Play → bilgisayar okur/çevirir → TV'de gösterilir. Basit bir şema; metin ya da Mermaid kullanabilirsin.
- **Gerekenler:**
  - Windows 10/11 bilgisayar,
  - PS5 + PS Remote Play,
  - aynı ağda Android TV / Google TV,
  - oyunda altyazılar açık.
- **Özellikler listesi:**
  - yerel anlık çeviri + Gemini,
  - GTA 6 paketi,
  - oyun profilleri,
  - TV'den kumandayla ayar ve hizalama,
  - seslendirme,
  - otomatik güncelleme.
- **Sık sorulan sorular:**
  - "Türkçe çıkmıyor" → oyunda altyazı açık mı?
  - "TV bulunamadı" → aynı ağ, TV uygulaması açık mı?
  - "Kayıyor" → hizalama.
- **Lisans notu:** Yerel çeviri modeli Helsinki-NLP opus-mt-tc-big-en-tr'dir, **CC-BY-4.0**. Kaynak bağlantısıyla belirt.
- **Mevcut `KURULUM.md`:** Eski Faz 0 belgesi. Silme; README'de "eski" diye bağlantı verme, sadece dokunma.

## 3. TV'de tanılama ekranı
Sorun olduğunda neyin bozuk olduğunu TV'den görebilmek için.

- **Yer:** `MainActivity`'ye **"Tanılama"** düğmesi ekle. Düğme `DiagnosticsActivity`'yi açar. Ekran yarı saydam ya da düz olabilir.
- **Gösterilecekler:**
  - bilgisayar bağlı mı ve bilgisayarın adı (`hello` mesajındaki `name`),
  - son mesajın kaç saniye önce geldiği,
  - son 10 saniyede gelen `items` mesajı sayısı,
  - ekranda kaç çeviri kutusu olduğu,
  - ekran çözünürlüğü ve `density`,
  - ekran üstü izni var mı,
  - uygulama sürümü (`versionName` / `versionCode`),
  - TV'nin IP adresi ve port,
  - hizalama değerleri (`dx`, `dy`, `sx`, `sy`).
- **Yenileme:** Ekran 1 saniyede bir yenilensin. **Geri** ile kapansın.
- **Uygulama:** Bu bilgileri `OverlayService` içinde thread-safe sayaçlarla tut. Protokolde değişiklik **yok**.

## Bitti kriteri
- `main`'e push et.
- `build.yml` ve `pc-tests.yml` ikisi de **başarılı** bitsin.
- `GELISTIRME_NOTLARI.md` günlüğünü güncelle.
