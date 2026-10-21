import json
from pathlib import Path

import pytest

from podcast_ops.ingest.spotify_gateway import map_episode
from podcast_ops.ingest.youtube_gateway import map_video_item

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def youtube_items():
    return json.loads((FIXTURES / "youtube_videos.json").read_text(encoding="utf-8"))


@pytest.fixture
def spotify_items():
    return json.loads((FIXTURES / "spotify_episodes.json").read_text(encoding="utf-8"))


@pytest.fixture
def youtube_records(youtube_items):
    return [map_video_item(i) for i in youtube_items]


@pytest.fixture
def spotify_records(spotify_items):
    return [map_episode(i) for i in spotify_items]
