"""Entity-resolution eval endpoints (US3, T050).

- `POST /evals/resolution/run?matcher=baseline|combined`  run the hermetic ER eval and store it
- `GET  /evals/resolution/latest`                         the most recent result (per matcher)

The golden set comes from the registered vertical's `golden_set_path` (the engine stays
domain-agnostic). `combined` uses `HashingEmbeddings` so the endpoint is deterministic and needs no
model download or network.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.state import AppContext, get_ctx
from ontology_engine.embeddings.provider import HashingEmbeddings
from ontology_engine.evals.golden import load_golden
from ontology_engine.evals.resolution import EvalThresholds, evaluate, write_report
from ontology_engine.resolve.baseline import BaselineMatcher
from ontology_engine.resolve.similarity import CombinedMatcher, SimilarityMatcher

router = APIRouter(tags=["evals"])


def _golden_path(ctx: AppContext) -> str:
    for vertical in ctx.registry.verticals:
        if vertical.golden_set_path:
            return vertical.golden_set_path
    raise HTTPException(status_code=404, detail="no golden set registered by any vertical")


def _matcher(kind: str):
    if kind == "baseline":
        return BaselineMatcher()
    if kind == "combined":
        return CombinedMatcher(BaselineMatcher(), SimilarityMatcher(HashingEmbeddings()))
    raise HTTPException(status_code=400, detail=f"unknown matcher {kind!r}")


@router.post("/evals/resolution/run")
def run_eval(
    matcher: str = Query("baseline", pattern="^(baseline|combined)$"),
    ctx: AppContext = Depends(get_ctx),
) -> dict[str, object]:
    try:
        cases = load_golden(_golden_path(ctx))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    result = evaluate(_matcher(matcher), cases)
    passed, reasons = result.gate(EvalThresholds())

    write_report(result, ctx.settings.run_dir / "evals" / f"resolution_{matcher}.json")
    ctx.evals[matcher] = result  # remember the latest per matcher

    body = result.model_dump(mode="json")
    body["gate"] = {"passed": passed, "reasons": reasons}
    return body


@router.get("/evals/resolution/latest")
def latest_eval(
    matcher: str = Query("baseline", pattern="^(baseline|combined)$"),
    ctx: AppContext = Depends(get_ctx),
) -> dict[str, object]:
    result = ctx.evals.get(matcher)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"no eval run yet for matcher {matcher!r}; POST .../run first"
        )
    passed, reasons = result.gate(EvalThresholds())
    body = result.model_dump(mode="json")
    body["gate"] = {"passed": passed, "reasons": reasons}
    return body
