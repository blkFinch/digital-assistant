from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .contracts import AgentOutput


Subscriber = Callable[[AgentOutput], None]

# Bus to set up observer pattern. AgentEngine will publish the output of conversation steps so
# other services can subscribe and consume the data (TTS, Animation, Chat etc..)

@dataclass
class OutputBus:
    _subs: List[Subscriber] = field(default_factory=list)
    latest: Optional[AgentOutput] = None

    def subscribe(self, fn: Subscriber) -> Callable[[], None]:
        self._subs.append(fn)

        def unsubscribe() -> None:
            try:
                self._subs.remove(fn)
            except ValueError:
                pass

        return unsubscribe

    def publish(self, output: AgentOutput) -> None:
        self.latest = output
        # best-effort delivery; isolate subscriber failures
        for fn in list(self._subs):
            try:
                fn(output)
            except Exception:
                # later: logger.exception(...)
                pass
