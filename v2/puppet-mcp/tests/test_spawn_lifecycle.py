from puppet_mcp.models import PuppetState
from puppet_mcp.tk_renderer import TkProcessRenderer
from tests.spawn_helpers import fake_renderer_child


def test_prepared_child_supports_lazy_apply_and_shutdown() -> None:
    renderer = TkProcessRenderer(
        startup_timeout=5,
        command_timeout=5,
        process_target=fake_renderer_child,
    )
    try:
        assert renderer.prepare().status == "stopped"
        assert renderer.get_status().status == "stopped"

        result = renderer.apply(PuppetState("chibi", "happy", 0.5))

        assert result.status == "ready"
    finally:
        renderer.close()
    assert renderer.get_status().status == "stopped"