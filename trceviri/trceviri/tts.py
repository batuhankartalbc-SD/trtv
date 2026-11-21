"""Türkçe seslendirme: Windows'un kendi Türkçe sesi (Microsoft Tolga) ile, internetsiz.
Konuşma altyazıları çevrildiğinde okunur; birikirse eskiler atlanır (oyunun gerisinde kalmasın)."""
from __future__ import annotations

import asyncio
import logging
import queue
import threading

log = logging.getLogger("ses")


def available_voices() -> list[str]:
    try:
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer
        return [v.display_name for v in SpeechSynthesizer.all_voices if v.language.lower().startswith("tr")]
    except Exception:
        return []


class Speaker:
    def __init__(self, settings):
        self.settings = settings
        self.q: queue.Queue[str] = queue.Queue()
        self.spoken: set[str] = set()
        self.t = threading.Thread(target=self._run, daemon=True, name="seslendirme")
        self.t.start()

    def say(self, text: str, key: str | None = None) -> None:
        if not self.settings.tts_enabled or not text:
            return
        k = key or text
        if k in self.spoken:
            return
        self.spoken.add(k)
        if len(self.spoken) > 500:
            self.spoken.clear()
        while self.q.qsize() >= 2:          # gecikmeyi önle: en yenisi okunsun
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
        self.q.put(text)

    def _run(self) -> None:
        try:
            import winsound
            from winrt.windows.media.speechsynthesis import SpeechSynthesizer
            from winrt.windows.storage.streams import DataReader
        except Exception as e:
            log.warning("Seslendirme kullanılamıyor: %s", e)
            return
        loop = asyncio.new_event_loop()
        synth = SpeechSynthesizer()
        voices = [v for v in SpeechSynthesizer.all_voices if v.language.lower().startswith("tr")]
        if not voices:
            log.warning("Türkçe ses bulunamadı (Windows Ayarlar → Saat ve dil → Konuşma'dan Türkçe ses ekleyin)")
            return
        synth.voice = voices[0]

        async def synth_bytes(text: str) -> bytes:
            synth.options.speaking_rate = max(0.5, min(3.0, float(self.settings.tts_rate)))
            st = await synth.synthesize_text_to_stream_async(text)
            r = DataReader(st.get_input_stream_at(0))
            n = st.size
            await r.load_async(n)
            buf = bytearray(n)
            r.read_bytes(buf)
            return bytes(buf)

        while True:
            text = self.q.get()
            try:
                wav = loop.run_until_complete(synth_bytes(text))
                winsound.PlaySound(wav, winsound.SND_MEMORY)
            except Exception as e:
                log.info("seslendirme hatası: %s", e)
