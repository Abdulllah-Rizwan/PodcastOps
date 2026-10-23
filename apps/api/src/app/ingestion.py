"""Shared ingestion entrypoint — the single callable used by both the API and the worker.

Keeping it here (not in a router) means the background worker (arq / Cloud Run Job) and the
`POST /ingest/run` endpoint run the exact same code path (research decision #9).
"""

from __future__ import annotations

from ontology_engine.config import Settings
from ontology_engine.ingest.pipeline import IngestionPipeline, IngestResult
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.repository import Repository
from vertical_podcast.registry import source_targets


def execute_ingestion(
    settings: Settings,
    registry: OntologyRegistry,
    repo: Repository,
    *,
    object_type_key: str = "episode",
) -> IngestResult:
    """Run the ingest → resolve → object pipeline for the registered vertical's sources."""
    pipeline = IngestionPipeline(registry, repo)
    return pipeline.run(source_targets(settings), object_type_key=object_type_key)
