"""Podcast source adapters: YouTube (read + write) and Apple Podcasts (read, public)."""

from __future__ import annotations

from vertical_podcast.sources.apple_adapter import AppleAdapter
from vertical_podcast.sources.youtube_adapter import YouTubeAdapter

__all__ = ["AppleAdapter", "YouTubeAdapter"]
