"""EpisodeRepository — persists the fused Episode objects."""

from __future__ import annotations

import json
from pathlib import Path

from podcast_ops.objects.episode import Episode


class EpisodeRepository:
    def __init__(self, objects_dir: Path) -> None:
        self._dir = Path(objects_dir)
        self._path = self._dir / "episodes.json"

    @property
    def path(self) -> Path:
        return self._path

    def save(self, episodes: list[Episode]) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = [e.model_dump(mode="json") for e in episodes]
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self._path

    def load(self) -> list[Episode]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [Episode.model_validate(item) for item in data]
