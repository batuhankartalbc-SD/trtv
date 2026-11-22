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


def test_vtt_timestamps():
    cues = srt.parse("WEBVTT\n\n00:01.000 --> 00:02.500\nHi there\n".replace("00:01.000", "00:00:01.000")
                     .replace("00:02.500", "00:00:02.500"))
    assert cues[0].start == "00:00:01,000" and cues[0].end == "00:00:02,500"
