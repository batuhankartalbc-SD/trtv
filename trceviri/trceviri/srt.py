"""İngilizce altyazı dosyası (.srt / .vtt) → Türkçe .srt.

Film TV'de Plex / Kodi / VLC ile oynatılıyorsa canlı okumaya gerek yok: altyazı dosyası önceden çevrilir,
oynatıcıda Türkçe altyazı olarak seçilir. Zamanlamalar aynen korunur.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

log = logging.getLogger("srt")
_TIME = re.compile(r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})")
_TAG = re.compile(r"</?[^>]+>|\{\\[^}]*\}")


@dataclass
class Cue:
    start: str
    end: str
    text: str            # satırlar "\n" ile


def _ts(t: str) -> str:
    """VTT/kısa biçimi SRT zamanına çevirir: 00:01:02,345"""
    t = t.replace(".", ",")
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms.ljust(3, '0')[:3]}"


def parse(text: str) -> list[Cue]:
    text = text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [l for l in block.split("\n") if l.strip()]
        for i, l in enumerate(lines):
            m = _TIME.search(l)
            if m:
                body = "\n".join(lines[i + 1:]).strip()
                if body:
                    cues.append(Cue(_ts(m.group(1)), _ts(m.group(2)), body))
                break
    return cues


def write(cues: list[Cue]) -> str:
    return "\n".join(f"{i}\n{c.start} --> {c.end}\n{c.text}\n" for i, c in enumerate(cues, 1))


def _plain(t: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub("", t)).strip()


def _italic(t: str) -> bool:
    s = t.strip()
    return s.lower().startswith("<i>") and s.lower().endswith("</i>")


def _wrap(t: str, width: int = 42) -> str:
    """Türkçe metni en fazla 2 dengeli satıra böler (diyalog tireleri ayrı satırda kalır)."""
    parts = re.split(r"\s(?=- )", t)
    if len(parts) == 2 and all(p.startswith("- ") for p in parts) or (len(parts) == 2 and parts[1].startswith("- ")):
        return "\n".join(parts)
    if len(t) <= width:
        return t
    words, best, best_d = t.split(), t, 10 ** 9
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        d = abs(len(a) - len(b))
        if d < best_d:
            best, best_d = f"{a}\n{b}", d
    return best


def translate_cues(cues: list[Cue], translate: Callable[[list[str], list[str]], list[str]],
                   progress: Callable[[int, int], None] | None = None, batch: int = 20) -> list[Cue]:
    """translate(lines, context) → Türkçe satırlar. Müzik (♪) satırları olduğu gibi kalır."""
    out: list[Cue] = []
    ctx: list[str] = []
    for i in range(0, len(cues), batch):
        chunk = cues[i:i + batch]
        src = [_plain(c.text) for c in chunk]
        todo = [j for j, s in enumerate(src) if s and "♪" not in s and "♫" not in s]
        tr = [""] * len(chunk)
        if todo:
            try:
                res = translate([src[j] for j in todo], ctx[-6:])
            except Exception as e:
                log.warning("altyazı parçası çevrilemedi (%d. satır): %s", i + 1, e)
                res = [""] * len(todo)
            for j, r in zip(todo, res):
                tr[j] = r
        for c, s, t in zip(chunk, src, tr):
            if t:
                body = _wrap(_plain(t))
                if _italic(c.text):
                    body = f"<i>{body}</i>"
            else:
                body = c.text                       # çevrilemeyen / şarkı satırı: orijinal kalsın
            out.append(Cue(c.start, c.end, body))
        ctx += [s for s in src if s]
        if progress:
            progress(min(len(cues), i + batch), len(cues))
    return out


def read_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def output_path(path: Path) -> Path:
    """film.en.srt → film.tr.srt, film.srt → film.tr.srt (oynatıcılar dili dosya adından tanır)."""
    stem = re.sub(r"\.(en|eng|english)$", "", path.stem, flags=re.I)
    return path.with_name(f"{stem}.tr.srt")


def translate_file(path: Path, translate, progress=None) -> tuple[Path, int]:
    cues = parse(read_file(path))
    if not cues:
        raise ValueError("Dosyada altyazı bulunamadı (.srt ya da .vtt olmalı)")
    res = translate_cues(cues, translate, progress)
    out = output_path(path)
    out.write_text(write(res), encoding="utf-8-sig")
    log.info("Altyazı çevrildi: %s → %s (%d satır)", path.name, out.name, len(res))
    return out, len(res)
