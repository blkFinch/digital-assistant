"""FastMCP stdio entry point for the puppet controller."""

from __future__ import annotations

import json
import multiprocessing

from mcp.server.fastmcp import FastMCP

from .assets import AssetCatalog
from .config import load_settings
from .controller import PuppetController
from .models import PuppetState
from .tk_renderer import TkProcessRenderer


def create_server(controller: PuppetController) -> FastMCP:
    mcp = FastMCP("puppet-mcp", json_response=True)

    @mcp.tool()
    def set_expression(expression: str, intensity: float = 0.5) -> str:
        """Render an available expression and preserve its intensity in state."""
        return json.dumps(
            controller.set_expression(expression, intensity), indent=2
        )

    @mcp.tool()
    def get_current_state() -> str:
        """Return committed puppet state and renderer status."""
        return json.dumps(controller.get_current_state(), indent=2)

    @mcp.tool()
    def list_expressions() -> str:
        """List valid expressions for the configured puppet."""
        return json.dumps(controller.list_expressions(), indent=2)

    return mcp


def main() -> None:
    multiprocessing.freeze_support()
    settings = load_settings()
    catalog = AssetCatalog()
    renderer = TkProcessRenderer(
        window_title=settings.window_title,
        startup_timeout=settings.startup_timeout,
        command_timeout=settings.command_timeout,
    )
    controller = PuppetController(
        catalog,
        renderer,
        PuppetState(settings.puppet),
    )
    try:
        renderer.prepare()
        create_server(controller).run(transport="stdio")
    finally:
        controller.close()


if __name__ == "__main__":
    main()