from __future__ import annotations

from .contracts import Event, AgentOutput
from .output_bus import OutputBus
from ..runner import run_agent, RunOptions

def _sanitize_for_tts(text: str) -> str:
    # cheap MVP sanitizer; later: have LLM produce spoken_text explicitly
    # remove common emoji ranges + collapse whitespace
    import re
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

class AgentEngine:
    def __init__(self, *, output_bus: OutputBus | None = None) -> None:
        self.output_bus = output_bus or OutputBus()
        
    def handle_event(self, event: Event) -> AgentOutput:
        # MVP: only USER_TEXT supported; context flag comes via meta
        opts = RunOptions(
            new_session=event.new_session,
            session_id=event.session_id,
            user_input=event.text,
            context=bool(event.meta.get("capture_context", False)),
        )

        llm_response, session_id = run_agent(opts)
        display_text = llm_response.display_text

        out = AgentOutput(
            session_id=session_id or "unknown",
            display_text=display_text,
            spoken_text=_sanitize_for_tts(llm_response.spoken_text),
            puppet=llm_response.puppet,
            meta=llm_response.meta,
        )
        
        self.output_bus.publish(out)
        
        return out