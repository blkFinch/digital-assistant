# elevenlabs_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import requests

from ..config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID


@dataclass
class ElevenLabsTTSConfig:
    """
    Configuration for ElevenLabs TTS.
    """
    voice_id: str = ELEVENLABS_VOICE_ID
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "wav"   # "wav" or "mp3"
    stability: float = 0.38      # lower = more expressive
    similarity_boost: float = 0.8
    style: Optional[float] = 0.08    # some voices/models support this
    use_speaker_boost: bool = True


class ElevenLabsTTSSynthesizer:
    """
    ElevenLabs text-to-speech synthesizer.

    synthesize(text) -> audio bytes
    """
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, config: Optional[ElevenLabsTTSConfig] = None):
        if not ELEVENLABS_API_KEY:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")
        if not ELEVENLABS_VOICE_ID:
            raise RuntimeError("ELEVENLABS_VOICE_ID is not set")

        self.config = config or ElevenLabsTTSConfig()

    def synthesize(self, text: str, *, voice: Optional[str] = None) -> bytes:
        """
        Convert text to speech and return raw audio bytes.
        Blocking call; run from a worker thread.
        """
        text = text.strip()
        if not text:
            return b""

        voice_id = voice or self.config.voice_id

        url = f"{self.API_URL}/{voice_id}"
        headers = {
            "Accept": "audio/wav" if self.config.output_format == "wav" else "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
        }

        voice_settings = {
            "stability": self.config.stability,
            "similarity_boost": self.config.similarity_boost,
            "use_speaker_boost": self.config.use_speaker_boost,
        }
        if self.config.style is not None:
            voice_settings["style"] = self.config.style

        payload = {
            "text": text,
            "model_id": self.config.model_id,
            "voice_settings": voice_settings,
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"ElevenLabs TTS failed ({resp.status_code}): {resp.text}"
            )

        return resp.content
