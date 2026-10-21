"""Unit tests for the entity-resolution matcher (the hard core, Principle III)."""

from podcast_ops.resolve.matcher import Matcher, normalize_title


def test_normalize_strips_tags_and_episode_numbers():
    assert normalize_title("Space Travel 101 [Full Episode]") == "space travel 101"
    assert normalize_title("The Future of AI with Jane Doe") == "the future of ai with jane doe"
    assert normalize_title("My Show Ep. 12: Rockets!") == "my show rockets"


def test_matches_same_episode_despite_title_mismatch(youtube_records, spotify_records):
    # yt_b "Space Travel 101 [Full Episode]" should match sp_b "Space Travel 101".
    matches = Matcher().match(youtube_records, spotify_records)
    pairs = {
        (youtube_records[m.youtube_index].platform_id, spotify_records[m.spotify_index].platform_id)
        for m in matches
    }
    assert ("yt_a", "sp_a") in pairs
    assert ("yt_b", "sp_b") in pairs


def test_one_to_one_no_false_merge_no_fanout(youtube_records, spotify_records):
    matches = Matcher().match(youtube_records, spotify_records)
    # Exactly two true matches; yt_d and sp_c remain unmatched (one-sided).
    assert len(matches) == 2
    yt_used = [m.youtube_index for m in matches]
    sp_used = [m.spotify_index for m in matches]
    assert len(yt_used) == len(set(yt_used))  # no fan-out on YouTube side
    assert len(sp_used) == len(set(sp_used))  # no fan-out on Spotify side


def test_distinct_similar_titles_not_merged(youtube_records, spotify_records):
    # yt_a (3/1) and sp_b (3/8) are 7 days apart -> blocked -> never merged.
    matches = Matcher().match(youtube_records, spotify_records)
    wrong = {
        (youtube_records[m.youtube_index].platform_id, spotify_records[m.spotify_index].platform_id)
        for m in matches
    }
    assert ("yt_a", "sp_b") not in wrong
    assert ("yt_b", "sp_a") not in wrong
