from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Literal

EventType = Literal["USER_TEXT", "CAPTURE_REQUEST", "SCREEN_OCR", "TICK"]

## CORE

@dataclass(frozen=True)
class Event:
    type: EventType
    session_id: Optional[str] = None
    new_session: bool = False

    # payload (v1)
    text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PuppetDirective:
    expression: str = "idle"   # later: Enum
    intensity: float = 0.5     # 0..1
    beats: list[dict[str, Any]] = field(default_factory=list)

@dataclass(frozen=True)
class AgentOutput:
    session_id: str
    display_text: str
    spoken_text: str
    puppet: PuppetDirective = field(default_factory=PuppetDirective)
    meta: dict[str, Any] = field(default_factory=dict)

## TRANSPORT

@dataclass(frozen=True)
class RunOptions:
    new_session: bool = False
    session_id: Optional[str] = None
    user_input: str = ""
    context: bool = False


## PERSISTANCE

@dataclass(frozen=True)
class SessionMessage:
    role: str
    content: str
    meta: Optional[dict[str, Any]] = None
    
    def to_dict(self) -> dict[str, Any]:
        base = {
            "role": self.role,
            "content": self.content,
        }
        if self.meta is not None:
            base["meta"] = self.meta
        return base
    
## LLM

@dataclass
class InitialResponseJson:
    display_text: str
    spoken_text: str
    puppet: PuppetDirective
    meta: dict[str, Any] = field(default_factory=dict)
 
    def to_session_message(self) -> SessionMessage:
        return SessionMessage(
            role="assistant",
            content=self.display_text,
            meta={
                "spoken_text": self.spoken_text,
                "puppet": {
                    "expression": self.puppet.expression,
                    "intensity": self.puppet.intensity,
                    "beats": self.puppet.beats,
                },
                **self.meta,
            },
        )