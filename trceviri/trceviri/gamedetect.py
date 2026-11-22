"""Hangi oyun oynanıyor? Ekranda okunan yazılardaki özel isimlerden (karakter, yer, terim) tahmin eder.

Her oyun profilinin sözlüğündeki "çevrilmez" (boş değerli) terimler o oyunun parmak izidir: Kratos, Aloy, Ellie...
Son birkaç dakikada okunan metinlerde başka bir oyunun en az 3 farklı terimi geçiyorsa ve o oyun mevcut profilden
açıkça öndeyse profil değiştirme önerilir. Kullanıcı onaylamadan profil değişmez.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque

GENERIC = {"genel oyun (her oyun)", "genel", "film / dizi"}
# birden fazla oyunda geçen ya da sıradan kelime olan terimler parmak izi sayılmaz
STOP = {"ghost", "boy", "sam", "adam", "eve", "focus", "spirit", "machine", "realm", "katana", "porter", "merchant"}


class GameDetector:
    MIN_HITS = 3

    def __init__(self, profiles: list):
        self.lock = threading.Lock()
        self.recent: deque[tuple[float, str]] = deque(maxlen=400)
        self.terms: dict[str, list[tuple[str, re.Pattern]]] = {}
        counts: dict[str, int] = {}
        raw: dict[str, set[str]] = {}
        for p in profiles:
            if getattr(p, "kind", "game") != "game" or p.name.lower() in GENERIC:
                continue
            ts = {k.strip() for k, v in p.glossary.items() if not v and len(k.strip()) >= 3}
            ts = {t for t in ts if t.lower() not in STOP}
            raw[p.name] = ts
            for t in ts:
                counts[t.lower()] = counts.get(t.lower(), 0) + 1
        for name, ts in raw.items():
            uniq = [t for t in ts if counts[t.lower()] == 1]          # sadece bu oyuna özgü terimler
            self.terms[name] = [(t, re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w])", re.I)) for t in uniq]

    def feed(self, text: str) -> None:
        if text:
            with self.lock:
                self.recent.append((time.monotonic(), text))

    def scores(self, window_s: float = 240.0) -> dict[str, set[str]]:
        now = time.monotonic()
        with self.lock:
            texts = [t for ts, t in self.recent if now - ts <= window_s]
        blob = "\n".join(texts)
        out: dict[str, set[str]] = {}
        if not blob:
            return out
        for name, pats in self.terms.items():
            hits = {t for t, rx in pats if rx.search(blob)}
            if hits:
                out[name] = hits
        return out

    def suggest(self, current: str) -> tuple[str, list[str]] | None:
        """(önerilen profil, bulunan terimler) ya da None."""
        sc = self.scores()
        if not sc:
            return None
        best = max(sc, key=lambda n: len(sc[n]))
        if best == current or len(sc[best]) < self.MIN_HITS:
            return None
        if len(sc.get(current, ())) * 2 >= len(sc[best]):            # mevcut oyun da güçlü eşleşiyor: karışma
            return None
        return best, sorted(sc[best])
