"""
Speech-to-Text strategy.

PRIMARY (default, always works, zero config):
  The React frontend uses the browser's native Web Speech API
  (window.SpeechRecognition / webkitSpeechRecognition) to convert the
  candidate's voice directly into text in real time, which is then placed in
  the answer text box before submission. This requires no server round trip
  and no API key, but is only supported in Chromium-based browsers (Chrome,
  Edge). See README for the documented browser compatibility limitation.

OPTIONAL SERVER-SIDE FALLBACK:
  If a candidate's browser does not support the Web Speech API, this module
  exposes `transcribe_audio_bytes`, which forwards recorded audio to OpenAI's
  Whisper transcription endpoint IF OPENAI_API_KEY is configured. If no key
  is configured, it returns a clear, user-friendly error instead of crashing.
"""
import io
import logging

import httpx

from app.config import settings

logger = logging.getLogger("speech.stt")

OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "Server-side speech-to-text is not configured (no OPENAI_API_KEY set). "
            "Please use the in-browser microphone (Chrome/Edge) or type your answer instead."
        )
    try:
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        files = {"file": (filename, io.BytesIO(audio_bytes), "audio/webm")}
        data = {"model": "whisper-1"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(OPENAI_TRANSCRIPTION_URL, headers=headers, files=files, data=data)
            resp.raise_for_status()
            return resp.json().get("text", "")
    except Exception as exc:  # noqa: BLE001
        logger.error("Server-side transcription failed: %s", exc)
        raise RuntimeError("Speech-to-text service failed. Please type your answer instead.") from exc
