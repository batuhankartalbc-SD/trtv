"""Film/dizi modu, altyazı dosyası çevirisi ve genel profiller."""
import json
from pathlib import Path

from trceviri import srt
from trceviri.config import Profile
from trceviri.ocr import Line
from trceviri.pipeline import build_blocks, film_clean
from trceviri.translate import system_prompt

W, H = 1920, 1080
PROFILES = Path(__file__).resolve().parent.parent / "profiles"


def L(text, x0, y0, x1, y1, score=0.95):
    return Line(text, (x0, y0, x1, y1), score)


def test_film_mode_reads_only_bottom_subtitles():
    lines = [
        L("Episode 3: The Long Night", 700, 80, 1220, 130),        # üstteki başlık / oynatıcı yazısı
        L("Where are you going?", 820, 900, 1100, 950),             # kısa altyazı (oyun modunda 'other' olurdu)
        L("♪ Dancing in the moonlight ♪", 700, 960, 1220, 1010),  # şarkı sözü
    ]
    items = build_blocks(lines, W, H, [], True, {"subtitle"}, None, film=True)
    assert [i.src for i in items] == ["Where are you going?"]
    assert items[0].kind == "subtitle"


def test_film_clean_keeps_dialogue_dash_and_strips_tags():
    assert film_clean("<i>-Hey, wait.</i>") == "- Hey, wait."
    assert film_clean("[door creaks]") == "[door creaks]"


def test_profile_kind_roundtrip_and_bundled_profiles():
    p = Profile.from_dict({"name": "Film / dizi", "kind": "film"})
    assert p.is_film
    assert not Profile.from_dict({"name": "X", "kind": "bogus"}).is_film
    names = {json.loads(f.read_text(encoding="utf-8"))["name"] for f in PROFILES.glob("*.json")}
    assert {"Genel oyun (her oyun)", "Film / dizi", "GTA 6", "God of War Ragnarök"} <= names
    for f in PROFILES.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d.get("kind", "game") in ("game", "film"), f.name


def test_film_prompt():
    s = system_prompt("Breaking Bad", {}, "samimi", "", "film")
    assert "subtitle" in s and "Title: Breaking Bad" in s and "video game" not in s


SRT = """1
00:00:01,000 --> 00:00:03,500
<i>Where are you going?</i>

2
00:00:04,000 --> 00:00:06,000
- Home.
- Now?

3
00:00:07,000 --> 00:00:09,000
♪ la la la ♪
"""


def test_srt_parse_translate_write(tmp_path):
    cues = srt.parse(SRT)
    assert len(cues) == 3 and cues[0].start == "00:00:01,000"
    seen = []

    def fake(lines, ctx):
        seen.append(list(lines))
        return [{"Where are you going?": "Nereye gidiyorsun?", "- Home. - Now?": "- Eve. - Şimdi mi?"}[l] for l in lines]

    out = srt.translate_cues(cues, fake)
    assert seen == [["Where are you going?", "- Home. - Now?"]]   # şarkı satırı gönderilmez
    assert out[0].text == "<i>Nereye gidiyorsun?</i>"
    assert out[1].text == "- Eve.\n- Şimdi mi?"
    assert out[2].text == "♪ la la la ♪"
    f = tmp_path / "film.en.srt"
    f.write_text(SRT, encoding="utf-8")
    res, n = srt.translate_file(f, fake)
    assert res.name == "film.tr.srt" and n == 3
    assert "00:00:04,000 --> 00:00:06,000" in res.read_text(encoding="utf-8-sig")


def test_game_detector_suggests_profile():
    from trceviri.gamedetect import GameDetector
    profs = [load_from(f) for f in PROFILES.glob("*.json")]
    det = GameDetector(profs)
    for t in ["Kratos: Stay close, boy.", "Atreus, wait!", "Mimir: Brother, look there.", "Press R1 to attack"]:
        det.feed(t)
    assert det.suggest("GTA 6")[0] == "God of War Ragnarök"
    assert det.suggest("God of War Ragnarök") is None
    det2 = GameDetector(profs)
    det2.feed("Kratos")                       # tek terim yetmez
    assert det2.suggest("GTA 6") is None


def test_common_pack_and_uppercase():
    from trceviri.cache import TranslationCache
    from trceviri.config import Settings
    from trceviri.pipeline import Pipeline
    import tempfile
    p = Pipeline(Settings(), load_from(PROFILES / "gta6.json"), TranslationCache(Path(tempfile.mkdtemp()) / "c.db"))
    p.load_pack()
    assert p.lookup("Any unsaved progress will be lost.") == "Kaydedilmemiş ilerleme kaybolacak."   # ortak paket
    assert p.lookup("Quit to Main Menu") == "Ana Menüye Dön"            # oyun paketi ortak paketten önce gelir
    assert p.lookup("INVENTORY FULL") == "ENVANTER DOLU"                # büyük harf eşleşmesi
    film = Pipeline(Settings(), Profile.from_dict({"name": "Film / dizi", "kind": "film"}),
                    TranslationCache(Path(tempfile.mkdtemp()) / "c.db"))
    film.load_pack()
    assert film.lookup("Quit to Main Menu") is None                     # film modunda oyun paketi yok


