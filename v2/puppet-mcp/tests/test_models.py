import math

import pytest

from puppet_mcp.models import PuppetState, RendererStatus


def test_state_normalizes_and_serializes() -> None:
    state = PuppetState(" CHIBI ", " Happy ", 0.8)
    assert state.to_dict() == {
        "puppet": "chibi", "expression": "happy", "intensity": 0.8,
    }


def test_default_and_intensity_boundaries() -> None:
    assert PuppetState("chibi").intensity == 0.5
    assert PuppetState("chibi", intensity=0).intensity == 0.0
    assert PuppetState("chibi", intensity=1).intensity == 1.0


@pytest.mark.parametrize(
    "value", [True, False, -0.01, 1.01, math.nan, math.inf, -math.inf, "0.5"]
)
def test_invalid_intensity_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="intensity"):
        PuppetState("chibi", intensity=value)


def test_blank_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="puppet"):
        PuppetState("")
    with pytest.raises(ValueError, match="expression"):
        PuppetState("chibi", " ")


def test_renderer_status_serializes_null_error() -> None:
    status = RendererStatus("tk", "ready")
    assert status.to_dict() == {"backend": "tk", "status": "ready", "error": None}