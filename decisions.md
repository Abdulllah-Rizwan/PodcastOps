# Decisions Log — Podcast Ops-Hub

**Purpose**: Record every decision that *departs from the agreed plan* — what was planned,
what we did instead, and why. This is the deviation log, not a general design doc. If work
followed the plan, it does **not** belong here (put status in `progress.md` instead).

**How to use (one entry per deviation)**:
- Add a new dated entry at the top of the log (newest first).
- State the original plan, the new decision, the reason the original was abandoned, and the
  impact on scope / milestones / the constitution.
- If a decision touches scope, confirm it still respects the constitution's hard boundaries
  (`.specify/memory/constitution.md`). A scope-widening decision must be named and justified.

**Entry template**:

```
## YYYY-MM-DD — <short title>

- **Original plan**: <what the spec/plan/constitution said we would do>
- **Decision taken instead**: <what we are doing now>
- **Why the original was abandoned**: <reason — blocker, new info, API limit, etc.>
- **Impact**: <scope / milestones / constitution / spec — and any follow-up needed>
- **Links**: <spec FR ids, milestone, files affected>
```

---

## Log

## 2026-10-23 — Hermetic ER eval: deterministic `HashingEmbeddings` + a real golden set with curated hard negatives (US3)

- **Decision**: make the entity-resolution eval and its CI gate fully hermetic by (a) adding a
  deterministic, dependency-free `HashingEmbeddings` provider (word + char-trigram signed feature
  hashing, L2-normalized) used by the similarity/combined matchers in eval + CI, and (b) seeding the
  golden set from the **199 real matched pairs** of the 2026-10-21 live run plus **116 curated hard
  negatives** (each a YouTube record paired with a *different* episode's Apple record whose title is
  similar but whose release date is far apart).
- **Why**:
  - The plan says the eval runs on `LocalEmbeddings`, but `sentence-transformers` pulls a ~90 MB
    model over the network on first use — neither hermetic nor fast nor reproducible in CI. The eval
    must gate every change (Principle VI), so it has to run offline and deterministically.
    `HashingEmbeddings` is lexical, not semantic, but it is pure Python and reproducible; `Voyage`/
    `Local` remain the production providers for real semantics. The eval harness is matcher-agnostic,
    so swapping in a real provider later needs no harness change.
  - Hard negatives must be *separable by the multi-signal baseline* yet *fool a naive title-only
    matcher*: title-similar + date-far pairs score low on the baseline (date signal → 0) but high on
    title alone. On the committed set the baseline scores **P = 1.000 / R = 1.000** (315 cases), so
    the gate (precision ≥ 95%, recall ≥ 90%) passes, and widening the date tolerance / lowering the
    threshold / dropping a signal reintroduces false positives → the gate fails.
  - The real data has no title-identical, date-far different episodes (those would be false positives
    for the baseline by construction), so the "detect a weakened matcher as a regression" assertion
    (T045) lives in a **tiny controlled fixture** inside the test, not the real golden set, which is
    reserved for the CI gate (T049).
- **Impact**: `HashingEmbeddings` + `get_provider("hashing")`; `resolve/similarity.py`
  (`SimilarityMatcher`, `CombinedMatcher` — baseline stays runnable alone per Principle III);
  `evals/golden.py` (`GoldenCase` loader), `evals/resolution.py` (harness + gate),
  `evals/run_gate.py` (CI entry); `verticals/podcast/evals/golden/cases.jsonl` (315 cases, public
  podcast metadata only — no secrets); CI `eval-gate` job; `/evals/resolution/*` API + `app/evals` UI.
- **Links**: constitution Principle III/VI, SC-002/SC-007; `.github/workflows/ci.yml`;
  `engine/tests/test_resolution_eval.py`; `verticals/podcast/tests/test_golden_gate.py`.

## 2026-10-23 — Keep the slice (`src/podcast_ops/`) alongside the new engine during M0

