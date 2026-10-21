"""Contract test for the Apple Podcasts read mapping (per contracts/apple-read.md)."""

from datetime import date

from podcast_ops.ingest.apple_gateway import map_episode


def test_mapping_fields(apple_items):
    rec = map_episode(apple_items[0])
    assert rec.platform == "apple"
    assert rec.platform_id == "ap_a"
    assert rec.title == "The Future of AI with Jane Doe"
    assert rec.published_at == date(2024, 3, 1)
    assert rec.duration_seconds == 3600


def test_engagement_is_null(apple_records):
    # Apple Podcasts exposes no public listen counts.
    for rec in apple_records:
        assert rec.engagement is None


def test_release_date_parses_iso_datetime():
    rec = map_episode(
        {
            "wrapperType": "podcastEpisode",
            "trackId": 42,
            "trackName": "Y",
            "releaseDate": "2021-07-04T00:00:00Z",
            "trackTimeMillis": None,
        }
    )
    assert rec.platform_id == "42"
    assert rec.published_at == date(2021, 7, 4)
    assert rec.duration_seconds is None
