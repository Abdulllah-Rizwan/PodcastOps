"""`run` command: orchestrate the full data -> logic -> action spine."""

from __future__ import annotations

from podcast_ops.commands.act import run_act
from podcast_ops.commands.decide import run_decide
from podcast_ops.commands.fuse import run_fuse
from podcast_ops.commands.ingest import run_ingest
from podcast_ops.config import Config


def run_spine(config: Config, *, real: bool = False) -> None:
    print("== DATA: ingest ==")
    run_ingest(config)
    print("== DATA: fuse ==")
    run_fuse(config)
    print("== LOGIC: decide ==")
    run_decide(config)
    print("== ACTION: act ==")
    run_act(config, real=real)
    print("== spine complete ==")
