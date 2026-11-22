"""Kontrol ipuçları için kalıp çeviri: "Press X to open the door" → "Kapıyı açmak için X'e basın".

Yerel model bu kalıpları sık bozuyor ("L2'yi nişan al", "R1'e ışık saldırısına basın", "Çemberi çömelmek için tut").
Burada tuş adı ve Türkçe eki (X'e / Kare'ye / R2'yi / L3'ü) kuralla, eylem ise sözlükten ya da modelden
("In order to V." → "V-mek için") gelir; cümle Türkçe dizilişle kurulur.
"""
from __future__ import annotations

import re

# İngilizce tuş adı → (Türkçe ad, -e hali eki, -i hali eki)
BUTTONS: dict[str, tuple[str, str, str]] = {
    "x": ("X", "'e", "'i"), "cross": ("X", "'e", "'i"),
    "o": ("O", "'ya", "'yu"), "circle": ("Daire", "'ye", "'yi"),
    "square": ("Kare", "'ye", "'yi"), "triangle": ("Üçgen", "'e", "'i"),
    "r1": ("R1", "'e", "'i"), "r2": ("R2", "'ye", "'yi"), "r3": ("R3", "'e", "'ü"),
    "l1": ("L1", "'e", "'i"), "l2": ("L2", "'ye", "'yi"), "l3": ("L3", "'e", "'ü"),
    "options": ("OPTIONS", "'a", "'ı"), "create": ("CREATE", "'e", "'i"), "share": ("SHARE", "'e", "'i"),
    "touchpad": ("dokunmatik yüzey", "e", "i"), "touch pad": ("dokunmatik yüzey", "e", "i"),
    "touchpad button": ("dokunmatik yüzey", "e", "i"),
    "left stick": ("sol çubuk", "a", "u"), "right stick": ("sağ çubuk", "a", "u"),
    "d-pad up": ("yukarı yön tuşu", "na", "nu"), "d-pad down": ("aşağı yön tuşu", "na", "nu"),
    "d-pad left": ("sol yön tuşu", "na", "nu"), "d-pad right": ("sağ yön tuşu", "na", "nu"),
    "up": ("yukarı yön tuşu", "na", "nu"), "down": ("aşağı yön tuşu", "na", "nu"),
    "left": ("sol yön tuşu", "na", "nu"), "right": ("sağ yön tuşu", "na", "nu"),
    "d-pad": ("yön tuşu", "na", "nu"), "ps button": ("PS tuşu", "na", "nu"),
}
# "sol çubuk" + a → "sol çubuğa" (k→ğ yumuşaması)
_SOFT = {"sol çubuk": "sol çubuğ", "sağ çubuk": "sağ çubuğ"}

