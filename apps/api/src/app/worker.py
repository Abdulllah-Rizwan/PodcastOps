"""Background ingestion worker (T032).

Runs the SAME `execute_ingestion` callable as the API, on an arq worker over Redis locally and as a
Cloud Run Job (triggered by Cloud Scheduler) in cloud. arq/redis are imported lazily so the API
package imports without them; `WorkerSettings` is only referenced when a worker process starts.
"""

from __future__ import annotations

from app.ingestion import execute_ingestion
from app.main import build_context


async def ingest_task(ctx: dict) -> dict:  # pragma: no cover - requires a running worker
    """arq task: run one ingestion pass and return the counts."""
    app_ctx = ctx.get("app_ctx") or build_context()
    result = execute_ingestion(app_ctx.settings, app_ctx.registry, app_ctx.repo)
    return result.as_dict()


async def _startup(ctx: dict) -> None:  # pragma: no cover
    ctx["app_ctx"] = build_context()


class WorkerSettings:  # pragma: no cover - read by the arq CLI
    """`arq app.worker.WorkerSettings` — the worker entrypoint."""

    functions = [ingest_task]
    on_startup = _startup

    @staticmethod
    def redis_settings():
        from arq.connections import RedisSettings

        from ontology_engine.config import Settings

        url = Settings.from_env().redis_url or "redis://localhost:6379/0"
        return RedisSettings.from_dsn(url)
