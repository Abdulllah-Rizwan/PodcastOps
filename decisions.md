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
