"""Actions — the only path that mutates external state (Principle IV).

This module defines the declarative `ActionDef` and the `ActionAttempt` audit record (foundational
data model). The mock-first/idempotent/approval-gated Action *port* behavior is added in the US2
phase; this package holds the types the store and registry depend on.
"""

from __future__ import annotations

from ontology_engine.actions.attempt import ActionAttempt, ActionDef

__all__ = ["ActionAttempt", "ActionDef"]
