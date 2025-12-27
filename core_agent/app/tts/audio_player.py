# audio_player.py
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioPlayerConfig:
    """
    Minimal, dependency-free audio playback.

    Strategy:
      1) Write audio bytes to a temp file (wav/mp3/ogg/etc).
      2) Play using an OS-native player where possible:
         - macOS: afplay (wav/mp3/aac/etc)
         - Linux: tries (paplay -> aplay -> ffplay)
         - Windows: tries (powershell SoundPlayer for wav) then ffplay for others
    """
    default_ext: str = "wav"          # "wav" is easiest cross-platform
    prefer_ffplay: bool = True       # if True, try ffplay first if available
    ffplay_path: str = "ffplay"       # override if ffplay isn't on PATH
    keep_temp_files: bool = False     # useful for debugging


class AudioPlayer:
    """
    Best-effort audio playback wrapper.

    - play(audio_bytes, ext="wav") starts playback.
    - stop() attempts to halt playback early (works when using subprocess-based players).
    """
    def __init__(self, config: Optional[AudioPlayerConfig] = None):
        self.config = config or AudioPlayerConfig()
        self._proc_lock = threading.RLock()
        self._proc: Optional[subprocess.Popen] = None
        self._last_tmp: Optional[str] = None

    def play(self, audio_bytes: bytes, *, ext: Optional[str] = None) -> None:
        """
        Play audio bytes. Blocks until playback completes for most backends.
        If you want non-blocking, call this from a worker thread (recommended).
        """
        ext = (ext or self.config.default_ext).lstrip(".").lower()

        # Stop any current playback first (barge-in).
        self.stop()

        tmp_path = self._write_temp(audio_bytes, ext)
        cmd = self._build_command(tmp_path, ext)

        if cmd is None:
            self._cleanup(tmp_path)
            raise RuntimeError(
                f"No available audio player backend found for ext={ext!r}. "
                f"Install ffmpeg (ffplay) or use wav on Windows."
            )

        logger.debug(f"Playing {len(audio_bytes)} bytes as .{ext} via: {cmd}")

        # Some backends aren't subprocesses (e.g., PowerShell SoundPlayer) but we still run them as subprocess.
        with self._proc_lock:
            self._last_tmp = tmp_path
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        # Wait for completion
        try:
            stdout, stderr = self._proc.communicate()
            if stderr:
                logger.warning(f"Audio playback stderr: {stderr.decode('utf-8', errors='replace')}")
        finally:
            with self._proc_lock:
                self._proc = None
            self._cleanup(tmp_path)

    def stop(self) -> None:
        """
        Attempt to stop current playback early.
        Works for subprocess-based players; may not stop instantly on all OS backends.
        """
        with self._proc_lock:
            proc = self._proc
            self._proc = None

        if not proc:
            return

        try:
            proc.terminate()
        except Exception:
            pass

        try:
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        # Don't delete temp file here; the play() call will clean it up when it unwinds.
        # (If play() isn't the caller anymore, keep_temp_files=False will still clean on next play.)

    def _write_temp(self, audio_bytes: bytes, ext: str) -> str:
        fd, path = tempfile.mkstemp(prefix="vtuber_tts_", suffix=f".{ext}")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return path

    def _cleanup(self, path: str) -> None:
        if self.config.keep_temp_files:
            return
        try:
            os.remove(path)
        except Exception:
            pass

    def _build_command(self, path: str, ext: str) -> Optional[list[str]]:
        """
        Return a subprocess command list for playing the file at path.
        """
        system = platform.system().lower()

        # Optional: prefer ffplay if available
        if self.config.prefer_ffplay and self._has_ffplay():
            return self._ffplay_cmd(path)

        if system == "darwin":
            # afplay supports many formats (wav, mp3, m4a, etc.)
            if shutil.which("afplay"):
                return ["afplay", path]
            if self._has_ffplay():
                return self._ffplay_cmd(path)
            return None

        if system == "linux":
            # Prefer PulseAudio's paplay for wav; aplay is ALSA wav; otherwise ffplay.
            if shutil.which("paplay") and ext in ("wav", "ogg"):
                return ["paplay", path]
            if shutil.which("aplay") and ext == "wav":
                return ["aplay", "-q", path]
            if self._has_ffplay():
                return self._ffplay_cmd(path)
            return None

        if system == "windows":
            # Windows: native easiest is wav via .NET SoundPlayer.
            # For mp3/other formats, recommend ffplay.
            if ext == "wav":
                # PowerShell: [System.Media.SoundPlayer] supports wav
                ps = (
                    "$p = New-Object System.Media.SoundPlayer '{}'; "
                    "$p.Load(); $p.PlaySync();"
                ).format(path.replace("'", "''"))
                if shutil.which("powershell"):
                    return ["powershell", "-NoProfile", "-Command", ps]
                if shutil.which("pwsh"):
                    return ["pwsh", "-NoProfile", "-Command", ps]
                # Fallback: ffplay if present
            if self._has_ffplay():
                return self._ffplay_cmd(path)
            return None

        # Unknown OS: last resort ffplay
        if self._has_ffplay():
            return self._ffplay_cmd(path)
        return None

    def _has_ffplay(self) -> bool:
        return shutil.which(self.config.ffplay_path) is not None

    def _ffplay_cmd(self, path: str) -> list[str]:
        # -nodisp: no video window
        # -autoexit: exit when done
        # -loglevel error: keep stderr quiet unless error
        return [self.config.ffplay_path, "-nodisp", "-autoexit", "-loglevel", "error", path]