# oyunlarda sık geçen eylemler (model bunları yanlış çeviriyor ya da oyun terimi farklı)
ACTIONS: dict[str, str] = {
    "aim": "nişan almak", "shoot": "ateş etmek", "fire": "ateş etmek", "reload": "şarjör değiştirmek",
    "sprint": "koşmak", "run": "koşmak", "walk": "yürümek", "crouch": "eğilmek", "jump": "zıplamak",
    "climb": "tırmanmak", "vault": "üstünden atlamak", "dodge": "kaçmak", "roll": "yuvarlanmak",
    "block": "bloklamak", "parry": "savuşturmak", "attack": "saldırmak", "light attack": "hafif saldırı yapmak",
    "heavy attack": "ağır saldırı yapmak", "melee": "yakın dövüş saldırısı yapmak", "lock on": "hedefe kilitlenmek",
    "lock-on": "hedefe kilitlenmek", "interact": "etkileşime geçmek", "pick up": "almak", "loot": "toplamak",
    "accelerate": "hızlanmak", "brake": "fren yapmak", "reverse": "geri gitmek", "handbrake": "el frenini çekmek",
    "drift": "drift yapmak", "honk": "korna çalmak", "use horn": "korna çalmak", "break free": "kurtulmak",
    "struggle": "kurtulmaya çalışmak", "skip": "geçmek", "skip cutscene": "ara sahneyi geçmek", "pause": "duraklatmak",
    "cancel": "iptal etmek", "continue": "devam etmek", "confirm": "onaylamak", "go back": "geri dönmek",
    "back": "geri dönmek", "open the map": "haritayı açmak", "open map": "haritayı açmak",
    "switch weapons": "silah değiştirmek", "change weapons": "silah değiştirmek", "swap weapons": "silah değiştirmek",
    "heal": "iyileşmek", "use item": "eşya kullanmak", "throw": "fırlatmak", "take cover": "siper almak",
    "cover": "siper almak", "hide": "saklanmak", "swim": "yüzmek", "dive": "dalmak", "talk": "konuşmak",
    "enter vehicle": "araca binmek", "enter the vehicle": "araca binmek", "exit vehicle": "araçtan inmek",
    "exit the vehicle": "araçtan inmek", "get in": "binmek", "get out": "inmek", "mount": "binmek",
    "dismount": "inmek", "zoom": "yakınlaştırmak", "zoom in": "yakınlaştırmak", "zoom out": "uzaklaştırmak",
    "scan": "taramak", "focus": "odaklanmak", "whistle": "ıslık çalmak", "call horse": "atı çağırmak",
    "inspect": "incelemek", "examine": "incelemek", "rotate": "döndürmek", "sell": "satmak", "buy": "satın almak",
    "equip": "kuşanmak", "fast travel": "hızlı seyahat etmek", "set waypoint": "yol noktası koymak",
    "place waypoint": "yol noktası koymak", "start mission": "görevi başlatmak", "start": "başlamak",
    "retry": "tekrar denemek", "restart": "yeniden başlamak", "quick save": "hızlı kaydetmek", "save": "kaydetmek",
    "open the menu": "menüyü açmak", "open menu": "menüyü açmak", "open inventory": "envanteri açmak",
    "open the inventory": "envanteri açmak", "use ability": "yetenek kullanmak", "photo mode": "fotoğraf moduna geçmek",
}

_PRESS = r"(?P<verb>press(?: and hold)?|hold(?: down)?|tap|mash|repeatedly press|tap repeatedly|press repeatedly)"
_BTN = r"(?:the\s+)?(?P<btn>" + "|".join(sorted((re.escape(b) for b in BUTTONS), key=len, reverse=True)) + r")(?:\s+button)?"
_RX = re.compile(r"^\s*" + _PRESS + r"\s+" + _BTN + r"(?P<rep>\s+repeatedly)?\s+to\s+(?P<act>[^.!?]+?)\s*[.!]?\s*$", re.I)


def parse(text: str):
    m = _RX.match(text or "")
    if not m:
        return None
    verb = m.group("verb").lower()
    kind = "hold" if verb.startswith("hold") or "and hold" in verb else \
           "mash" if ("repeat" in verb or verb == "mash" or m.group("rep")) else "press"
    return kind, m.group("btn").lower(), m.group("act").strip()


def button(btn: str, case: str) -> str:
    name, dat, acc = BUTTONS[btn]
    suf = dat if case == "dat" else acc
    base = _SOFT.get(name, name) if suf[:1] in "aeıiouöü" and not suf.startswith("'") else name
    return base + suf


def compose(kind: str, btn: str, action_tr: str) -> str:
    a = action_tr.strip().rstrip(".").strip()
    a = re.sub(r"\s+için$", "", a, flags=re.I)
    if kind == "hold":
        return _cap(f"{a} için {button(btn, 'acc')} basılı tutun")
    if kind == "mash":
        return _cap(f"{a} için {button(btn, 'dat')} art arda basın")
    return _cap(f"{a} için {button(btn, 'dat')} basın")


def action_from_dict(act: str) -> str | None:
    return ACTIONS.get(act.lower().strip())


def model_input(act: str) -> str:
    """Modelin eylemi '-mek için' biçiminde vermesi için sorulacak cümle."""
    return f"In order to {act}."


def clean_model_action(t: str) -> str | None:
    """'Kapıyı açmak için.' → 'Kapıyı açmak'. Beklenen biçimde değilse None (genel çeviriye bırak)."""
    t = t.strip().rstrip(".").strip()
    m = re.match(r"^(.+?\b\w+(?:mak|mek))\s+için$", t, re.I)
    if not m:
        return None
    return m.group(1)


def _cap(s: str) -> str:
    if not s:
        return s
    first = {"i": "İ", "ı": "I"}.get(s[0], s[0].upper())
    return first + s[1:]
