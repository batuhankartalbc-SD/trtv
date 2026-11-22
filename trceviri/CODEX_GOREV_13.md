# CODEX GÖREV 13 – TV'de gerçek cihaz testinden çıkan hatalar (Build 75 / 1.75)

Claude, 2026-11-22'de Beko Google TV'de (192.168.1.103) Build 75'i kurup uçtan uca test etti.
PC↔TV bağlantısı, sihirbaz 1–3, Ayarlar ve PC ayar eşitlemesi çalışıyor. Aşağıdakiler bozuk; öncelik sırasıyla.
Ekran görüntüleri Claude'da; gerekirse kullanıcıdan iste.

## 1. KRİTİK – Film/bağımsız mod hiç çeviri göstermiyor (IndependentModeService.onImage)
Belirti: YouTube'da İngilizce altyazı ekranda (alt bantta, net), film modu açık, 1 dakikadan uzun bekleme →
Türkçe katman yok, ana ekranda "Bağımsız mod · OCR 0 ms". Uygulama pid'inden 25 sn boyunca tek satır log yok
(ne OCR hatası ne kare hatası). Yani `recognizer.process` hiç tamamlanmıyor/çağrılmıyor.

Muhtemel kök neden: `onImage` iki dalda (`awaitingCleanFrame` başlatılırken ve `now < cleanFrameAfter`) ve
`now - lastFrameAt < interval` dalında **görüntüyü acquire etmeden return ediyor**. ImageReader `maxImages = 2`;
alınmayan kareler kuyruğu doldurunca sanal ekran yeni kare üretemez, dinleyici bir daha çağrılmaz →
servis `awaitingCleanFrame = true` ve `suppressOverlayUi(true)` durumunda sonsuza kadar takılır
(PC'den gelen çeviriler de gizli kalır).

İstenen:
- Her `onImage` çağrısında `source.acquireLatestImage()` al; işlenmeyecekse hemen `close()` et. Hiçbir dal
  kareyi kuyrukta bırakmasın.
- `suppressOverlayUi(true)` sonrası bir zaman aşımı ile (ör. 300 ms) mutlaka `false`'a dönülsün; kare gelmese bile.
- Teşhis için `Log.i`: ilk kare geldi, her 50 karede bir sayaç, OCR satır sayısı + süre. Tanılama ekranına
  "Film: alınan kare / OCR çalışması / son OCR ms / son satır" ekle (bu TV'de logcat saniyede binlerce satırla doluyor).
- Doğrulama: YouTube TED videosu `iG9CE55wbtY`, altyazı İngilizce → 5 sn içinde Türkçe alt bant görünmeli.

## 2. Sihirbaz son adım kumandayla bitmiyor (OnboardingActivity.dispatchKeyEvent)
Adım 4/4'te OK/ENTER `nextStep()` çağırıyor; `step < 3` olmadığı için hiçbir şey olmuyor ve kullanıcı takılıyor
(`complete()` yalnızca dokunmatik tıklamada çalışıyor). Düzeltme: `if (step == 3) complete() else nextStep()`.
DPAD_RIGHT için de aynı.

## 3. Ana ekran düğme yazıları yarıdan kesik (MainActivity.buttonParams)
`LayoutParams(MATCH_PARENT, 68)` sabit 68 px; 21sp yazı + Button varsayılan iç boşluğu sığmıyor
("Kumandayla hizala", "Ayarlar"… alt yarısı görünmüyor). WRAP_CONTENT + `minimumHeight` (~72dp) ve
`setPadding(… , 14, … , 14)` kullan. 1920x1080 TV'de ekran görüntüsüyle doğrula.

## 4. Eski ad
Ana ekran bilgi kartı: "Bilgisayarda TRÇeviri'yi açın" → "Bilgisayarda Brolis Game Translate'i açın".
Tüm `app/` içinde "TRÇeviri" metnini tara.

## 5. Ayarlar – film modu satırı
Satırda ‹ PC'den (PS5) › okları var ama sol/sağ hiçbir şey yapmıyor; yalnızca OK açıyor. Sol/sağ da `activate("film_mode")`
çağırsın ya da okları kaldırıp "OK ile aç" yaz.

## 6. Ayarlar – "Örnek Türkçe yazı" ve örnek cümle
"Polisler sahil yolunu kapatmış." örnek satırı "Yazı tipi" ile "Türkçe yazılar" satırlarının arasına düşüyor;
önizleme kartının içine taşı (kopuk duruyor).

## PC tarafı (Claude yaptı, bilgi için)
- PC artık `engines` listesine Gemini'yi yalnızca anahtar varsa koyuyor; anahtarsız Gemini seçimi PC'de yok sayılıyor
  ve `style` yeniden gönderiliyor. TV, `engines` listesinde olmayan değeri göstermemeli.

Bitince GELISTIRME_NOTLARI.md'ye ekle; Claude yeni APK'yı TV'ye kurup 1. maddeyi YouTube + Netflix ile tekrar test edecek.
