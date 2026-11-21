# TRCeviri — Real‑Time In‑Game English→Turkish Screen Translator (Windows) — Build Prompt

You are a senior full‑stack / desktop software engineer. Build the application described below **completely, runnable, production quality**. No "example code", no TODOs, no "insert your logic here". Write every file in full. Where something is ambiguous, apply the defaults in this document — do not ask me questions.

---

## 1. Goal

PS5 games (priority: **Grand Theft Auto VI**) are played on a Windows PC inside a **PS Remote Play** or **chiaki‑ng** window. The app watches that window live, **OCRs English text** inside user‑defined zones (dialogue subtitles, speaker names, mission objectives, the in‑game phone/messages screen, help/tip boxes, menus), **translates it to Turkish**, and draws the Turkish text **instantly** in a box that **fully covers the original English text**.

- No game interference at all: no memory reading, no DLL injection, no hooks. Screen pixels only.
- The entire user interface is in **Turkish**.
- Runs on the PC. The user watches the game in the Remote Play window (on the PC monitor or on a TV connected to the PC over HDMI).

## 2. Tech stack (mandatory)

- **Python 3.12**, Windows 10 2004+ / Windows 11, x64.
- UI: **PySide6** (Qt 6).
- Capture: **mss** (GDI) of the target window's client area. The overlay window is excluded from capture with `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE=0x11)`, so we never re‑read our own translation. Window geometry via `GetClientRect` + `ClientToScreen` (ctypes/pywin32). DPI awareness via `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)`.
- OCR: **RapidOCR** (`rapidocr-onnxruntime`, PP‑OCR models, CPU). Optional GPU via `onnxruntime-directml`, toggled in settings. Preprocessing with **OpenCV** + **numpy**.
- Fuzzy matching: **rapidfuzz**.
- Translation over REST with `httpx`. Engines:
  1. **Google Gemini**: default. Model is configurable; default `gemini-3.5-flash-lite`.
  2. **OpenAI**.
  3. **Anthropic Claude**.
  4. **DeepL**.
  5. **Free MyMemory API** (`api.mymemory.translated.net/get?langpair=en|tr`). Used as the fallback when there is no key or the primary engine fails. It has a daily quota; apply a cooldown on 429 or quota errors. Do not use the unofficial `translate.googleapis.com` endpoint: it rejects Python clients with 429.
- Cache: **SQLite**.
- API keys are stored encrypted with Windows **DPAPI** (`win32crypt.CryptProtectData`). Never write them to logs.
- Packaging:
  - `run.bat` creates a venv, installs `requirements.txt` and launches the app.
  - `build.bat` produces a one‑folder exe with **PyInstaller**.
- Tests: **pytest**.

## 3. Project layout

```
trceviri/
  run.bat, build.bat, requirements.txt, README.md
  trceviri/
    __main__.py, app.py, config.py, secrets.py, winutil.py, capture.py,
    zones.py, ocr.py, detect.py, textproc.py, cache.py, pipeline.py,
    overlay.py, hotkeys.py, log.py
    translate/ base.py gemini.py openai_.py claude.py deepl.py free.py manager.py
    ui/ main_window.py zone_editor.py glossary_editor.py widgets.py
  profiles/gta6.json
  tests/
```

What each module is responsible for:
- `config.py`: dataclass settings, JSON persistence and game profiles.
- `secrets.py`: DPAPI encryption of API keys.
- `winutil.py`: window enumeration, client rectangle, DPI, capture exclusion and click‑through flags.
- `capture.py`: the capture thread, with a target FPS and per‑frame timestamps.
- `zones.py`: the zone model and its types.
- `ocr.py`: the OCR wrapper, preprocessing and line grouping.
- `detect.py`: change detection, stability and empty‑zone detection.
- `textproc.py`: normalisation, speaker split and noise/HUD filters.
- `translate/manager.py`: the priority queue, batching, fallback engine, context and glossary.
- `pipeline.py`: orchestration of capture → detect → OCR → translate → display.
- `overlay.py`: the transparent, click‑through, always‑on‑top overlay.
- `ui/`: the Turkish control panel, zone editor and glossary editor.

## 4. Zones

Each zone has these fields:
- `id`, `name`, `type`;
- `x, y, w, h`, **normalised 0–1 relative to the Remote Play client area**;
- `enabled`, `stability_ms`, `min_confidence`, `cover_style`, `font_scale`, `align`.

