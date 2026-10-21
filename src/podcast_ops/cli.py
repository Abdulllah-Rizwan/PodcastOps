"""Command-line entry point. Thin dispatcher over the per-stage command handlers."""

from __future__ import annotations

import argparse
import logging
import sys

from podcast_ops.config import Config


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _cmd_check_access(config: Config) -> int:
    from podcast_ops.access_check import run_all

    results = run_all(config)
    print("M0 access gate:")
    all_ok = True
    for r in results:
        mark = "OK " if r.ok else "XX "
        all_ok = all_ok and r.ok
        print(f"  [{mark}] {r.name}: {r.message}")
    if all_ok:
        print("Gate PASSED - modeling may proceed.")
        return 0
    print("Gate FAILED - resolve the above before modeling against real data (Principle V).")
    return 1


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    parser = argparse.ArgumentParser(prog="podcast-ops", description="Podcast Ops-Hub slice")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-access", help="M0: confirm API access for the one read and one write")
    sub.add_parser("auth", help="one-time OAuth consent to mint the YouTube write token")
    sub.add_parser("ingest", help="DATA: read both platforms into staging")
    sub.add_parser("fuse", help="DATA: resolve + conform staging into Episode objects")
    sub.add_parser("decide", help="LOGIC: apply the one read-only rule")
    p_act = sub.add_parser("act", help="ACTION: the one writeback (mock by default)")
    p_act.add_argument("--real", action="store_true", help="perform the real writeback")
    p_run = sub.add_parser("run", help="run the full spine end-to-end")
    p_run.add_argument("--real", action="store_true", help="use the real writeback")

    args = parser.parse_args(argv)
    config = Config.from_env()

    if args.command == "check-access":
        return _cmd_check_access(config)
    if args.command == "auth":
        from podcast_ops.commands.auth import run_auth

        return run_auth(config)
    if args.command == "ingest":
        from podcast_ops.commands.ingest import run_ingest

        run_ingest(config)
        return 0
    if args.command == "fuse":
        from podcast_ops.commands.fuse import run_fuse

        run_fuse(config)
        return 0
    if args.command == "decide":
        from podcast_ops.commands.decide import run_decide

        run_decide(config)
        return 0
    if args.command == "act":
        from podcast_ops.commands.act import run_act

        run_act(config, real=args.real)
        return 0
    if args.command == "run":
        from podcast_ops.commands.run import run_spine

        run_spine(config, real=args.real)
        return 0
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
