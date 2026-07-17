---
status: shipped
priority: medium
created: 2026-07-17
tier: sonnet
type: bug
parallel: safe
phase: converge
vision_facet: "Continuity core"
created_by: owner
surface: horus/closure.py (parallel_delivery_findings level / how boundary_freshness_gate composes it), horus/cli.py (cmd_close healthy verdict)
shipped_pr: 306
shipped_sha: c3f258e
---

# parallel-signal-informational-not-verdict — a named sibling PR shouldn't read as "Stale"

**Why (observed 2026-07-17, from PR #301):** the new parallel-delivery signal
(`closure.parallel_delivery_findings`) emits `warn`-level findings, so `close --check`
folds them into `boundary_freshness_gate` and `cmd_close`'s `healthy` computation treats
them as blocking — the verdict flips to "**Stale — action needed**" whenever ANY unrelated
sibling PR is merely open (e.g. the long-open PR #117 on this repo). That is wrong: a
supervisor legitimately closes while siblings exist — the signal's job is to *name* the
sibling so it isn't missed, NOT to gate closure on it. The `--commit --push` still runs
(and the unattended `commit_continuity` path is unaffected), so this is a misleading
verdict/label, not a functional block — but a false "action needed" on every close during
the trip is exactly the noise the away-mode kit must not produce.

## Fix (make the parallel signal informational)

The parallel-delivery findings should still PRINT (naming sibling PRs + live co-sessions)
but must NOT flip the overall Fresh→Stale verdict or count toward `healthy`. Either a
distinct non-blocking finding level (e.g. `info`/`note`) that renders but is excluded from
the warn/fail aggregation, or exclude parallel findings from the `healthy` computation
specifically — whichever keeps the existing freshness/checkpoint gates intact.

## Acceptance

- With only parallel-delivery signals present (no real freshness/checkpoint problem),
  `close --check` still NAMES the sibling PRs / live co-sessions but reports a fresh /
  non-blocking verdict — it does not say "Stale — action needed".
- A genuine freshness or checkpoint failure still flips the verdict to stale/action-needed
  exactly as today (the parallel change must not weaken those gates).
- `resume` continues to surface the same parallel signal (unchanged there).
- Tests cover: parallel signal alone → not stale; parallel signal + a real freshness
  failure → stale; no parallel signal → unchanged verdict.

## Non-goals

- Do not remove or weaken the parallel-delivery detection itself (item 5 behavior stays);
  this is purely about how the advisory signal maps to the close verdict.
- No change to the unattended supervisor path (`supervise._close_continuity` →
  `commit_continuity`), which never went through the `healthy` aggregation anyway.
