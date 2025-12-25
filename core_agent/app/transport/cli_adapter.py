from __future__ import annotations

from ..core.contracts import Event
from ..runner import RunOptions

# Convert RunOptions to an Event
def run_options_to_event(opts: RunOptions) -> Event:
    return Event(
        type="USER_TEXT",
        session_id=opts.session_id,
        new_session=opts.new_session,
        text=opts.user_input,
        meta={"capture_context": bool(opts.context)},
    )
