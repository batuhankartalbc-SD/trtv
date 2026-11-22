"""contrib/ önerilerini doğrulayıp profiles/packs/ içine birleştirir.

Kullanım:  python tools/merge_packs.py [--dry]
- contrib/ortak_ui.json          → profiles/packs/ortak.json
- contrib/gta6_extra.json        → profiles/packs/gta6.json
- contrib/packs/<profil>.json    → profiles/packs/<profil>.json (+ profiles/<profil>.json "pack" alanı)
Mevcut (elle seçilmiş) satırlar her zaman korunur. Oyun paketinde ortak paketle birebir aynı satırlar atılır.
Reddedilen satırlar tools/merge_rejects.txt dosyasına yazılır.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from trceviri import controls  # noqa: E402
from trceviri.cache import cache_key  # noqa: E402

CONTRIB = ROOT.parent / "contrib"
PACKS = ROOT / "profiles" / "packs"
PROFILES = ROOT / "profiles"

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")
TOKEN = re.compile(r"\{[^}]*\}|%[sd\d]|<[^>]+>|\[[A-Z0-9_]+\]")
TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
EN_WORDS = {"the", "and", "you", "your", "with", "press", "hold", "to", "of", "is", "are", "for"}


# "Defend the X" / "Upgrade X" gibi nesne alan emir kalıpları: öneri üreticisi çoğunda Türkçe hâl ekini unutmuş
# ("tren savun", "Arena kabul et", "Moğollar yükselt"). Nesneden önceki sözcükte ek yoksa reddedilir.
OBJ_VERBS = re.compile(r"^(defend|rescue|reach|go to|travel to|escape to|meet at|regroup at|return to|head to|"
                       r"accept|abandon|restart|untrack|track|upgrade|activate|collect|inspect|use|summon|find|"
                       r"open|enter|release|destroy|protect|escort|follow|search|investigate|turn|start|view|"
                       r"select|explore|clear|secure|locate|get to|abandon)\b", re.I)
CASE_END = re.compile(r"(ı|i|u|ü|a|e|da|de|ta|te|dan|den|tan|ten|la|le|ın|in|un|ün)$", re.I)
PASSIVE_END = re.compile(r"(dı|di|du|dü|tı|ti|tu|tü)$")
TR_ONLY = set("çğıöşüÇĞİÖŞ")


def _cap(s: str) -> str:
    return ({"i": "İ", "ı": "I"}.get(s[0], s[0].upper()) + s[1:]) if s else s


def clean(en: str, tr: str) -> tuple[str | None, str | None]:
    """(düzeltilmiş çeviri, None) ya da (None, red sebebi)."""
    if not isinstance(en, str) or not isinstance(tr, str) or not en.strip() or not tr.strip():
        return None, "boş"
    if TR_ONLY & set(en):
        return None, "İngilizce anahtarda Türkçe"
    if re.search(r"\d+\s*%", en):
        return None, "yüzde/sayı varyantı"
    if controls.parse(en):
        return None, "kontrol ipucu (controls.py şablonu daha doğru)"
    if en[:1].isupper() and tr[:1].islower():
        if not PASSIVE_END.search(tr.split()[-1]):
            return None, "küçük harf + eksik ek"
        tr = _cap(tr)
    m = OBJ_VERBS.match(en)
    words = tr.split()
    if m and len(words) >= 2:
        # fiil 1–2 sözcük ("savun", "kabul et"); nesne onun hemen önündeki sözcük
        verb_len = 2 if words[-1] in ("et", "yap", "ol", "ver", "al") and len(words) >= 3 else 1
        obj = words[-1 - verb_len].strip("'’")
        if not CASE_END.search(obj) and "'" not in words[-1 - verb_len]:
            return None, "nesnede hâl eki yok"
    why = problem(en, tr)
    return (None, why) if why else (tr, None)


def problem(en: str, tr: str) -> str | None:
    if EMOJI.search(tr) and not EMOJI.search(en):
        return "emoji"
    if sorted(TOKEN.findall(en)) != sorted(TOKEN.findall(tr)):
        return "yer tutucu farklı"
    for a, b in ('""', "()", "[]"):
        if tr.count(a) - (tr.count(b) if a != b else 0) != en.count(a) - (en.count(b) if a != b else 0):
            return f"denk olmayan {a}{b}"
    if len(tr) > max(12, len(en) * 3.2) or (len(en) > 12 and len(tr) < len(en) * 0.3):
        return "uzunluk oranı"
    words = re.findall(r"[a-zA-Z]+", tr.lower())
    if len(words) >= 3 and sum(w in EN_WORDS for w in words) >= 2 and not TR_CHARS & set(tr):
        return "İngilizce kalmış"
    letters = [c for c in en if c.isalpha()]
    if len(letters) >= 4 and all(c.isupper() for c in letters):
        tl = [c for c in tr if c.isalpha()]
        if tl and not all(c.isupper() for c in tl):
            return "büyük harf uyumsuz"
    return None


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def merge(base: dict, extra: dict, name: str, rejects: list, drop: dict | None = None) -> tuple[dict, int]:
    seen = {cache_key(k) for k in base}
    added = 0
    for en, tr in extra.items():
        k = cache_key(en)
        if k in seen:
            continue
        fixed, why = clean(en, tr)
        if why:
            rejects.append(f"{name}\t{why}\t{en}\t{tr}")
            continue
        tr = fixed
        if drop is not None and drop.get(k) == tr:
            continue                                  # ortak paketle aynı → gereksiz
        base[en] = tr
        seen.add(k)
        added += 1
    return base, added


def save(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(dry: bool) -> None:
    rejects: list[str] = []
    ortak, n = merge(load(PACKS / "ortak.json"), load(CONTRIB / "ortak_ui.json"), "ortak", rejects)
    print(f"ortak: +{n} → {len(ortak)}")
    common = {cache_key(k): v for k, v in ortak.items()}
    gta, n = merge(load(PACKS / "gta6.json"), load(CONTRIB / "gta6_extra.json"), "gta6", rejects, common)
    print(f"gta6: +{n} → {len(gta)}")
    out = {"ortak": ortak, "gta6": gta}
    for f in sorted((CONTRIB / "packs").glob("*.json")):
        prof = PROFILES / f.name
        if not prof.exists():
            print(f"{f.stem}: profil yok, atlandı")
            continue
        d, n = merge(load(PACKS / f.name), load(f), f.stem, rejects, common)
        out[f.stem] = d
        print(f"{f.stem}: +{n} → {len(d)}")
    (ROOT / "tools" / "merge_rejects.txt").write_text("\n".join(rejects) + "\n", encoding="utf-8")
    print(f"reddedilen: {len(rejects)} (tools/merge_rejects.txt)")
    if dry:
        return
    for name, d in out.items():
        save(PACKS / f"{name}.json", d)
        prof = PROFILES / f"{name}.json"
        if name != "ortak" and prof.exists():
            pd = json.loads(prof.read_text(encoding="utf-8"))
            if pd.get("pack") != name:
                pd["pack"] = name
                prof.write_text(json.dumps(pd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main("--dry" in sys.argv)