- **Original plan**: `plan.md` (Structure Decision) says "the existing `src/podcast_ops/` is
  **migrated**: its generic pieces become the `engine/` package; its podcast-specific pieces become
  the `verticals/podcast/` plugin" — implying the old `src/` is moved/removed.
- **Decision taken instead**: For the M0 skeleton (Phases 1–2), **copy-and-generalize** the proven
  slice modules into `engine/` + `verticals/podcast/` while **leaving `src/podcast_ops/` in place**.
  The old package and its CLI remain runnable. `src/` is retired only once the engine reaches
  end-to-end parity for vertical #1 (through US1–US3), at which point the duplicate is deleted.
- **Why the original was abandoned**: Constitution Principle I requires vertical #1 to "remain
  working end-to-end at all times." The new engine cannot yet run end-to-end (no ingest pipeline,
  functions, or action port until US1–US2), so deleting `src/` during M0 would break the working
  spine with nothing to replace it. "A working spine always wins over a half-finished layer."
- **Impact**:
  - **Scope/constitution**: none widened; this is strictly *safer* and honors Principle I. The
    engine/vertical seam is still clean (no engine module imports a vertical; verified by a smoke
    test and formalized later by T059).
  - **Cost**: temporary code duplication between `src/podcast_ops/` and the new packages until the
    retirement step. Accepted as the price of never breaking the spine.
  - **Follow-up**: delete `src/podcast_ops/` (and fold its CLI into the new stack or drop it) when
    US1–US3 land; note that retirement in `progress.md` and here.
- **Links**: `plan.md` Structure Decision; `engine/`, `verticals/podcast/` (new); `src/podcast_ops/`
  (retained); `002` tasks T001–T026 (M0 skeleton); Principle I.

## 2026-10-23 — Pivot: narrow validation slice → reusable AI-native ontology engine

- **Original plan**: A deliberately **narrow, throwaway validation slice** whose only goal was to
  prove the data → logic → action spine *once* on real data. The constitution (v1.1.0) explicitly
  forbade a **general/reusable ontology engine**, any **ML**, a **multi-platform product**, and
  productization; success was defined as "the spine runs end-to-end on real data, once," after
  which we **stop**.
- **Decision taken instead**: With the slice **complete and proven** (live end-to-end run on
  2026-10-21, commit `bcc5502`), build the real thing it was a proof-of-concept for: a **reusable,
  AI-native ontology engine** (objects, typed links, read-only functions, validated actions),
  **proven by verticals**. The podcast operation becomes **vertical #1** (the live demo); a second,
  different vertical later (M5) is the **generality proof**. This is a **full-stack** build: web UI
  (ontology explorer + ops dashboard + AI agent), API backend (FastAPI over the existing Python
  core), Postgres + **pgvector**, a background worker, an **AI layer grounded in the ontology**,
  an **eval + observability** harness, and **cloud deployment** with CI/CD.
- **Why the original was abandoned**: Not a blocker — a deliberate, owner-chosen change of ambition.
  The slice succeeded, and the owner decided the valuable, market-relevant asset is the **engine /
  ontology pattern itself** (the Palantir-style objects → functions → actions model, now compelling
  because LLM agents are far more reliable when grounded in a typed ontology), not a single podcast
  app. Learning-by-building and showcasing full-stack + AI-engineering expertise are explicit goals;
  a usable tool and possible product are secondary.
