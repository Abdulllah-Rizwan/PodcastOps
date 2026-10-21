"""StagingRepository — raw records land here first, kept separate from objects.

Persists RawPlatformRecords as JSON under run/staging/{platform}/. This is the inlet; the
resolver reads from here to build Episode objects (Principle II).
"""

from __future__ import annotations

import json
from pathlib import Path

from podcast_ops.ingest.records import Platform, RawPlatformRecord


class StagingRepository:
    def __init__(self, staging_dir: Path) -> None:
        self._dir = Path(staging_dir)

    def _platform_dir(self, platform: Platform) -> Path:
        d = self._dir / platform
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(self, platform: Platform, records: list[RawPlatformRecord]) -> Path:
        """Overwrite the staged set for a platform with `records`. Returns the file path."""
        d = self._platform_dir(platform)
        path = d / "records.json"
        payload = [r.model_dump(mode="json") for r in records]
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def load(self, platform: Platform) -> list[RawPlatformRecord]:
        path = self._dir / platform / "records.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [RawPlatformRecord.model_validate(item) for item in data]
