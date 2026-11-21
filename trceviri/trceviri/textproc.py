"""OCR metnini temizleme, konuşmacı ayırma ve gürültü filtreleri."""
from __future__ import annotations

import re
import unicodedata

SPEAKER_RE = re.compile(r"^([A-Z][A-Za-z0-9 .'\-]{0,24}?)\s*[:;]\s+(.+)$")
HUD_RES = [
    re.compile(r"^\$?\s?[\d.,]+\s?(\$|m|km|ft|mi|%)?$", re.I),     # para, mesafe, sayı
    re.compile(r"^\d{1,2}:\d{2}(\s?[ap]m)?$", re.I),                 # saat
    re.compile(r"^[\W_]+$"),                                         # sadece simge
]
_FIXES = [
    (re.compile(r"(?<=\s)\|(?=\s)"), "I"),
    (re.compile(r"^\|(?=\s)"), "I"),
    (re.compile(r"(?<=[a-z])\|(?=[a-z])"), "l"),
    (re.compile(r"\s+([,.!?;:])"), r"\1"),
    (re.compile(r"([,.!?])(?=[A-Za-z])"), r"\1 "),
    (re.compile(r"\s{2,}"), " "),
    (re.compile(r"[’‘`´]"), "'"),
    (re.compile(r"[“”]"), '"'),
]


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").strip()
    for rx, rep in _FIXES:
        t = rx.sub(rep, t)
    return t.strip(" -_~")


def letters(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def is_noise(text: str, ignore: list[str] | None = None) -> bool:
    t = text.strip()
    if letters(t) < 2:
        return True
    if any(rx.match(t) for rx in HUD_RES):
        return True
    if sum(ch.isdigit() for ch in t) > letters(t):     # "Build 930.048.020" gibi sürüm/sayı satırları
        return True
    if ignore and t.lower() in {i.lower() for i in ignore}:
        return True
    return False


TR_WORDS = {
    "ve", "bir", "bu", "için", "icin", "ile", "da", "de", "ya", "mi", "ne", "çok", "cok", "daha", "gibi", "olarak",
    "yap", "giris", "giriş", "ayarlar", "ayarları", "kullanarak", "sistemlerinde", "uzaktan", "oyunlari",
    "oyunları", "basın", "basin", "tuşuna", "tusuna", "devam", "geri", "iptal", "tamam", "evet", "hayır", "hayir",
    "hos", "hoş", "geldiniz", "bağlan", "baglan", "seçenekler", "secenekler", "oyna", "değil", "degil",
}
EN_WORDS = {
    "the", "to", "you", "and", "of", "is", "it", "in", "that", "we", "for", "on", "with", "this", "what", "your",
    "are", "be", "have", "not", "go", "get", "my", "me", "i", "a", "an", "at", "press", "hold", "do", "was",
}


def looks_english(text: str) -> bool:
    """Türkçe karakter içeren ya da zaten Türkçe görünen satırları çevirmeye gönderme.
    OCR Türkçe harfleri (ş, ı, ğ) kaçırabildiği için kelime listesiyle de kontrol edilir."""
    if re.search(r"[çğıöşüÇĞİÖŞÜ]", text):
        return False
    if letters(text) < 2:
        return False
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
    if not words:
        return False
    tr = sum(w in TR_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    if tr > en:
        return False
    return True


def split_speaker(text: str) -> tuple[str, str]:
    m = SPEAKER_RE.match(text)
    if m and len(m.group(1).split()) <= 3:
        return m.group(1).strip(), m.group(2).strip()
    return "", text


_ALLOWED = re.compile(r"[^0-9A-Za-zÀ-ÿçğıöşüÇĞİÖŞÜ \.,!\?'\"\-:;\(\)%&/\$]")
NAV_RE = re.compile(
    r"\b(turn (left|right)|keep (left|right)|bear (left|right)|make a u-?turn|u-?turn|continue (straight|on)|"
    r"take the (exit|ramp)|exit \d|merge|arriv(e|ing|ed)|you have arrived|destination|recalculating|"
    r"go straight|head (north|south|east|west)|roundabout)\b", re.I)
DIST_RE = re.compile(r"\b\d+([.,]\d+)?\s?(m|ft|km|mi|yd|yds|miles?|meters?|feet)\b", re.I)
CTRL_RE = re.compile(r"^(press|hold|tap|use|release|mash|rotate|move|push|pull|aim|select|back|confirm|cancel|skip)\b", re.I)
BTN_RE = re.compile(r"\b(x|o|l1|l2|l3|r1|r2|r3|square|triangle|circle|cross|options|touchpad|share|"
                    r"left stick|right stick|d-?pad)\b", re.I)
UI_WORDS = {"select", "back", "confirm", "cancel", "accept", "continue", "options", "skip", "exit", "quit",
            "zoom", "scroll", "navigate", "toggle", "info", "details", "reset", "apply", "delete", "change"}


def clean_symbols(text: str) -> str:
    """OCR'ın buton simgelerinden ve ikonlardan ürettiği özel karakterleri temizler (↑ @ ⁇ • © vb.)."""
    t = _ALLOWED.sub(" ", text or "")
    t = re.sub(r"\s{2,}", " ", t).strip(" -:;,")
    return t


def is_navigation(text: str) -> bool:
    """GPS / yön tarifi / mesafe yazıları: 'Turn Right 8 m', '120 m', 'Arrive at destination'."""
    return bool(NAV_RE.search(text)) or (bool(DIST_RE.search(text)) and len(text.split()) <= 5)


def is_controls(text: str) -> bool:
    """Kontrol / tuş ipucu: 'Press X to enter the vehicle', 'Hold L2 to aim', 'SELECT  BACK'."""
    if CTRL_RE.search(text) and (BTN_RE.search(text) or " to " in f" {text.lower()} "):
        return True
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", text)]
    return bool(words) and len(words) <= 4 and all(w in UI_WORDS or len(w) <= 2 for w in words)


def cache_key(text: str) -> str:
    t = normalize(text).lower()
    return re.sub(r"[^\w' ]+", "", t).strip()
