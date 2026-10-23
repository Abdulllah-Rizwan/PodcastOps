"""FastAPI entrypoint (T025): load the engine, register the podcast vertical, expose /health.

The API is deliberately thin — it wires the engine to the registered vertical and serves HTTP; no
domain logic lives here (Principle I/VII). US1–US4 routers are mounted in their phases.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request

from ontology_engine.config import Settings
from ontology_engine.ontology.registry import OntologyRegistry
from vertical_podcast.registry import register as register_podcast

logger = logging.getLogger("podcast_ops.api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def build_registry(settings: Settings) -> OntologyRegistry:
    """Create the engine registry and plug in the podcast vertical."""
    registry = OntologyRegistry()
    register_podcast(registry, settings)
    return registry


def create_app() -> FastAPI:
    settings = Settings.from_env()
    registry = build_registry(settings)

    app = FastAPI(
        title="Ontology Engine — Podcast Ops",
        version="0.1.0",
        description="Thin API over the ontology engine with the podcast vertical registered.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.registry = registry

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN001
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness + a summary of what is registered (proves the stack moves — M0)."""
        return {
            "status": "ok",
            "engine_version": "0.1.0",
            "storage": "postgres" if settings.use_postgres else "json",
            "verticals": [v.key for v in registry.verticals],
            "object_types": [ot.key for ot in registry.object_types()],
            "link_types": [lt.key for lt in registry.link_types()],
            "sources": [a.source_key for a in registry.source_adapters()],
        }

    logger.info(
        "registered verticals=%s object_types=%s sources=%s",
        [v.key for v in registry.verticals],
        [ot.key for ot in registry.object_types()],
        [a.source_key for a in registry.source_adapters()],
    )
    return app


app = create_app()
