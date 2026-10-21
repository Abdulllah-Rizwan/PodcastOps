"""Podcast Ops-Hub — validation slice.

One end-to-end spine of the data -> logic -> action pattern:
read (YouTube + Apple Podcasts) -> stage -> resolve/conform into Episode objects ->
one read-only decision rule -> one safe, logged, mock-first writeback.
"""

__version__ = "0.1.0"
