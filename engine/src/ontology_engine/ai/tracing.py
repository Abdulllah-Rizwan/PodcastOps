"""Tracing seam for AI calls (Principle VI: AI is traced).

The engine depends only on a tiny `Tracer` interface; the Langfuse SDK is imported lazily inside the
adapter, so importing this module never requires it. The no-op tracer still returns a real
`trace_id`, so a `GroundedAnswer` always carries one even when no backend is configured.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator
from uuid import uuid4


@dataclass
class Trace:
    """A single traced operation; `id` is surfaced on the agent's answer."""

    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "agent.ask"
    metadata: dict[str, Any] = field(default_factory=dict)


class NoopTracer:
    """Default tracer: generates a trace_id, records nothing externally."""

    @contextmanager
    def trace(self, name: str, **metadata: Any) -> Iterator[Trace]:
        yield Trace(name=name, metadata=metadata)


class LangfuseTracer:
    """Langfuse-backed tracer (lazy import). Falls back to no-op behavior if the SDK is absent."""

    def __init__(self, *, host: str, public_key: str, secret_key: str) -> None:
        self._host = host
        self._public_key = public_key
        self._secret_key = secret_key
        self._client = None

    def _get_client(self):  # pragma: no cover - requires the langfuse SDK + a live backend
        if self._client is None:
            from langfuse import Langfuse

            self._client = Langfuse(
                host=self._host, public_key=self._public_key, secret_key=self._secret_key
            )
        return self._client

    @contextmanager
    def trace(self, name: str, **metadata: Any) -> Iterator[Trace]:  # pragma: no cover - live
        trace = Trace(name=name, metadata=metadata)
        span = self._get_client().trace(id=trace.id, name=name, metadata=metadata)
        try:
            yield trace
        finally:
            try:
                span.update(output=metadata.get("output"))
            except Exception:  # noqa: BLE001 - tracing must never break the agent
                pass


def get_tracer(settings: Any | None = None) -> NoopTracer | LangfuseTracer:
    """Pick a tracer from settings: Langfuse if fully configured, else the no-op tracer."""
    if (
        settings is not None
        and settings.langfuse_host
        and settings.langfuse_public_key
        and (settings.langfuse_secret_key)
    ):
        return LangfuseTracer(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )
    return NoopTracer()
