import queue
import threading
from dataclasses import dataclass
from typing import Any, Optional
from ..core.contracts import AgentOutput

@dataclass
class TTSConfig:
    enabled: bool = False
    interrupt: bool = True
    voice: Optional[str] = None

class TTSSubscriber:
    def __init__(self, tts_client, audio_player, config: Optional[TTSConfig] = None):
        self.tts_client = tts_client
        self.audio_player = audio_player
        self.config = config or TTSConfig()

        self._q: queue.Queue[tuple[str, str, dict[str, Any]]] = queue.Queue()
        self._lock = threading.RLock()
        self._stop = False

        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def set_enabled(self, on: bool) -> None:
        with self._lock:
            self.config.enabled = on

    def toggle(self) -> bool:
        with self._lock:
            self.config.enabled = not self.config.enabled
            return self.config.enabled

    def flush(self) -> None:
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        # optional: also stop current playback if your player supports it
        if hasattr(self.audio_player, "stop"):
            try:
                self.audio_player.stop()
            except Exception:
                pass

    def __call__(self, out: AgentOutput) -> None:
        # This is what you subscribe to OutputBus with.
        with self._lock:
            if not self.config.enabled:
                return
            interrupt = self.config.interrupt
            voice = self.config.voice

        meta = out.meta or {}
        if meta.get("tts") == "never":
            return

        text = (out.spoken_text or "").strip()
        if not text and meta.get("tts") == "force":
            text = (out.display_text or "").strip()
        if not text:
            return

        if interrupt:
            self.flush()

        # enqueue and return immediately (do not block OutputBus)
        self._q.put((out.session_id, text, {**meta, "voice": voice}))

    def _run(self) -> None:
        while not self._stop:
            session_id, text, meta = self._q.get()
            voice = meta.get("voice")

            audio_bytes = self.tts_client.synthesize(text, voice=voice)
            self.audio_player.play(audio_bytes)
