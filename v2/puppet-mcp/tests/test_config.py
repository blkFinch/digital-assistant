import pytest

from puppet_mcp.config import Settings, load_settings


def test_defaults_use_isolated_empty_environment() -> None:
    assert load_settings({}) == Settings()


@pytest.mark.parametrize("puppet", ["chibi", "saki", " SAKI "])
def test_both_puppet_choices(puppet) -> None:
    assert load_settings({"PUPPET_MCP_PUPPET": puppet}).puppet == puppet.strip().lower()


def test_title_and_timeouts_are_parsed() -> None:
    settings = load_settings({
        "PUPPET_MCP_WINDOW_TITLE": " My Puppet ",
        "PUPPET_MCP_STARTUP_TIMEOUT": "1.25",
        "PUPPET_MCP_COMMAND_TIMEOUT": "0.1",
    })
    assert settings.window_title == "My Puppet"
    assert settings.startup_timeout == 1.25
    assert settings.command_timeout == 0.1


@pytest.mark.parametrize("value", ["", "unknown", "../chibi"])
def test_unknown_puppet_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="PUPPET_MCP_PUPPET"):
        load_settings({"PUPPET_MCP_PUPPET": value})


@pytest.mark.parametrize("value", ["", " "])
def test_blank_title_is_rejected(value) -> None:
    with pytest.raises(ValueError, match="WINDOW_TITLE"):
        load_settings({"PUPPET_MCP_WINDOW_TITLE": value})


@pytest.mark.parametrize("value", ["bad", "0", "-1", "nan", "inf", "-inf"])
@pytest.mark.parametrize(
    "variable", ["PUPPET_MCP_STARTUP_TIMEOUT", "PUPPET_MCP_COMMAND_TIMEOUT"]
)
def test_malformed_timeouts_are_rejected(variable, value) -> None:
    with pytest.raises(ValueError, match=variable):
        load_settings({variable: value})