def test_line_memo_distinguishes_different_subtitles():
    """Regresyon: aynı yerde benzer uzunlukta iki farklı altyazı eski metni döndürmemeli."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from trceviri.ocr import FullScreenReader
    font = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 40) if Path("C:/Windows/Fonts/georgia.ttf").exists() \
        else ImageFont.load_default()

    def crop(text, noise=0):
        im = Image.new("RGB", (1300, 60), (40, 60, 80))
        ImageDraw.Draw(im).text((650, 30), text, font=font, fill=(255, 255, 255), anchor="mm")
        a = np.array(im).astype(np.int16)
        if noise:
            a = a + np.random.default_rng(1).integers(-noise, noise + 1, a.shape)
        return np.clip(a, 0, 255).astype(np.uint8)

    a = FullScreenReader._sig(crop("The bridge is out. We have to find another way across."))
    b = FullScreenReader._sig(crop("Follow the river until you reach the old mill to rest."))
    a2 = FullScreenReader._sig(crop("The bridge is out. We have to find another way across.", noise=6))
    assert not FullScreenReader._same(a, b)
    assert FullScreenReader._same(a, a2)


def test_capture_loop_restarts_after_crash(monkeypatch):
    import tempfile
    import trceviri.pipeline as pl
    from trceviri.cache import TranslationCache
    from trceviri.config import Settings
    p = pl.Pipeline(Settings(), Profile(), TranslationCache(Path(tempfile.mkdtemp()) / "c.db"))
    calls = []

    def loop():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("çökme")
    monkeypatch.setattr(p, "_loop", loop)
    monkeypatch.setattr(pl.time, "sleep", lambda s: None)
    p.running.set()
    p._supervise()
    assert len(calls) == 3                      # iki çökmeden sonra yeniden başladı ve normal bitti


def test_user_correction_wins_and_persists(monkeypatch, tmp_path):
    import trceviri.config as cfg
    from trceviri.cache import TranslationCache
    from trceviri.config import Settings
    from trceviri.pipeline import Pipeline
    monkeypatch.setattr(cfg, "PROFILE_DIR", tmp_path)
    prof = load_from(PROFILES / "gta6.json")
    p = Pipeline(Settings(), prof, TranslationCache(tmp_path / "c.db"))
    p.load_pack()
    p.save_correction("Lose the cops.", "Aynasızları ekip at.")
    assert p.lookup("Lose the cops.") == "Aynasızları ekip at."
    p2 = Pipeline(Settings(), prof, TranslationCache(tmp_path / "c2.db"))
    p2.load_pack()                                     # yeniden açılışta da geçerli
    assert p2.lookup("LOSE THE COPS.") == "AYNASIZLARI EKİP AT."


def test_control_hint_templates():
    from trceviri import controls as c
    assert c.parse("Press X to open the door") == ("press", "x", "open the door")
    assert c.parse("Hold down the L2 button to aim.") == ("hold", "l2", "aim")
    assert c.parse("Tap Square repeatedly to break free") == ("mash", "square", "break free")
    assert c.parse("Lucia: Press X to win") is None
    assert c.parse("Where are you going?") is None
    assert c.compose("hold", "r3", "koşmak") == "Koşmak için R3'ü basılı tutun"
    assert c.compose("press", "left stick", "ıslık çalmak") == "Islık çalmak için sol çubuğa basın"
    assert c.compose("press", "touchpad", "haritayı açmak") == "Haritayı açmak için dokunmatik yüzeye basın"
    assert c.compose("hold", "d-pad up", "inceleme") .endswith("yukarı yön tuşunu basılı tutun")
    assert c.clean_model_action("Lucia ile konuşmak için.") == "Lucia ile konuşmak"
    assert c.clean_model_action("Işıklı saldırı.") is None


def test_game_packs_bundled_and_backfilled(monkeypatch, tmp_path):
    import trceviri.config as cfg
    from trceviri.cache import TranslationCache
    from trceviri.config import Settings
    from trceviri.pipeline import Pipeline
    monkeypatch.setattr(cfg, "PROFILE_DIR", tmp_path)
    old = json.loads((PROFILES / "tlou2.json").read_text(encoding="utf-8"))
    old["pack"] = ""                                   # 2.5 öncesi kullanıcı kopyası
    old["style"] = "kullanıcının kendi notu"
    (tmp_path / "tlou2.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    prof = cfg.load_profile("The Last of Us Part II")
    assert prof.pack == "tlou2" and prof.style == "kullanıcının kendi notu"
    p = Pipeline(Settings(), prof, TranslationCache(tmp_path / "c.db"))
    p.load_pack()
    assert p.lookup("Safe Code") == "Kasa kodu"
    for f in (PROFILES / "packs").glob("*.json"):       # paketler geçerli ve kontrol ipucu içermiyor (ortak)
        d = json.loads(f.read_text(encoding="utf-8"))
        assert all(isinstance(k, str) and isinstance(v, str) and v for k, v in d.items()), f.name


def load_from(f):
    return Profile.from_dict(json.loads(Path(f).read_text(encoding="utf-8")))


def test_vtt_timestamps():
    cues = srt.parse("WEBVTT\n\n00:01.000 --> 00:02.500\nHi there\n".replace("00:01.000", "00:00:01.000")
                     .replace("00:02.500", "00:00:02.500"))
    assert cues[0].start == "00:00:01,000" and cues[0].end == "00:00:02,500"
