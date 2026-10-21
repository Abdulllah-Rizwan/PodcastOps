# CLAUDE.md — Podcast Ops-Hub (validation slice)

## Purpose of this file
Durable context and guardrails for this project. Read before every task. This is the
project's constitution-in-brief: it fixes **what we're building, why, and the hard
boundaries**. Detailed specs are produced separately (SDD); this file governs them.

## What we are building
A deliberately **narrow vertical slice** of a "podcast ops-hub" that proves one
end-to-end spine of the **data → logic → action** pattern: an operational layer that
fuses data from systems we don't own, decides on it, and writes a change back out
safely.

The goal is to **demonstrate the pattern**, not to ship a product.
Success = the spine runs end-to-end on real data, once.

### This project is NOT
- a clip-optimization tool or podcast SaaS
- a general / reusable "ontology engine"
- a multi-platform product
- an actual podcast (we own a throwaway test channel only, for writes)

If a task drifts toward any of these, stop and flag it.

## The framework: data → logic → action (narrow)
Three stages. Keep the vocabulary exact — sloppy wording here causes rework.

- **Data** — raw platform data lands in a **staging area first**, is then **resolved
  and conformed**, and only *then* becomes an **object**. The object is the clean,
  fused result, never the raw inlet. Core object type: `Episode`.
  An object *type* ≈ a table; an object *instance* ≈ a row.
- **Logic (= function)** — read-only. It **decides** ("what should we do?").
  Plain rules only for this slice. No ML, no forecasting.
- **Action** — the **only** thing that changes the world. It writes back to a
  platform, and it is **safe** (can fail, retry) and **logged**.
  Deciding is not acting — keep them separate.

**Entity resolution is the hard core of this project**: correctly matching the same
real-world thing (an episode, a guest) across platforms that use mismatched IDs,
titles and schemas. Never paper over it — it is the part worth proving.

Deferred, acknowledged, **do not build in this slice**: the learning **loop**
(performance feeding back into logic) and the **governance/security** layer.
These are later milestones.

## Scope of the validation slice (hard boundary)
- **Read:** ONE real, public show, from **two** platforms — **YouTube + Apple Podcasts** —
  using public metadata (+ YouTube public engagement counts). No ownership needed to read.
  (Apple replaced Spotify on 2026-10-21 — Spotify's API required a Premium app-owner account;
  see `decisions.md`.)
- **Fuse:** match the same episode across both platforms into one `Episode` object.
  ← this is the entity-resolution proof.
- **Logic:** exactly **one** rule/function that produces a decision
  (e.g. "episode exists on Apple Podcasts but has no YouTube clip yet").
- **Action:** exactly **one** writeback, to **our own throwaway test channel**
  (e.g. post a draft clip / update show notes / schedule a post). Never to anyone
  else's channel.
- **Out of scope:** the loop, analytics dashboards, extra platforms, ML.

Owner-only data (listen counts, retention curves for a show we don't own) is **not**
accessible — do not design around it.

## Operating principles (apply to every task, including Claude Code's)
1. **Ship-not-learn.** The smallest thing that runs end-to-end wins. Prefer a working
   spine over a complete feature.
2. **Hold the line on scope creep.** If a change adds a platform, a model, a dashboard,
   the loop, or "make it general," it is out of scope for the slice — name it and defer it.
3. **Writeback behind a seam, mock first.** The action first **logs**
   `"would publish X to Y"` instead of calling the real API. Prove the whole spine
   moves, *then* swap in the real call against the test channel.
4. **Confirm API access before modeling.** Before any object is modeled, verify the two
   platforms actually permit the one read and the one write planned (quotas, auth, write
   scopes). Do not design a writeback a platform forbids.
5. **Separate raw from object.** Raw → staging → resolve + conform → object.
   Never ingest raw straight into an object.

## Milestones
- **M0** — confirm API access for the one read and the one write.
- **M1** — read + fuse both platforms into `Episode` objects (entity resolution working).
- **M2** — one function produces a decision.
- **M3** — one action: mock-logged first, then real against the test channel, safe + logged.
- *(later)* **M4** — close one loop.  **M5** — widen.

## Definition of done (slice)
One run: pulls a real show from YouTube + Apple Podcasts, fuses its episodes correctly, applies
the one rule, and executes one safe, logged writeback to the test channel. If that runs
end-to-end, the slice is done. Stop there.