"""RawPlatformRecord — the staging-layer object.

An untransformed public-metadata record from one platform. It lives only in staging and is
never read by the logic or action stages (Principle II: raw is not an object).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Platform = Literal["youtube", "spotify"]


class Engagement(BaseModel):
    """Public engagement counts (YouTube only). Spotify exposes none."""

    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None


class RawPlatformRecord(BaseModel):
    """Raw record as pulled from a single platform. Treated as immutable once built."""

    model_config = {"frozen": True}

    platform: Platform
    platform_id: str
    title: str
    description: Optional[str] = None
    published_at: date
    duration_seconds: Optional[int] = None
    engagement: Optional[Engagement] = None
    raw: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
