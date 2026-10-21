"""Contract test for the Spotify read mapping (per contracts/spotify-read.md)."""

from datetime import date

from podcast_ops.ingest.spotify_gateway import map_episode


def test_mapping_fields(spotify_items):
    rec = map_episode(spotify_items[0])
    assert rec.platform == "spotify"
    assert rec.platform_id == "sp_a"
    assert rec.title == "The Future of AI with Jane Doe"
    assert rec.published_at == date(2024, 3, 1)
    assert rec.duration_seconds == 3600


def test_engagement_is_null(spotify_records):
    # Spotify exposes no public listen counts.
    for rec in spotify_records:
        assert rec.engagement is None


def test_release_date_precision_year():
    rec = map_episode(
        {"id": "x", "name": "Y", "release_date": "2021", "release_date_precision": "year"}
    )
    assert rec.published_at == date(2021, 1, 1)
