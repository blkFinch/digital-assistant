#!/usr/bin/env python3
"""
Test script for ElevenLabs TTS components.

This script demonstrates:
- Creating a TTS subscriber with ElevenLabs client and audio player
- Sending a sample AgentOutput message
- Observing the TTS synthesis and playback flow

Run with: python -m core_agent.scripts.test_tts_elevenlabs
"""

import time
from core_agent.app.core.contracts import AgentOutput, PuppetDirective
from core_agent.app.tts.elevenlabs_client import ElevenLabsTTSSynthesizer, ElevenLabsTTSConfig
from core_agent.app.tts.audio_player import AudioPlayer, AudioPlayerConfig
from core_agent.app.tts.tts_subscriber import TTSSubscriber, TTSConfig
from core_agent.app.utils.logger import configure_logging


def main():
    configure_logging(debug=True)
    print("Setting up ElevenLabs TTS components...")

    # Configure ElevenLabs TTS
    tts_config = ElevenLabsTTSConfig(
        model_id="eleven_multilingual_v2",
        output_format="wav",
        stability=0.38,
        similarity_boost=0.8,
    )
    tts_client = ElevenLabsTTSSynthesizer(config=tts_config)
    print("✓ ElevenLabs TTS client initialized")

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
        display_text="Greetings! This is a test message synthesized with ElevenLabs.",
        spoken_text="Greetings! This is a test message synthesized with ElevenLabs.",
        puppet=PuppetDirective(expression="happy", intensity=0.7),
        meta={"tts": "force"},  # Force TTS even if spoken_text is present
    )
    print(f"✓ Sample AgentOutput created: {sample_output.display_text}")

    # Send message to TTS subscriber (background) to test with ElevenLabs
    print("\nSending message to ElevenLabs TTS subscriber (background)...")
    subscriber(sample_output)
    print("Waiting 5s for background worker (ElevenLabs synthesis + playback)...")
    time.sleep(5)

    print("✓ Test completed. If you didn't hear audio:")
    print("  - Verify ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are set in config.py")
    print("  - Check Windows volume/mute + output device")
    print("  - Look for temp wav files named vtuber_tts_*.wav in %TEMP%")
    print("  - Install ffmpeg (ffplay) and set prefer_ffplay=True")


if __name__ == "__main__":
    main()