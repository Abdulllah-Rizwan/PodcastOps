"""Contract test for the YouTube read mapping (per contracts/youtube-read.md)."""

from datetime import date

from podcast_ops.ingest.youtube_gateway import map_video_item, parse_iso8601_duration


def test_duration_parsing():
    assert parse_iso8601_duration("PT1H") == 3600
    assert parse_iso8601_duration("PT45M") == 2700
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration(None) is None


def test_mapping_fields(youtube_items):
    rec = map_video_item(youtube_items[0])
    assert rec.platform == "youtube"
    assert rec.platform_id == "yt_a"
    assert rec.title == "The Future of AI with Jane Doe"
    assert rec.published_at == date(2024, 3, 1)
    assert rec.duration_seconds == 3600


def test_engagement_counts_are_integers(youtube_records):
    for rec in youtube_records:
        assert rec.engagement is not None
        assert isinstance(rec.engagement.views, int)
        assert isinstance(rec.engagement.likes, int)
        assert isinstance(rec.engagement.comments, int)
