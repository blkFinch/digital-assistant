"""Discovery and strict resolution of bundled puppet assets."""

from __future__ import annotations

import re
from importlib.abc import Traversable
from importlib.resources import files
from pathlib import Path

_SAFE_NAME = re.compile(r"^[a-z0-9_-]+$")


def _normalize_name(value: str, kind: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{kind} must be a string")
    name = value.strip().lower()
    if not name or not _SAFE_NAME.fullmatch(name):
        raise ValueError(f"Invalid {kind} name: {value!r}")
    return name


class AssetCatalog:
    """Catalog PNG expressions from package resources or an injected root."""

    def __init__(self, root: Traversable | Path | None = None) -> None:
        self._root = root or files("puppet_mcp").joinpath("assets", "puppets")

    def list_puppets(self) -> tuple[str, ...]:
        puppets: list[str] = []
        for entry in self._root.iterdir():
            if entry.name.startswith(".") or not entry.is_dir():
                continue
            expressions = self._expressions_in(entry)
            if "idle" not in expressions:
                raise RuntimeError(f"Puppet '{entry.name}' is missing required idle.png")
            puppets.append(entry.name)
        return tuple(sorted(puppets))

    def list_expressions(self, puppet: str) -> tuple[str, ...]:
        name = _normalize_name(puppet, "puppet")
        if name not in self.list_puppets():
            raise ValueError(f"Unknown puppet '{name}'")
        return self._expressions_in(self._root.joinpath(name))

    def resolve_png(self, puppet: str, expression: str) -> Traversable:
        puppet_name = _normalize_name(puppet, "puppet")
        expression_name = _normalize_name(expression, "expression")
        expressions = self.list_expressions(puppet_name)
        if expression_name not in expressions:
            raise ValueError(
                f"Unknown expression '{expression_name}' for puppet '{puppet_name}'"
            )
        return self._root.joinpath(puppet_name, f"{expression_name}.png")

    @staticmethod
    def _expressions_in(directory: Traversable) -> tuple[str, ...]:
        names = [
            entry.name[:-4]
            for entry in directory.iterdir()
            if not entry.name.startswith(".")
            and entry.is_file()
            and entry.name.lower().endswith(".png")
        ]
        return tuple(sorted(names))