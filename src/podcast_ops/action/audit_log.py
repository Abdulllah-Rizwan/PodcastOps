"""Audit logging for the action stage.

Every writeback attempt (mock or real, success or failure) is appended here as one JSON line
(Principle IV: the action is logged).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from podcast_ops.action.writeback import WritebackAttempt

logger = logging.getLogger("podcast_ops.action")


class AuditLog:
    """Append-only JSON-lines log of writeback attempts."""

    def __init__(self, action_dir: Path) -> None:
        self._dir = Path(action_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "audit.log"

    @property
    def path(self) -> Path:
        return self._path

    def record(self, attempt: "WritebackAttempt") -> None:
        line = attempt.model_dump_json()
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        logger.info("writeback attempt: %s", line)

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        out: list[dict] = []
        for raw in self._path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                out.append(json.loads(raw))
        return out
