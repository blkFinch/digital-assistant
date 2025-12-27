#!/usr/bin/env python3
"""
Test script for TTS components.

This script demonstrates:
- Creating a TTS subscriber with OpenAI client and audio player
- Sending a sample AgentOutput message
- Observing the TTS synthesis and playback flow (without actual audio output)

Run with: python -m core_agent.scripts.test_tts
"""

import time
from core_agent.app.core.contracts import AgentOutput, PuppetDirective
from core_agent.app.tts.openai_client import OpenAITTSSynthesizer, OpenAITTSConfig
from core_agent.app.tts.audio_player import AudioPlayer, AudioPlayerConfig
from core_agent.app.tts.tts_subscriber import TTSSubscriber, TTSConfig
from core_agent.app.utils.logger import configure_logging


def main():
    configure_logging(debug=True)
    print("Setting up TTS components...")

    # Configure TTS
    tts_config = OpenAITTSConfig(
        model="gpt-4o-mini-tts",
        voice="alloy",
        response_format="wav",
    )
    tts_client = OpenAITTSSynthesizer(config=tts_config)
    print("✓ OpenAI TTS client initialized")

    # Configure audio player
    player_config = AudioPlayerConfig(
        keep_temp_files=True,  # Keep temp files for inspection
    )
    audio_player = AudioPlayer(config=player_config)
    print("✓ Audio player initialized")

    # Configure TTS subscriber
    subscriber_config = TTSConfig(
        enabled=True,
        interrupt=True,
        voice="alloy",
    )
    subscriber = TTSSubscriber(
        tts_client=tts_client,
        audio_player=audio_player,
        config=subscriber_config,
    )
    print("✓ TTS subscriber initialized")

    # Create a sample AgentOutput
    sample_output = AgentOutput(
        session_id="test_session_123",
        display_text="Hello, this is a test message for TTS synthesis.",
        spoken_text="Hello, this is a test message for TTS synthesis.",
        puppet=PuppetDirective(expression="happy", intensity=0.7),
        meta={"tts": "force"},  # Force TTS even if spoken_text is present
    )
    print(f"✓ Sample AgentOutput created: {sample_output.display_text}")

    # 1) Direct path (foreground): synthesize + play so errors aren't hidden in the worker thread
    print("\nSynthesizing (foreground)...")
    audio_bytes = tts_client.synthesize(sample_output.spoken_text)
    print(f"✓ Synthesized {len(audio_bytes)} bytes")

    print("Playing (foreground)...")
    try:
        audio_player.play(audio_bytes, ext="wav")
        print("✓ Playback finished")
    except Exception as exc:
        print(f"✗ Playback failed: {exc}")

    # 2) Subscriber path (background): still test the subscriber flow
    print("\nSending message to TTS subscriber (background)...")
    subscriber(sample_output)
    print("Waiting 3s for background worker...")
    time.sleep(3)

    print("✓ Test completed. If you didn't hear audio:")
    print("  - Check Windows volume/mute + output device")
    print("  - Look for temp wav files named vtuber_tts_*.wav in %TEMP%")
    print("  - Install ffmpeg (ffplay) and set prefer_ffplay=True")


if __name__ == "__main__":
    main()
