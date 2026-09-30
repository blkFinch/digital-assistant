import inspect
import json
import sys

import pytest

from puppet_mcp import server as server_module
from puppet_mcp.server import create_server


class StubController:
    def set_expression(self, expression, intensity=0.5):
        if expression == "bad":
            raise ValueError("unknown expression")
        return {
            "puppet": "chibi",
            "expression": expression,
            "intensity": intensity,
            "renderer": {"backend": "tk", "status": "ready", "error": None},
        }

    def get_current_state(self):
        return {
            "puppet": "chibi", "expression": "idle", "intensity": 0.5,
            "renderer": {"backend": "tk", "status": "ready", "error": None},
        }

    def list_expressions(self):
        return {
            "puppet": "chibi", "default_expression": "idle",
            "expressions": ["happy", "idle"],
        }


def tools_by_name(server):
    return {tool.name: tool for tool in server._tool_manager.list_tools()}


def test_exactly_three_tools_and_default_signature() -> None:
    tools = tools_by_name(create_server(StubController()))
    assert set(tools) == {"set_expression", "get_current_state", "list_expressions"}
    signature = inspect.signature(tools["set_expression"].fn)
    assert signature.parameters["intensity"].default == 0.5


def test_tools_return_indented_json_shapes() -> None:
    tools = tools_by_name(create_server(StubController()))
    state_text = tools["set_expression"].fn("happy", 0.8)
    assert "\n  " in state_text
    state = json.loads(state_text)
    assert state["renderer"] == {"backend": "tk", "status": "ready", "error": None}
    assert json.loads(tools["get_current_state"].fn())["expression"] == "idle"
    assert json.loads(tools["list_expressions"].fn())["default_expression"] == "idle"


def test_controller_errors_propagate_as_tool_errors() -> None:
    tool = tools_by_name(create_server(StubController()))["set_expression"]
    with pytest.raises(ValueError, match="unknown expression"):
        tool.fn("bad")


def test_importing_server_does_not_import_tkinter_or_spawn(monkeypatch) -> None:
    assert "tkinter" not in sys.modules


def test_main_prepares_renderer_without_opening_window(monkeypatch) -> None:
    events = []

    class MainController:
        def start(self):
            events.append("start")

        def close(self):
            events.append("close")

    class MainServer:
        def run(self, transport):
            events.append(f"run:{transport}")

    class MainRenderer:
        def prepare(self):
            events.append("prepare")

    controller = MainController()
    renderer = MainRenderer()
    settings = type("Settings", (), {
        "window_title": "Puppet", "startup_timeout": 1.0,
        "command_timeout": 1.0, "puppet": "chibi",
    })()
    monkeypatch.setattr(server_module.multiprocessing, "freeze_support", lambda: None)
    monkeypatch.setattr(server_module, "load_settings", lambda: settings)
    monkeypatch.setattr(server_module, "AssetCatalog", lambda: object())
    monkeypatch.setattr(server_module, "TkProcessRenderer", lambda **kwargs: renderer)
    monkeypatch.setattr(server_module, "PuppetState", lambda puppet: object())
    monkeypatch.setattr(server_module, "PuppetController", lambda *args: controller)
    monkeypatch.setattr(server_module, "create_server", lambda value: MainServer())

    server_module.main()

    assert events == ["prepare", "run:stdio", "close"]