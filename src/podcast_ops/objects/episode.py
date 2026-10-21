"""Episode — the fused, conformed object.

One Episode per real-world episode. It unites the matching YouTube and Apple Podcasts identities
and records which platforms it is present on / missing from. Produced only by the resolver.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, model_validator

from podcast_ops.ingest.records import Engagement, Platform

ALL_PLATFORMS: set[Platform] = {"youtube", "apple"}


class PlatformRef(BaseModel):
    """A reference to one platform's identity for an episode."""

    platform: Platform
    platform_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    engagement: Optional[Engagement] = None


class Episode(BaseModel):
    """The clean, fused result. See data-model.md for field-level rules."""

    episode_id: str
    title: str
    published_at: date
    duration_seconds: Optional[int] = None
    youtube: Optional[PlatformRef] = None
    apple: Optional[PlatformRef] = None
    present_on: list[Platform]
    missing_from: list[Platform]
    match_confidence: Optional[float] = None

    @model_validator(mode="after")
    def _check_invariants(self) -> "Episode":
        # "At least one of youtube/apple MUST be set."
        if self.youtube is None and self.apple is None:
            raise ValueError("Episode must have at least one platform reference")

        # "present_on + missing_from MUST together equal {youtube, apple} with no overlap."
        present = set(self.present_on)
        missing = set(self.missing_from)
        if present & missing:
            raise ValueError("present_on and missing_from must not overlap")
        if present | missing != ALL_PLATFORMS:
            raise ValueError("present_on + missing_from must cover exactly {youtube, apple}")

        # present_on must agree with which refs are set.
        refs_present = {p for p, ref in (("youtube", self.youtube), ("apple", self.apple)) if ref}
        if refs_present != present:
            raise ValueError("present_on must match the platform refs that are set")

        # "A two-sided Episode MUST carry exactly one YouTube ref and one Apple ref."
        if present == ALL_PLATFORMS and not (self.youtube and self.apple):
            raise ValueError("two-sided Episode must carry both a YouTube and an Apple ref")
        return self

    @property
    def is_two_sided(self) -> bool:
        return self.youtube is not None and self.apple is not None
