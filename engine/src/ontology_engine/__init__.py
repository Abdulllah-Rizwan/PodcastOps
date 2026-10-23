"""ontology_engine — a reusable, domain-agnostic ontology engine.

Implements the data → logic → action pattern: objects fused from sources we don't own
(resolved in a staging-first pipeline), read-only functions that decide, and typed,
validated, audited actions that change the world. A *vertical* (e.g. podcast ops) plugs
in by registering its object types, links, source adapters, functions, and actions through
`ontology_engine.ontology.registry`. No engine module imports a vertical module (Principle I).
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
