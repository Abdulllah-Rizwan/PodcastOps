"""Read-only functions — the LOGIC stage (Principle II): they decide and change nothing.

This package defines the declarative `FunctionDef`. The read-only execution registry (which hands
functions a `ReadOnlyStore` and nothing writable) is added in the US2 phase.
"""

from __future__ import annotations

from ontology_engine.functions.definitions import Decision, FunctionDef

__all__ = ["Decision", "FunctionDef"]
