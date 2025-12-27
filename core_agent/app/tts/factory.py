from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .tts_subscriber import TTSSubscriber, TTSConfig
from .openai_client import OpenAITTSSynthesizer
from .elevenlabs_client import ElevenLabsTTSSynthesizer
from .audio_player import AudioPlayer
from ..config import TTS_PROVIDER

@dataclass
class TTSInit:
    enabled: bool = False
    interrupt: bool = True
    voice: Optional[str] = None

def make_tts_subscriber(init: Optional[TTSInit] = None) -> TTSSubscriber:
    init = init or TTSInit()
    provider = TTS_PROVIDER
    
    if provider == "openai":
        syth = OpenAITTSSynthesizer()
    elif provider == "elevenlabs":
        synth = ElevenLabsTTSSynthesizer()
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {provider!r}")

    player = AudioPlayer()           # picks a backend internally

    return TTSSubscriber(
        tts_client=synth,
        audio_player=player,
        config=TTSConfig(
            enabled=init.enabled,
            interrupt=init.interrupt,
            voice=init.voice,
        ),
    )
