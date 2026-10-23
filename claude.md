# CLAUDE.md — Podcast Ops-Hub → Ontology Engine

## Purpose of this file
Durable context and guardrails for this project. Read before every task. This is the
project's constitution-in-brief: it fixes **what we're building, why, and the hard
boundaries**. Detailed specs are produced separately (SDD); this file governs them.
The full constitution is `.specify/memory/constitution.md` (**v2.0.0**); where this
brief and that document differ, the constitution governs.

> **Pivot note (2026-10-23):** the original narrow validation slice is **complete** and
> proven. The project has been deliberately redefined from that throwaway slice into a
> reusable **ontology engine** (constitution MAJOR bump 1.1.0 → 2.0.0; see `decisions.md`).
> This file reflects the new direction.

## What we are building
A reusable, **AI-native ontology engine** that implements the **data → logic → action**
pattern — objects fused from systems we don't own, read-only functions that decide, and
safe actions that write changes back out — and we **prove it by building verticals on top**.

- The **engine is the product.** It is domain-agnostic: an object/link registry, read-only
  functions, typed actions, the ingestion/resolution pipeline, an API, and an AI runtime.
- A **vertical** is a plugin/configuration on the engine. **Podcast operations is vertical #1**
  and is the live demo that proves the engine on real, messy, cross-platform data.
- **Generality is *earned*, never asserted.** One vertical is a demo; **two different verticals
  on one engine** are the proof the engine is real. Vertical #2 is planned (M5), not yet built.

### This project IS (as of v2.0.0)
- a general, reusable ontology engine
- an AI-native operational platform (AI grounded in the ontology)
- full-stack: web UI, API backend, Postgres + vector store, background worker, cloud
- a candidate product, if real demand appears

### This project is NOT
- a generality built in the abstract with no real user (the classic "worse Foundry" trap)
- an engine that grows abstractions no current vertical actually uses
- an actual podcast business (we own a throwaway test channel only, for writes)

If a task drifts toward building speculative generality ahead of a real second need, or
toward collapsing the engine/vertical seam, stop and flag it.

## The framework: data → logic → action = the ontology
Three stages, exact vocabulary. Sloppy wording here causes rework.

- **Data → Objects** — raw platform data lands in a **staging area first**, is **resolved and
  conformed**, and only *then* becomes an **object**. The object is the clean, fused result,
  never the raw inlet. The engine models **object types** (≈ tables), **object instances**
  (≈ rows), and typed **links** between types (e.g. `Episode —features→ Guest`,
  `Episode —hasClip→ Clip`). Vertical #1's core object type is `Episode`.
- **Logic = Functions** — read-only. They **decide** ("what should we do?") and change nothing.
  Held in an inspectable registry.
- **Action** — the **only** thing that changes the world. Typed, validated, safe (can fail,
  retry), **idempotent**, and **logged/audited**. Deciding is not acting — keep them separate.

Object types, links, functions, and actions are declared **declaratively** in the engine's
registries, so a vertical adds them as config/plugins, not by editing engine core.

**Entity resolution is the hard core**: correctly matching the same real-world thing (an
episode, a guest) across platforms with mismatched IDs, titles and schemas. Never paper over it
— it is the part worth proving. Where embeddings/vector similarity are used, keep a deterministic
baseline matcher to **evaluate** against. Resolution must be explicit, inspectable, and measured.

## AI in the engine (grounded + evaluated)
- AI reads the world through **objects, links, and functions**, and changes the world **only
  through validated actions**. The LLM *proposes*; the engine *validates and records*; a human
  *approves* mutations (human-in-the-loop).
- Retrieval feeding an LLM is **grounded in the ontology** (objects + their links / embeddings),
  not unstructured dumps.
- **Evals are mandatory.** Entity resolution has precision/recall against a labeled golden set;
  AI generation/action-selection has deterministic + rubric/LLM-as-judge checks; AI calls are
  traced. Eval suites run in CI and gate changes against regression.

