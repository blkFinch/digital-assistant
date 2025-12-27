from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from ..config import RESOURCES_DIR

import tkinter as tk
from PIL import Image, ImageTk


# --- config / paths -----------------------------------------------------------

@dataclass(frozen=True)
class PuppetPaths:
    base_dir: Path                 # .../app/resources/puppets/chibi
    default_emotion: str = "idle"  # filename stem

    def png_for(self, emotion: Optional[str]) -> Path:
        """Resolve emotion -> PNG path, falling back to default."""
        stem = (emotion or "").strip().lower()
        if not stem:
            stem = self.default_emotion

        candidate = self.base_dir / f"{stem}.png"
        if candidate.exists():
            return candidate

        return self.base_dir / f"{self.default_emotion}.png"


def default_puppet_dir(puppet_name: str = "chibi") -> Path:
    # core_agent/app/viewer/png_viewer.py -> core_agent/app -> core_agent/app/resources/puppets/{puppet_name}
    puppet_dir = RESOURCES_DIR / "puppets" / puppet_name
    if puppet_dir.exists():
        return puppet_dir
    return RESOURCES_DIR / "puppets" / "chibi"


# --- viewer ------------------------------------------------------------------

class PngViewer:
    """
    Lightweight Tkinter PNG viewer.
    Call `set_emotion("happy")` to swap sprites.
    """

    def __init__(self, *, root: tk.Tk, puppets: PuppetPaths, title: str = "AI Vtuber — PNG Viewer") -> None:
        self.root = root
        self.puppets = puppets

        self.root.title(title)
        self.root.resizable(False, False)

        self._label = tk.Label(self.root)
        self._label.pack()

        self._current_path: Optional[Path] = None
        self._photo: Optional[ImageTk.PhotoImage] = None  # keep reference alive

        # show default immediately
        self.set_emotion(self.puppets.default_emotion)

    def _load_photo(self, path: Path) -> ImageTk.PhotoImage:
        img = Image.open(path).convert("RGBA")
        return ImageTk.PhotoImage(img)

    def set_image_path(self, path: Path) -> None:
        path = path.resolve()
        if self._current_path == path:
            return

        if not path.exists():
            path = self.puppets.png_for(None)

        self._photo = self._load_photo(path)
        self._label.configure(image=self._photo)
        self._current_path = path

    def set_emotion(self, emotion: Optional[str]) -> None:
        self.set_image_path(self.puppets.png_for(emotion))


# --- manual run / dev test ----------------------------------------------------

def main() -> None:
    # Minimal manual test: opens the viewer and cycles emotions every 1s.
    puppets_dir = default_puppet_dir()
    puppets = PuppetPaths(base_dir=puppets_dir, default_emotion="idle")

    root = tk.Tk()
    viewer = PngViewer(root=root, puppets=puppets)

    emotions = [
        "idle", "happy", "thinking", "confused", "annoyed",
        "angry", "sad", "laugh", "smug", "surprised",
        None, "does_not_exist",  # should fall back to idle
    ]
    i = 0

    def tick() -> None:
        nonlocal i
        viewer.set_emotion(emotions[i % len(emotions)])
        i += 1
        root.after(1000, tick)

    root.after(500, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
