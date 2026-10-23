"""EmbeddingProvider port + adapters (Voyage hosted, local offline/CI) and the stored record.

Anthropic offers no embeddings endpoint, so embeddings are an isolated dependency behind a port
(Principle VII). The local adapter keeps the ER eval hermetic and free in CI.
"""

from __future__ import annotations

from ontology_engine.embeddings.provider import (
    EmbeddingProvider,
    HashingEmbeddings,
    LocalEmbeddings,
    VoyageEmbeddings,
    get_provider,
)
from ontology_engine.embeddings.record import EmbeddingRecord

__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddings",
    "LocalEmbeddings",
    "VoyageEmbeddings",
    "get_provider",
    "EmbeddingRecord",
]
