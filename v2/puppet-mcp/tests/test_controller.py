import pytest

from puppet_mcp.assets import AssetCatalog
from puppet_mcp.controller import PuppetController
from puppet_mcp.models import PuppetState, RendererStatus
from puppet_mcp.renderer import RendererUnavailableError


class FakeRenderer:
    def __init__(self, outcomes=None):
        self.status = RendererStatus("fake", "stopped")
        self.outcomes = list(outcomes or [])
        self.applied = []
        self.starts = []
        self.close_count = 0

    def start(self, state):
        self.starts.append(state)
        self.status = RendererStatus("fake", "ready")
        return self.status

    def apply(self, state):
        self.applied.append(state)
        outcome = self.outcomes.pop(0) if self.outcomes else self.status
        if callable(outcome):
            outcome = outcome(state)
        if isinstance(outcome, BaseException):
            raise outcome
        self.status = outcome
        return outcome

    def get_status(self):
        return self.status

    def close(self):
        self.close_count += 1
        self.status = RendererStatus("fake", "stopped")


def make_controller(renderer=None):
    renderer = renderer or FakeRenderer()
    controller = PuppetController(AssetCatalog(), renderer, PuppetState("chibi"))
    controller.start()
    return controller, renderer


def test_successful_apply_commits_acknowledged_state() -> None:
    controller, _ = make_controller()
    result = controller.set_expression(" HAPPY ", 0.8)
    assert result["expression"] == "happy"
    assert result["intensity"] == 0.8
    assert result["renderer"]["status"] == "ready"


def test_state_is_not_committed_until_apply_returns() -> None:
    holder = {}

    def observe_before_ack(_state):
        assert holder["controller"].get_current_state()["expression"] == "idle"
        return RendererStatus("fake", "ready")

    renderer = FakeRenderer([observe_before_ack])
    controller, _ = make_controller(renderer)
    holder["controller"] = controller
    controller.set_expression("happy")


@pytest.mark.parametrize("expression", ["", "missing", "../happy"])
def test_expression_errors_are_strict(expression) -> None:
    controller, renderer = make_controller()
    with pytest.raises(ValueError):
        controller.set_expression(expression)
    assert renderer.applied == []


def test_timeout_preserves_prior_state_without_restart() -> None:
    renderer = FakeRenderer([RuntimeError("timed out")])
    controller, _ = make_controller(renderer)
    with pytest.raises(RuntimeError, match="timed out"):
        controller.set_expression("happy")
    assert controller.get_current_state()["expression"] == "idle"
    assert len(renderer.starts) == 1


@pytest.mark.parametrize(
    "failure",
    [RendererUnavailableError("crashed"), RendererStatus("fake", "stopped")],
)
def test_closed_or_crashed_renderer_restarts_once(failure) -> None:
    renderer = FakeRenderer([failure, RendererStatus("fake", "ready")])
    controller, _ = make_controller(renderer)
    result = controller.set_expression("happy")
    assert result["expression"] == "happy"
    assert len(renderer.starts) == 2
    assert renderer.close_count == 1


def test_restart_has_one_retry_limit_and_preserves_state() -> None:
    renderer = FakeRenderer([
        RendererUnavailableError("crashed"),
        RendererUnavailableError("crashed again"),
    ])
    controller, _ = make_controller(renderer)
    with pytest.raises(RendererUnavailableError, match="again"):
        controller.set_expression("happy")
    assert controller.get_current_state()["expression"] == "idle"
    assert len(renderer.applied) == 2


def test_list_shape_and_idempotent_close() -> None:
    controller, renderer = make_controller()
    result = controller.list_expressions()
    assert result["puppet"] == "chibi"
    assert result["default_expression"] == "idle"
    assert result["expressions"] == sorted(result["expressions"])
    controller.close()
    controller.close()
    assert renderer.close_count == 1