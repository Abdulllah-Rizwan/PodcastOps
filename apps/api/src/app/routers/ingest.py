"""Ingestion + access endpoints (US1, T033).

`POST /ingest/run` kicks off the pipeline and returns a job id; `GET /ingest/jobs/{id}` reports
status + counts; `GET /access/check` is the read-only Principle V gate per source. Locally the run
is synchronous (JSON backend, no queue); in cloud the arq worker / Cloud Run Job runs the same
`execute_ingestion` callable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.ingestion import execute_ingestion
from app.state import AppContext, get_ctx
from ontology_engine.access.check import run_access_checks

router = APIRouter(tags=["ingest"])


@router.post("/ingest/run")
def run_ingest(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    job = ctx.jobs.create()
    job.status = "running"
    try:
        result = execute_ingestion(ctx.settings, ctx.registry, ctx.repo)
        job.counts = {
            "staged": result.staged,
            "fused": result.fused,
            "single_source": result.single_source,
        }
        job.errors = result.errors
        job.status = "completed"
    except Exception as exc:  # noqa: BLE001 - report failure on the job, don't 500 the request
        job.status = "failed"
        job.errors = [str(exc)]
    return {"job_id": job.id, "status": job.status}


@router.get("/ingest/jobs/{job_id}")
def get_job(job_id: str, ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    job = ctx.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return job.as_dict()


@router.get("/access/check")
def access_check(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    results = run_access_checks(ctx.registry.source_adapters())
    return {
        "results": [r.model_dump(mode="json") for r in results],
        "all_passed": bool(results) and all(r.ok for r in results),
    }