| Type | GTA 6 example | Behaviour |
|---|---|---|
| `subtitle` | Bottom‑centre dialogue: `Lucia: Where are you?` | Highest priority. Split `Name: text` and do not translate the name; show it coloured. Stability 120 ms. Remove the overlay within 250 ms after the text disappears. For text that types out progressively, update the translation in place. |
| `objective` | Yellow/white mission line `Go to the safehouse.` | Stability 250 ms. Stays until the line changes. |
| `phone` | In‑game phone: contacts, messages, app names | Multi‑line. Cover each OCR line with its own box. Translate short UI words (`Contacts`, `Messages`) from the glossary. |
| `help` | Top‑left tip box `Press ⓧ to...` | Preserve button glyphs. When OCR turns an icon into a stray letter, mark it as `[X]`. |
| `menu` | Pause menu, settings | Optional, off by default. |
| `free` | Any user‑drawn area | Generic behaviour. |

Ship `profiles/gta6.json` for 16:9:

| Zone | x | y | w | h | Default |
|---|---|---|---|---|---|
| subtitle | 0.12 | 0.80 | 0.76 | 0.15 | on |
| objective | 0.15 | 0.70 | 0.70 | 0.08 | off |
| help | 0.01 | 0.02 | 0.30 | 0.20 | on |
| phone | 0.66 | 0.30 | 0.20 | 0.55 | off |

Profiles: support multiple games, selectable in the panel, duplicable, with import and export.

## 5. Pipeline: what makes it real‑time

1. **Capture thread**
   - Grab the client area at 20 FPS; configurable from 5 to 30.
   - Survive minimise or close, and re‑acquire the window afterwards.
   - Auto‑suggest windows whose title contains `PS Remote Play` or `chiaki`; also allow manual selection from a list.
2. **Change detection** (per zone)
   - Downscale to 1/4 → greyscale → blur → mean absolute difference against the previous frame. Below the threshold, skip OCR.
   - Run a Canny edge‑density "is the zone empty?" test. If it is empty and an overlay is showing, remove the overlay.
3. **OCR workers** (max 2 concurrent, subtitle first)
   - Preprocess: 2× INTER_CUBIC upscale, CLAHE, and inversion when the text is dark on a light background.
   - Group RapidOCR boxes into lines by y position. Drop boxes below `min_confidence`.
   - Keep the **pixel bounding box** of every line; the cover box needs it.
4. **Text processing**
   - Unicode normalisation and whitespace cleanup.
   - Light OCR fixes: `|`→`I`, contextual `0`/`O`, `rn`→`m`.
   - Speaker split with `^([A-Z][\w .'-]{0,24}):\s*(.+)$`.
   - Noise filter: drop fewer than 2 letters, digits or symbols only, and HUD constants (money `$1,234`, distance `120 m`, clock).
   - Apply a user "do not translate" list.
5. **Stability**
   - Text becomes stable when two consecutive OCR results in a zone have `rapidfuzz.ratio ≥ 90`, or when `stability_ms` has elapsed.
   - If it is ≥ 92 similar to the previous stable text, do not request a new translation; treat it as OCR jitter.
6. **Cache**
   - Key: `(profile, normalised_text, target_lang, engine)`.
   - A hit displays with **zero translation latency**.
   - Fuzzy lookup reuses entries that are ≥ 95 similar.
7. **Translation manager**
   - Priority queue: subtitle > objective > help/phone > menu.
   - Batch window of 40 ms: lines that arrive together are translated in one request as a JSON array.
   - LLM system instruction: "You translate video‑game subtitles into natural, concise, spoken Turkish. Translate slang and profanity faithfully, do not soften. Never translate proper names, brands, places. Return only a JSON array." Add to it:
     - the game title;
     - **the last 6 dialogue lines as context**;
     - the **glossary**. It is user‑editable, with a GTA 6 preset: `Vice City`, `Leonida`, `Jason`, `Lucia` stay as‑is; `cops`→`polisler`; `heat`→`aranma seviyesi`; and so on.
   - Timeout of 2.5 s. On error or timeout, fall back to **free MyMemory**. If that also fails, leave the English untouched and show no overlay.
   - Where an engine supports streaming, display the first complete sentence immediately.
   - Retry a single line when a response is truncated.
8. **Display**: when a result arrives, verify the zone still shows the same source text, so a stale translation is never painted onto a newer line. Only then push it to the overlay.

Latency targets:
- **≤ 150 ms** from the text appearing on screen when it is cached.
- **≤ 900 ms** for new lines with Gemini flash‑lite.
- Show the rolling averages of OCR, translation and total latency over the last 50 lines in the panel.

## 6. Overlay

