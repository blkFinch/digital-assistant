"""Importable spawn targets used by headless lifecycle tests."""


def fake_renderer_child(config, command_queue, event_queue) -> None:
    event_queue.put({"type": "prepared"})
    while True:
        command = command_queue.get()
        if command["type"] == "shutdown":
            event_queue.put({"type": "closed"})
            return
        if command["type"] == "start":
            event_queue.put({"type": "ready"})
        if command["type"] == "set_state":
            event_queue.put(
                {
                    "type": "applied",
                    "request_id": command["request_id"],
                    "state": command["state"],
                }
            )