- **Impact**:
  - **Scope**: materially widened. Three former hard boundaries are **reversed** — the bans on a
    general/reusable engine, on ML/AI, and on productization / "runs once." Guarded by a new
    discipline: **generality is earned by a second vertical, never asserted ahead of need** (YAGNI
    applied to generality); the engine must be built vertical-shaped first with clean seams, and
    must not grow abstractions no current vertical uses.
  - **Constitution**: amended **1.1.0 → 2.0.0** (MAJOR). Added principles: *Engine First, Proven by
    Verticals* and *AI Grounded in the Ontology, and Evaluated*. Retained (some generalized): the
    data → logic → action stage separation, *entity resolution is the hard core*, *safe/logged/
    mock-first actions* (now typed/idempotent/audited + human-in-the-loop for AI-proposed mutations),
    *confirm access before modeling*, and *high code quality* (extended full-stack). See the Sync
    Impact Report at the top of the constitution.
  - **What survives from the slice**: the proven Python core (ingest gateways, staging, matcher,
    `Episode` objects, decision rule, writeback seam + audit log) becomes the seed of the engine;
    the 199 real matched pairs from the live run seed the entity-resolution golden eval set.
  - **Milestones**: re-baselined to M0 full-stack skeleton → M1 generalized ontology core → M2
    vector-based entity resolution + evals → M3 AI agent over the ontology → M4 harden/deploy → M5
    vertical #2 (generality proof). The old slice milestones (M0–M3) are satisfied and folded in.
  - **Follow-up**: `CLAUDE.md` rewritten to the engine direction (done, 2026-10-23); a fresh Spec
    Kit cycle (`/speckit-specify` → `plan` → `tasks`) must define the new full-stack scope before
    implementation.
- **Links**: constitution v2.0.0 (`.specify/memory/constitution.md`), Principles I & VI new;
  `CLAUDE.md` (rewritten); `progress.md` (slice-complete history); the completed slice at commit
  `bcc5502`.

---

## 2026-10-21 — Second read platform: Spotify → Apple Podcasts

- **Original plan**: Read the one show from **YouTube + Spotify**; Spotify read via the Web API
  with a Client-Credentials (app-only) token (constitution Principle V, Scope Boundaries; spec
  SC/FRs; `contracts/spotify-read.md`).
- **Decision taken instead**: Replace Spotify with **Apple Podcasts**, read via the public
  **iTunes lookup API** (`GET https://itunes.apple.com/lookup?id=<collectionId>&entity=podcastEpisode`),
  which needs **no authentication, no market, and no subscription**. The one rule becomes
  `apple_without_youtube` ("on Apple Podcasts, no YouTube clip yet").
- **Why the original was abandoned**: Spotify's Web API refused **every** catalog request for the
  operator's app — not just podcasts, but music and search too — with HTTP 403:
  *"Active premium subscription required for the owner of the app."* The account that owns the
  Spotify developer app is not Premium (a gate Spotify applies in some markets, incl. the
  operator's). Verified it was not show-, market-, or code-specific by probing famous show IDs and
  markets US/PK/none, plus an artist and a search endpoint — all 403. This is a hard external
  blocker on the read side, so Principle V ("confirm API access before modeling") could not pass.
- **Impact**:
  - **Scope**: unchanged in shape — still exactly TWO platforms, still full-episode catalogs on
    both, so the entity-resolution hard core (Principle III) is fully preserved. Apple hosts the
    same full episodes as Spotify (this is *not* the rejected "Instagram/reels" idea, which had no
    shared episode to match).
  - **Constitution**: amended **1.0.0 → 1.1.0** (MINOR) — Principle III, Principle V, Scope
    Boundaries, and Definition of Done now name Apple Podcasts. See the Sync Impact Report.
  - **Milestones**: M0 Apple read probe now passes with no credentials (verified live). M1 live
    ingest proven against a real show. YouTube read + write sides are unchanged.
  - **Simplification**: removed the `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` config and the
    Spotify token flow; Apple needs no secret, shrinking the credential surface.
- **Links**: constitution Principle III/V + Scope + DoD (v1.1.0); `src/podcast_ops/ingest/apple_gateway.py`
  (new, replaces `spotify_gateway.py`); `access_check.check_apple_read`; `logic/decision.py`
  (`apple_without_youtube`); `objects/episode.py` (`apple` ref); `contracts/apple-read.md`;
  `.env.example` (`TARGET_APPLE_SHOW`).

---
