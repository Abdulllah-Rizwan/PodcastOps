"""EmbeddingProvider port + two adapters, selected by config.

Heavy/optional SDKs (voyageai, sentence-transformers) are imported lazily inside each adapter,
so importing the engine never requires them. The ER eval uses `LocalEmbeddings` for hermetic CI.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into vectors; one adapter per provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def model_id(self) -> str:
        ...


_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbeddings:
    """Deterministic, dependency-free embeddings via word + char-trigram feature hashing.

    Not semantic — it captures lexical overlap — but it is pure Python, needs no model download or
    network, and is fully reproducible, which makes it the right choice for the **hermetic** ER eval
    and its CI gate. Production uses `VoyageEmbeddings` (or `LocalEmbeddings`) for real semantics.
    """

    def __init__(self, *, dim: int = 256) -> None:
        self._dim = dim

    def _features(self, text: str) -> list[str]:
        tokens = _TOKEN.findall(text.lower())
        feats = list(tokens)
        joined = " ".join(tokens)
        for i in range(len(joined) - 2):  # char trigrams for sub-word overlap
            feats.append(f"#{joined[i : i + 3]}")
        return feats

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for feat in self._features(text):
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 8) & 1 else -1.0  # signed hashing reduces collisions
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def model_id(self) -> str:
        return f"hashing:char3-{self._dim}"


class VoyageEmbeddings:
    """Hosted embeddings via Voyage AI (default in cloud). Requires a VOYAGE_API_KEY."""

    def __init__(self, *, api_key: str, model: str = "voyage-3") -> None:
        if not api_key:
            raise ValueError("VOYAGE_API_KEY is required for VoyageEmbeddings")
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):  # pragma: no cover - live transport
        if self._client is None:
            import voyageai  # lazy

            self._client = voyageai.Client(api_key=self._api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - live
        result = self._get_client().embed(texts, model=self._model)
        return [list(v) for v in result.embeddings]

    def model_id(self) -> str:
        return f"voyage:{self._model}"


class LocalEmbeddings:
    """Local embeddings via sentence-transformers (offline/dev + hermetic CI)."""

    def __init__(self, *, model: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model
        self._model = None

    def _get_model(self):  # pragma: no cover - heavy optional dep
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # lazy

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - heavy dep
        vectors = self._get_model().encode(list(texts), normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]

    def model_id(self) -> str:
        return f"local:{self._model_name}"


def get_provider(
    kind: str,
    *,
    voyage_api_key: str | None = None,
    voyage_model: str = "voyage-3",
    local_model: str = "all-MiniLM-L6-v2",
) -> EmbeddingProvider:
    """Factory: choose the provider by config string ("voyage" | "local" | "hashing")."""
    if kind == "voyage":
        return VoyageEmbeddings(api_key=voyage_api_key or "", model=voyage_model)
    if kind == "local":
        return LocalEmbeddings(model=local_model)
    if kind == "hashing":
        return HashingEmbeddings()
    raise ValueError(
        f"unknown embedding provider {kind!r} (expected 'voyage', 'local', or 'hashing')"
    )
