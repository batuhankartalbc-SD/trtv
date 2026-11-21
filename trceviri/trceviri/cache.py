"""SQLite çeviri önbelleği (tam + bulanık eşleşme)."""
from __future__ import annotations

import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path

from rapidfuzz import fuzz, process

from .textproc import cache_key


class TranslationCache:
    def __init__(self, path: Path | str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS tr (k TEXT PRIMARY KEY, src TEXT, dst TEXT, engine TEXT, ts REAL)")
        self.db.commit()
        self.lock = threading.Lock()
        self.recent: OrderedDict[str, str] = OrderedDict()
        for k, dst in self.db.execute("SELECT k, dst FROM tr ORDER BY ts DESC LIMIT 3000"):
            self.recent[k] = dst

    def _key(self, scope: str, text: str) -> str:
        return f"{scope}|{cache_key(text)}"

    def get(self, scope: str, text: str, fuzzy: bool = True) -> str | None:
        k = self._key(scope, text)
        with self.lock:
            if k in self.recent:
                self.recent.move_to_end(k)
                return self.recent[k]
            row = self.db.execute("SELECT dst FROM tr WHERE k=?", (k,)).fetchone()
            if row:
                self.recent[k] = row[0]
                return row[0]
            if fuzzy and len(k) > len(scope) + 12:
                cand = [c for c in self.recent.keys() if c.startswith(scope + "|")]
                m = process.extractOne(k, cand, scorer=fuzz.ratio, score_cutoff=95)
                if m:
                    return self.recent[m[0]]
        return None

    def put(self, scope: str, text: str, dst: str, engine: str) -> None:
        k = self._key(scope, text)
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO tr VALUES (?,?,?,?,?)", (k, text, dst, engine, time.time()))
            self.db.commit()
            self.recent[k] = dst
            self.recent.move_to_end(k)
            while len(self.recent) > 5000:
                self.recent.popitem(last=False)

    def clear(self) -> None:
        with self.lock:
            self.db.execute("DELETE FROM tr")
            self.db.commit()
            self.recent.clear()

    def count(self) -> int:
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM tr").fetchone()[0]