## Scope & architecture (hard boundary)
Full-stack. All layers in scope:
- **UI** — ontology explorer + the vertical's ops dashboard + the AI agent/chat.
- **API backend** — over the ontology core (FastAPI over the existing Python core).
- **Storage** — Postgres for objects/staging + **pgvector** for embeddings (default).
- **Worker** — background ingestion.
- **AI layer** — grounded retrieval + agent.
- **Evals + observability** — eval harness + tracing.
- **Cloud** — containerized, deployed, with CI/CD (default target: GCP Cloud Run + Vercel).

**Vertical #1 (podcast ops):** object types `Show`, `Episode`, `Guest`, `Clip`; data sources
**YouTube + Apple Podcasts**; its functions; its actions (writeback to our own throwaway test
channel); its UI views. The entity-resolution proof — match one real episode across YouTube and
Apple into one `Episode` — MUST be preserved.

**Out of scope until deliberately chosen and logged:** the governance/security layer as a product
feature; multi-tenant productization; any data source that hasn't passed the access gate below.

## Operating principles (apply to every task, including Claude Code's)
1. **Engine first, earn generality.** Build vertical-shaped first with clean seams; do not add
   abstractions no current vertical uses. Keep vertical #1 working end-to-end at all times.
2. **Hold the engine/vertical seam.** Vertical specifics MUST NOT leak into the engine. If a
   change blurs the seam or adds speculative generality, name it and defer it.
3. **Separate raw from object.** Raw → staging → resolve + conform → object. Never ingest raw
   straight into an object.
4. **Deciding ≠ acting.** Functions are read-only; only validated actions mutate external state.
5. **Actions: safe, logged, mock-first, owned-target-only.** An action first **logs**
   `"would publish X to Y"` before any real call. Real actions are safe, idempotent, audited, and
   target only channels we own. AI-proposed actions require human approval.
6. **AI grounded + evaluated.** AI reads via the ontology, writes only via actions, and is
   covered by evals + tracing.
7. **Confirm access before modeling.** Before modeling an object/action against a source, verify
   the source actually permits the planned read/write (quotas, auth, scopes). Don't design a
   writeback a platform forbids. Applies to every new source a vertical introduces.
8. **High quality, full stack.** Clear structure mirroring the engine/vertical + data→logic→action
   boundaries; patterns where they add clarity (YAGNI otherwise); dependencies inverted at external
   boundaries so APIs/LLM/vector store/writeback are mockable; tests for resolution & functions,
   mock-mode action seam, AI evals; no secrets committed, config externalized (secret manager in prod).

## Milestones
- **M0** — Full-stack skeleton: API over the existing core, Postgres, minimal UI, deployed thin
  (no AI yet — prove the stack moves).
- **M1** — Generalized ontology core: declarative object/link/function/action registries; podcast
  defined as a vertical plugin.
- **M2** — Entity resolution upgraded (embeddings + vector store) with precision/recall evals
  against a labeled golden set (seeded from the real matched pairs already produced).
- **M3** — AI agent over the ontology: grounded retrieval + answers; proposes validated, audited,
  human-approved actions; AI evals + tracing.
- **M4** — Harden & deploy for real: CI/CD with the eval gate, observability, secrets, autoscale;
  UI complete (explorer + ops dashboard + agent).
- **M5** — Vertical #2: a second, different domain runs on the same engine with no engine rewrite —
  **the generality proof.**

## Definition of done (current build)
The engine runs the podcast vertical full-stack in the cloud — UI → API → ontology (objects fused
by honest entity resolution) → AI grounded in the ontology → a safe, idempotent, audited,
human-approved action — with eval suites green in CI. The **engine is proven** only when a second,
different vertical (M5) runs on it with no engine rewrite.

## History
The original narrow validation slice (read YouTube + Apple, fuse `Episode` objects, one rule, one
mock-then-real writeback) ran end-to-end on live data on 2026-10-21 and is complete. See
`progress.md` for that history and `decisions.md` for the 2026-10-23 pivot to the ontology engine.
