from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .tts_subscriber import TTSSubscriber, TTSConfig
from .openai_client import OpenAITTSSynthesizer
from .audio_player import AudioPlayer

@dataclass
class TTSInit:
    enabled: bool = False
    interrupt: bool = True
    voice: Optional[str] = None

def make_tts_subscriber(init: Optional[TTSInit] = None) -> TTSSubscriber:
    init = init or TTSInit()

    synth = OpenAITTSSynthesizer()   # reads env/config internally
    player = AudioPlayer()           # picks a backend internally

    return TTSSubscriber(
        synthesizer=synth,
        player=player,
        config=TTSConfig(
            enabled=init.enabled,
            interrupt=init.interrupt,
            voice=init.voice,
        ),
    )
