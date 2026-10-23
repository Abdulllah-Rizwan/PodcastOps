"""FastAPI entrypoint: load the engine, register the podcast vertical, mount routers.

The API is deliberately thin — it wires the engine to the registered vertical and serves HTTP; no
domain logic lives here (Principle I/VII). US1 adds the ingest + ontology-explorer routers; later
phases mount functions/actions (US2), evals (US3), and the agent (US4).
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.routers import ingest, ontology
from app.state import AppContext, JobStore, get_ctx
from ontology_engine.config import Settings
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.factory import build_repository
from vertical_podcast.registry import register as register_podcast

logger = logging.getLogger("podcast_ops.api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def build_context(settings: Settings | None = None) -> AppContext:
    """Wire the engine registry, the podcast vertical, and the configured store together."""
    settings = settings or Settings.from_env()
    registry = OntologyRegistry()
    register_podcast(registry, settings)
    repo = build_repository(settings)
    return AppContext(settings=settings, registry=registry, repo=repo, jobs=JobStore())


def create_app(settings: Settings | None = None) -> FastAPI:
    ctx = build_context(settings)

    app = FastAPI(
        title="Ontology Engine — Podcast Ops",
        version="0.1.0",
        description="Thin API over the ontology engine with the podcast vertical registered.",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.state.ctx = ctx

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN001
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    @app.get("/health", tags=["meta"])
    def health(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
        """Liveness + a summary of what is registered (proves the stack moves — M0)."""
        return {
            "status": "ok",
            "engine_version": "0.1.0",
            "storage": "postgres" if ctx.settings.use_postgres else "json",
            "verticals": [v.key for v in ctx.registry.verticals],
            "object_types": [ot.key for ot in ctx.registry.object_types()],
            "link_types": [lt.key for lt in ctx.registry.link_types()],
            "sources": [a.source_key for a in ctx.registry.source_adapters()],
        }

    app.include_router(ingest.router)
    app.include_router(ontology.router)

    logger.info(
        "registered verticals=%s object_types=%s sources=%s storage=%s",
        [v.key for v in ctx.registry.verticals],
        [ot.key for ot in ctx.registry.object_types()],
        [a.source_key for a in ctx.registry.source_adapters()],
        "postgres" if ctx.settings.use_postgres else "json",
    )
    return app


app = create_app()
