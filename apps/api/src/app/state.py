"""Application state: the wired engine + vertical + repo, and an in-memory job store.

`AppContext` is built once in `create_app` and attached to `app.state.ctx`; routers read it via the
`get_ctx` dependency. The job store tracks ingestion runs for the async job endpoints; locally the
run is synchronous, while in cloud the arq worker / Cloud Run Job drives the same pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from fastapi import Request

from ontology_engine.config import Settings
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.repository import Repository

if TYPE_CHECKING:
    from ontology_engine.actions.port import ActionHandler

JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class Job:
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    status: JobStatus = "queued"
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.id,
            "status": self.status,
            "counts": self.counts,
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self) -> Job:
        job = Job()
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)


@dataclass
class AppContext:
    settings: Settings
    registry: OntologyRegistry
    repo: Repository
    jobs: JobStore
    # Vertical-supplied action handlers, keyed by action key (the real writeback behavior).
    action_handlers: "dict[str, ActionHandler]" = field(default_factory=dict)
    # Latest ER eval result per matcher kind (populated by the evals endpoints).
    evals: dict[str, object] = field(default_factory=dict)


def get_ctx(request: Request) -> AppContext:
    """FastAPI dependency: the per-app wired context."""
    return request.app.state.ctx
