"""Build the configured Repository backend from Settings (Postgres if DATABASE_URL, else JSON)."""

from __future__ import annotations

from ontology_engine.config import Settings
from ontology_engine.store.repository import Repository


def build_repository(settings: Settings) -> Repository:
    """Return a Postgres repo when DATABASE_URL is set, otherwise the hermetic JSON repo."""
    if settings.use_postgres:
        from ontology_engine.store.postgres_repo import PostgresRepository

        return PostgresRepository(settings.database_url or "")

    from ontology_engine.store.json_repo import JsonRepository

    return JsonRepository(settings.store_dir)
