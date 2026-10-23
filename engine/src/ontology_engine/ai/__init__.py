"""AI layer: grounded retrieval tools, the propose-only agent, and tracing (Principle VI).

The agent reads the world only through the ontology (objects, links, functions) and changes it only
by *proposing* validated actions a human approves — it never calls the Action port's `execute`. The
heavy `anthropic` SDK is imported lazily inside the agent, so importing this package never requires
it (Principle VII); the retrieval tools and proposal validation are pure Python and fully hermetic.
"""
