"""One-shot ingestion entrypoint for a Cloud Run Job (`python -m app.jobs`).

Cloud Run Jobs run a container to completion rather than serving HTTP, so the scheduled ingest uses
this instead of the arq worker (which needs a long-lived Redis connection). It runs the *same*
`execute_ingestion` callable as the API's `POST /ingest/run` and the arq worker, so there is one
ingest code path across all three (research decision #9). Triggered by Cloud Scheduler in prod; run
locally with the three packages on `PYTHONPATH` and `DATABASE_URL` set.
"""

from __future__ import annotations

import json
import logging

from app.ingestion import execute_ingestion
from app.main import build_context

logger = logging.getLogger("podcast_ops.jobs")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    ctx = build_context()
    logger.info(
        "starting one-shot ingestion (storage=%s)",
        "postgres" if ctx.settings.use_postgres else "json",
    )
    result = execute_ingestion(ctx.settings, ctx.registry, ctx.repo)
    logger.info("ingestion complete: %s", json.dumps(result.as_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
