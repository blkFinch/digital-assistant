import multiprocessing

from tests.spawn_helpers import fake_renderer_child


def test_real_spawn_ready_apply_shutdown_lifecycle() -> None:
    context = multiprocessing.get_context("spawn")
    commands = context.Queue()
    events = context.Queue()
    process = context.Process(
        target=fake_renderer_child,
        args=({"backend": "fake"}, commands, events),
        daemon=True,
    )
    process.start()
    try:
        assert events.get(timeout=5) == {"type": "ready", "backend": "fake"}
        commands.put({
            "type": "set_state",
            "request_id": "request-1",
            "state": {"puppet": "chibi", "expression": "happy", "intensity": 0.5},
        })
        applied = events.get(timeout=5)
        assert applied["type"] == "applied"
        assert applied["request_id"] == "request-1"
        commands.put({"type": "shutdown"})
        assert events.get(timeout=5) == {"type": "closed"}
        process.join(5)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5)
        commands.close()
        events.close()