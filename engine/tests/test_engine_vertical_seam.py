"""T059 — Engine/vertical seam guard (Principle I, SC-005).

The engine is domain-agnostic: it discovers a vertical *only* through the
registration mechanism (`OntologyRegistry.register(Vertical(...))`), never by
importing a vertical module. If any `engine/` module imported `verticals/` (or
the `vertical_podcast` package), podcast specifics would have leaked into the
engine and the "earned generality" discipline would be broken.

This test statically parses every engine source file with `ast` (so matches in
strings/comments don't trigger false positives) and asserts none of them import
a vertical package. It is fully hermetic — no imports of the code under test,
no I/O beyond reading source files.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Package-name prefixes that only ever live in a vertical, never in the engine.
FORBIDDEN_PREFIXES = ("verticals", "vertical_podcast")

ENGINE_SRC = Path(__file__).resolve().parent.parent / "src" / "ontology_engine"


def _engine_modules() -> list[Path]:
    files = sorted(ENGINE_SRC.rglob("*.py"))
    assert files, f"found no engine source files under {ENGINE_SRC}"
    return files


def _imported_names(tree: ast.AST) -> list[str]:
    """Every module name reached by an `import x` or `from x import ...` node."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # node.module is None for bare relative imports (`from . import x`);
            # those stay inside the engine package, so they are fine.
            if node.module is not None:
                names.append(node.module)
    return names


def _is_forbidden(module_name: str) -> bool:
    head = module_name.split(".", 1)[0]
    return head in FORBIDDEN_PREFIXES


def test_no_engine_module_imports_a_vertical() -> None:
    """SC-005: no `engine/` module imports `verticals/` / `vertical_podcast`."""
    offenders: list[str] = []
    for path in _engine_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_names(tree):
            if _is_forbidden(name):
                rel = path.relative_to(ENGINE_SRC.parent.parent)
                offenders.append(f"{rel} imports {name}")
    assert not offenders, "engine modules must not import a vertical:\n" + "\n".join(offenders)


def test_engine_has_no_podcast_specific_references() -> None:
    """A lighter guard: the podcast vertical's own package name does not appear
    anywhere in engine source (catches dynamic importlib use that the AST import
    scan above would miss). The generic word 'podcast' is allowed in docstrings
    and comments; we only forbid the importable package token."""
    offenders: list[str] = []
    for path in _engine_modules():
        text = path.read_text(encoding="utf-8")
        if "vertical_podcast" in text:
            rel = path.relative_to(ENGINE_SRC.parent.parent)
            offenders.append(str(rel))
    assert (
        not offenders
    ), "engine source must not reference the 'vertical_podcast' package:\n" + "\n".join(offenders)
