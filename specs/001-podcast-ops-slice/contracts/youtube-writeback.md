# Contract: YouTube Writeback (the one action)

**Component**: `src/podcast_ops/action/writeback.py` — `WritebackPort` with `MockWriteback`
and `YouTubeWriteback`. **Direction**: outbound write. **Target**: our own throwaway test
channel ONLY. **Auth (real mode)**: OAuth 2.0, scope `youtube.force-ssl`.

## Interface (internal port)

```
WritebackPort.publish(decision: Decision, episode: Episode) -> WritebackAttempt
```

Two implementations, selected by CLI flag (`--mock` default, `--real`):

### MockWriteback (default, built first)
- Logs `"would publish X to Y"` with the full intended change.
- Makes **no** external API call. `outcome = success`, `mode = mock`.

### YouTubeWriteback (real, enabled only after mock-mode spine passes)
- Call: `videos.update` with `part=snippet`, updating `snippet.description` of an owned test
  video to append an Apple-Podcasts-link show-notes marker.
- `mode = real`, `target =` test video id on the test channel.

## Contract rules (safety — Principle IV)

- **Test-channel only**: MUST verify the target video belongs to the configured test channel;
  refuse otherwise. NEVER writes to any third-party channel.
- **Idempotent / retryable**: before writing, check whether the show-notes marker is already
  present; if so, return `outcome = skipped_idempotent` (no duplicate). A retry after a timeout
  MUST NOT create a second change.
- **Logged**: every attempt (mock or real, success/failure/skipped) is appended to the audit log.
- **Exactly one writeback** exists in this slice.
- Contract test: mock mode produces a `WritebackAttempt` with `mode=mock` and zero network
  calls; idempotency check returns `skipped_idempotent` on a second run.
