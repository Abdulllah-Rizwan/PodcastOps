"""vertical_podcast — vertical #1 (podcast ops) as a plugin on the ontology engine.

Registers its object types (Show, Episode, Guest, Clip), typed links, source adapters (YouTube +
Apple Podcasts), and — in later phases — its read-only function and its writeback action. The
engine never imports this package; `registry.build_vertical()` plugs it in (Principle I).
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
