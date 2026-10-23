"""Wire the podcast vertical into the engine (Principle I: the engine's only entry point).

`build_vertical(settings)` constructs the podcast `Vertical` — object types, links, and source
adapters (its read-only function and writeback action are added in later phases). `register(...)`
plugs it into an engine `OntologyRegistry`. The engine imports nothing from here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ontology_engine.ontology.registry import OntologyRegistry, Vertical
from vertical_podcast.objects import LINK_TYPES, OBJECT_TYPES
from vertical_podcast.sources import AppleAdapter, YouTubeAdapter

if TYPE_CHECKING:
    from ontology_engine.config import Settings

VERTICAL_KEY = "podcast"

# Golden set lives alongside the vertical (199 real matched pairs + hard negatives, seeded in US3).
GOLDEN_SET_PATH = str(Path(__file__).resolve().parents[2] / "evals" / "golden")


def build_vertical(settings: "Settings | None" = None) -> Vertical:
    """Build the podcast Vertical. Adapter credentials come from settings when provided."""
    if settings is not None:
        youtube = YouTubeAdapter(
            api_key=settings.youtube_api_key,
            oauth_token_path=settings.youtube_oauth_token,
            test_channel_id=settings.test_channel_id,
            test_video_id=settings.test_video_id,
        )
        apple = AppleAdapter()
    else:
        youtube = YouTubeAdapter()
        apple = AppleAdapter()

    return Vertical(
        key=VERTICAL_KEY,
        object_types=list(OBJECT_TYPES),
        link_types=list(LINK_TYPES),
        source_adapters=[youtube, apple],
        function_defs=[],  # apple_without_youtube — added in the US2 phase
        action_defs=[],  # youtube_update_show_notes — added in the US2 phase
        ui_config={
            "primary_object_type": "episode",
            "views": ["explorer", "ops", "evals", "agent"],
        },
        golden_set_path=GOLDEN_SET_PATH,
    )


def register(registry: OntologyRegistry, settings: "Settings | None" = None) -> Vertical:
    """Register the podcast vertical with an engine registry and return it."""
    vertical = build_vertical(settings)
    registry.register(vertical)
    return vertical


def source_targets(settings: "Settings") -> dict[str, object]:
    """Map each podcast source to the configured show id (keeps podcast ids out of the engine)."""
    return {
        "youtube": settings.target_youtube_source,
        "apple": settings.target_apple_show,
    }
