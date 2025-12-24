from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

import mss
from PIL import Image
import numpy as np
import easyocr


@dataclass
class ScreenContext:
    text: str
    created_at: str  # ISO timestamp
    source: str      # e.g. "monitor:1"


def _clean_lines(lines: Sequence[str]) -> str:
    # strip, drop noise, normalize spaces
    cleaned = []
    for ln in lines:
        ln = ln.strip()
        if len(ln) < 3:
            continue
        cleaned.append(ln)
    text = "\n".join(cleaned)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def capture_screen(monitor_index: int = 1) -> Image.Image:
    """Capture a full monitor screenshot using mss."""
    with mss.mss() as sct:
        mon = sct.monitors[monitor_index]  # 1 = primary monitor in mss
        shot = sct.grab(mon)
        return Image.frombytes("RGB", shot.size, shot.rgb)


class EasyOcrEngine:
    """
    Wrap EasyOCR Reader so we initialize it once and reuse it.
    Reader init is expensive; don't recreate per request.
    """

    def __init__(self, languages: list[str] | None = None, gpu: bool = True):
        self.languages = languages or ["en"]
        self.reader = easyocr.Reader(self.languages, gpu=gpu)

    def image_to_text(self, img: Image.Image) -> str:
        # EasyOCR wants a numpy array (RGB is fine)
        arr = np.array(img)

        # detail=0 returns only text strings
        # paragraph=True groups nearby text (usually nicer for UI screenshots)
        lines = self.reader.readtext(arr, detail=0, paragraph=True)

        # lines might be strings or lists depending on EasyOCR version;
        # normalize to list[str]
        normalized: list[str] = []
        for item in lines:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, (list, tuple)):
                normalized.extend([str(x) for x in item])
            else:
                normalized.append(str(item))

        return _clean_lines(normalized)


def capture_and_ocr(engine: EasyOcrEngine, monitor_index: int = 1) -> ScreenContext:
    img = capture_screen(monitor_index=monitor_index)
    text = engine.image_to_text(img)
    ts = datetime.now(timezone.utc).isoformat()
    return ScreenContext(text=text, created_at=ts, source=f"monitor:{monitor_index}")


if __name__ == "__main__":
    # Quick local test
    engine = EasyOcrEngine(languages=["en"], gpu=True)
    ctx = capture_and_ocr(engine)
    print(ctx.created_at, ctx.source)
    print(ctx.text[:2000])
