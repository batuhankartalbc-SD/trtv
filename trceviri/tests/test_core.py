import threading
import time

import cv2
import numpy as np

from trceviri.cache import TranslationCache
from trceviri.textproc import is_noise, looks_english, normalize, split_speaker
from trceviri.translate import Engine, TranslationManager


def render(text: str, w=1400, h=160) -> np.ndarray:
    img = np.full((h, w, 3), (40, 60, 70), np.uint8)
    cv2.putText(img, text, (40, 100), cv2.FONT_HERSHEY_DUPLEX, 1.6, (0, 0, 0), 8, cv2.LINE_AA)
    cv2.putText(img, text, (40, 100), cv2.FONT_HERSHEY_DUPLEX, 1.6, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def test_speaker_split():
    assert split_speaker("Lucia: Where are you?") == ("Lucia", "Where are you?")
    assert split_speaker("Tourist: You take the prayer out") == ("Tourist", "You take the prayer out")
    assert split_speaker("Just a normal line") == ("", "Just a normal line")


def test_noise():
    assert is_noise("$1,250")
    assert is_noise("120 m")
    assert is_noise("12:45")
    assert is_noise("o")
    assert not is_noise("Go to the safehouse.")
    assert is_noise("SET DESTINATION", ["set destination"])


def test_normalize_and_lang():
    assert normalize("Hello ,  world !") == "Hello, world!"
    assert looks_english("Where are you")
    assert not looks_english("Neredesin şimdi")


def test_cache(tmp_path):
    c = TranslationCache(tmp_path / "c.sqlite")
    c.put("gta", "Where are you going, man?", "Nereye gidiyorsun dostum?", "x")
    assert c.get("gta", "where are you going, man?") == "Nereye gidiyorsun dostum?"
    assert c.get("gta", "Where are you going man") == "Nereye gidiyorsun dostum?"   # bulanık
    assert c.get("other", "Where are you going, man?") is None


class FakeEngine(Engine):
    name = "fake"
    is_llm = True

    def __init__(self, fail=False):
        super().__init__()
        self.calls = []
        self.fail = fail

    def translate(self, lines, context, sys):
        self.calls.append(list(lines))
        if self.fail:
            raise RuntimeError("down")
        return [f"TR:{l}" for l in lines]


def test_manager_batches_and_fallback():
    primary, backup = FakeEngine(fail=True), FakeEngine()
    m = TranslationManager(primary, backup, "GTA", {}, "samimi", 4)
    got = {}
    done = threading.Event()

    def cb(src, tr, eng, ms):
        got[src] = (tr, eng)
        if len(got) == 3:
            done.set()

    for t in ("one line", "two line", "three line"):
        m.submit(t, 0, True, cb)
    assert done.wait(5)
    m.stop()
    assert got["one line"] == ("TR:one line", "fake")
    assert sum(len(c) for c in backup.calls) == 3


def test_ocr_reads_subtitle():
    from trceviri.ocr import OcrEngine
    eng = OcrEngine()
    lines = eng.read(render("Lucia: Where are you going?"), 0.5)
    text = " ".join(l.text for l in lines)
    assert "Where are you going" in text.replace("  ", " ")
    assert lines[0].box[2] > lines[0].box[0]


def test_categories():
    from trceviri.textproc import clean_symbols, is_controls, is_navigation
    assert is_navigation("Turn Right 8 m") and is_navigation("120 m") and is_navigation("Arrive at the destination")
    assert not is_navigation("Where the hell were you?")
    assert is_controls("Press X to enter the vehicle.") and is_controls("Hold L2 to aim at the target.")
    assert is_controls("SELECT BACK O")
    assert not is_controls("Lucia: Get in the car.")
    assert clean_symbols("↑ KLOSE K17 PISTOL @ • ⁇") == "KLOSE K17 PISTOL"
