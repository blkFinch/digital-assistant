# openai_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from ..config import OPENAI_API_KEY, OPENAI_MODEL, TTS_VOICE, TTS_FORMAT


@dataclass
class OpenAITTSConfig:
    """
    Configuration for OpenAI text-to-speech.
    """
    model: str = OPENAI_MODEL
    voice: str = TTS_VOICE
    response_format: str = TTS_FORMAT        # wav recommended for simplest playback
    # sample_rate is not directly configurable in OpenAI TTS API


class OpenAITTSSynthesizer:
    """
    Thin wrapper around OpenAI's TTS endpoint.

    synthesize(text) -> audio bytes
    """
    def __init__(self, config: Optional[OpenAITTSConfig] = None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")

        self.config = config or OpenAITTSConfig()
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def synthesize(self, text: str, *, voice: Optional[str] = None) -> bytes:
        """
        Convert text to speech and return raw audio bytes.
        Blocking call; run from a worker thread.
        """
        if not text.strip():
            return b""

        voice = voice or self.config.voice

        # OpenAI Python SDK supports streaming and non-streaming;
        # this is the simplest non-streaming form.
        response = self.client.audio.speech.create(
            model=self.config.model,
            voice=voice,
            input=text,
            response_format=self.config.response_format,
        )

        # response is a binary-like object
        return response.read()