- Window flags: frameless, `Qt.WindowStaysOnTopHint | Qt.Tool | Qt.FramelessWindowHint`, `WA_TranslucentBackground`, `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE` (click‑through, never steals focus), and `WDA_EXCLUDEFROMCAPTURE`.
- **Continuously tracks** the Remote Play client area across move, resize, full‑screen and mixed‑DPI monitors. Hides itself when Remote Play is minimised or not visible.
- Cover box, per translated line:
  - Take the **union of the OCR boxes, inflated by 6 px**, and paint it **opaque**.
  - Colour: the average sampled from the box border, or a fixed colour from settings (default `#101010` at 92 % opacity).
  - The English text must be fully hidden.
- Turkish text:
  - **Auto‑fit** in `Segoe UI Semibold` with word wrap. Shrink the font down to a minimum; if it still does not fit, grow the box vertically.
  - 2 px black outline. Speaker name in bold yellow or another accent colour.
- 80 ms fade‑in; removal is instant, with no flicker.
- Debug mode (F7) draws zone borders and OCR boxes.

## 7. Control panel (in Turkish)

Tabs:
- **Ana (Main)**
  - Window picker: auto‑detect, list and refresh.
  - Start/Stop, and status lights for Window, OCR and Translation.
  - Live latency stats.
  - Recent translations list (EN → TR, copyable).
- **Bölgeler (Zones)**
  - "Freeze frame" snapshot. On it: draw, move, resize and delete rectangles.
  - Side panel to edit type and settings, with a live per‑zone OCR preview.
  - Profile save, load, import and export.
- **Çeviri (Translation)**
  - Engine, model, masked API key with a "Test" button, and fallback engine.
  - Number of context lines, and tone (formal/casual).
  - Glossary table: EN, TR, and a "do not translate" flag.
- **Görünüm (Appearance)**
  - Font size, colours, opacity, speaker colour.
  - Cover style: opaque box, translucent, or "show below".
- **Gelişmiş (Advanced)**
  - FPS, OCR workers, GPU (DirectML), change threshold, stability timings, log level.
  - Clear or export the cache.

Global hotkeys (`RegisterHotKey`):

| Key | Action |
|---|---|
| **F8** | Toggle the overlay |
| **F9** | Pause / resume |
| **F10** | Open the zone editor |
| **F11** | Re‑translate the last line, bypassing the cache |
| **F7** | Toggle debug boxes |

Storage, all under `%APPDATA%\TRCeviri\`:

| What | Path |
|---|---|
| Settings | `config.json` |
| Profiles | `profiles\` |
| Cache | `cache.sqlite` |
| Logs | `logs\trceviri.log` (rotating, 5 MB × 3) |

## 8. Robustness

- Every thread stops cleanly on exit.
- No exception may crash the UI. A global `sys.excepthook` and the Qt message handler log the error and surface it in the panel.
- Auto‑recover when Remote Play disconnects and reconnects.
- Offline: keep working from the cache and show a warning in the panel.
- Correct positioning at 4K, 1080p and 720p, and at 100–200 % scaling.
- CPU target: below 25 % average on an 11th‑gen i5.

## 9. Tests (pytest)

- `textproc`: speaker split, noise filter and OCR fixes.
- `detect`: change threshold and stability logic, using synthetic frame sequences.
- `cache`: insert, lookup and fuzzy match.
- `translate.manager`, with a fake engine:
  - priority ordering;
  - batching;
  - fallback to the second engine;
  - dropping a stale result.
- `ocr`: an integration test on a PIL‑rendered image of "Lucia: Where are you going?".
- Overlay layout: text fitting, written as a pure function.

## 10. Deliverables

1. Full contents of every file.
2. A Turkish `README.md` covering:
   - install with `run.bat`;
   - starting Remote Play;
   - picking the window;
   - drawing zones;
   - getting a Gemini key from Google AI Studio;
   - troubleshooting:

     | Symptom | Cause / fix |
     |---|---|
     | Black frame | Remote Play hardware acceleration |
     | Empty OCR | Zone or resolution |
     | Nothing appears | The game's own subtitles must be ON |
3. Acceptance criteria. Demonstrate each one:
   - When a GTA 6 dialogue line appears in the Remote Play window, the English is fully covered and the Turkish shown within ≤ 1 s.
   - When the dialogue disappears, the Turkish disappears within ≤ 300 ms.
   - The overlay never re‑reads its own text (no feedback loop).
   - Boxes stay aligned when the window is moved or resized.
   - With no API key, the app works through free MyMemory.
   - A repeated line comes instantly from the cache.

Begin. First give a short architecture summary, then write the files one by one, completely.
