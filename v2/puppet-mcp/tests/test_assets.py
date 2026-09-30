from pathlib import Path

import pytest

from puppet_mcp.assets import AssetCatalog

CHIBI = (
    "angry", "annoyed", "confused", "happy", "idle", "laugh", "sad",
    "smug", "surprised", "thinking",
)
SAKI = (
    "angry", "annoyed", "happy", "happy2", "idle", "laugh", "sad",
    "smug", "surprised", "thinking",
)


def test_bundled_catalog_has_exact_sorted_sets() -> None:
    catalog = AssetCatalog()
    assert catalog.list_puppets() == ("chibi", "saki")
    assert catalog.list_expressions("chibi") == CHIBI
    assert catalog.list_expressions("saki") == SAKI


@pytest.mark.parametrize("puppet,expressions", [("chibi", CHIBI), ("saki", SAKI)])
def test_packaged_png_resources_have_png_signatures(puppet, expressions) -> None:
    catalog = AssetCatalog()
    for expression in expressions:
        with catalog.resolve_png(puppet, expression).open("rb") as image:
            assert image.read(8) == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("name", ["missing", "../chibi", "chibi/idle", "."])
def test_unknown_and_traversal_puppets_are_rejected(name) -> None:
    with pytest.raises(ValueError):
        AssetCatalog().list_expressions(name)


@pytest.mark.parametrize("name", ["missing", "../idle", "happy.png", ""])
def test_unknown_and_traversal_expressions_are_rejected(name) -> None:
    with pytest.raises(ValueError):
        AssetCatalog().resolve_png("chibi", name)


def test_non_png_and_hidden_files_are_ignored(tmp_path: Path) -> None:
    puppet = tmp_path / "sample"
    puppet.mkdir()
    (puppet / "idle.png").write_bytes(b"png")
    (puppet / "notes.txt").write_text("ignore", encoding="utf-8")
    (puppet / ".secret.png").write_bytes(b"ignore")
    assert AssetCatalog(tmp_path).list_expressions("sample") == ("idle",)


def test_idle_is_required(tmp_path: Path) -> None:
    puppet = tmp_path / "sample"
    puppet.mkdir()
    (puppet / "happy.png").write_bytes(b"png")
    with pytest.raises(RuntimeError, match="idle.png"):
        AssetCatalog(tmp_path).list_puppets()