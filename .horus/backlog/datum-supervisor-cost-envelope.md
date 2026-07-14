---
title: "Datum supervisor-cost envelope + one-act acceptance (frozen schema)"
status: open
priority: now
tier: sonnet
parallel: safe
type: task
surface: horus/datums.py, horus/cli.py, launch/completion capture (launcher/delivery), capabilities projection, skills/delegation-rubric
created: 2026-07-14
created_by: overseer
---

# Datum supervisor-cost envelope + one-act acceptance [frozen schema — implement as specified]

Dropped by the cockpit overseer 2026-07-14. The datum store instruments **quality**
(`clean/nudged/bounced/died`) but not **cost**, so it cannot say whether a dispatch was
actually efficient end-to-end. The 2026-07-13 Codex cockpit run showed a Sonnet
implementation dispatch with a positive dividend and a Haiku continuity dispatch whose
supervisor tax (launch, PR review, bounce, CI, merge, merge-SHA CI) exceeded the authored
change. The schema below was frozen inline by the cockpit (methodology decision); implement
it as specified — do not redesign the fields.

## 1. Mechanical usage snapshots (launch + close)

At `record_launch` and at `horus datum close` time, capture a best-effort snapshot of each
readable usage surface into the datum row:

- `usage_launch` / `usage_close`: small JSON objects, one entry per readable target, e.g.
  `{"claude": {"pct_5h": 42, "pct_weekly": 37, "read_at": "...", "freshness": "fresh"},
    "codex": {"pct_5h": 90, "pct_context": 47, "read_at": "...", "freshness": "stale"}}`.
- `freshness` ∈ `fresh | stale | unavailable`. Codex's cached usage refreshes only when
  Codex runs a turn — mark it `stale` when the cached window's reset time is in the past or
  the cache predates the run. Claude's OAuth /usage read counts as `fresh` at read time.
- **Store readings only — NEVER a computed delta or cost score.** Provider signals are
  coarse; windows reset mid-run; the delta is the agent's judgment at close, in prose.
  Best-effort like every datum write: a failed read stores `unavailable`, never blocks a run.

## 2. Agent-supplied cost half — new optional `horus datum close` flags

- `--oversight {light,moderate,heavy}` — supervisor-steps bucket. light = brief + one
  review + accept; moderate = one bounce OR a reinstall/live-probe cycle; heavy = multiple
  bounce/poll cycles or a debugging tail.
- `--follow-on N` — count of ADDITIONAL worker/PR cycles the dispatch spawned beyond the
  primary one (the 2026-07-13 Haiku continuity PR = 1).
- `--counterfactual {direct-session,one-worker,multi-worker}` — the mode the agent judges
  in hindsight would have been cheapest for this task. `direct-session` means an
  in-project session, not the cockpit implementing.
- `--dividend {positive,neutral,negative}` — headline judgment: worker detail/context the
  overseer avoided, minus the fixed tax (brief + review + gate + merge + reinstall +
  datum/continuity close). Positive only when savings plausibly exceed the tax OR when
  parallelism / protecting the cockpit was the explicit benefit (name it in `--note`).

All four optional; existing datums stay valid. **HARD BOUNDARY preserved:** the agent
judges, the harness records — no auto-scored dividend, no suggested model, no routing.

## 3. One-act acceptance (collapse the post-merge tail)

Extend `horus datum close` with acceptance behavior (an `--accept` mode or a thin sibling
command — keep the surface minimal):

- Close the datum (quality + cost flags above) in one command, AND
- **Deterministically stamp the delivered backlog card** in the target project when given
  `--card <path-or-slug>`: set `status: done` (or `shipped`) + `shipped: <date>` in its
  frontmatter. Mechanical frontmatter write = legitimate CLI scaffolding (this implements
  the card-lifecycle-ship-provenance ask), AND
- **Probe target continuity freshness** (target `.horus/PRD.md` `last_updated` / latest
  session note vs the run's completion time) and PRINT a warning when stale — surface it,
  never auto-fix it. A tiny residual continuity close is done by the worker in its own PR
  (brief requirement) or by the overseer/in-project session — never a second worker.

## 4. Projection + rubric

- `horus capabilities --models`: per-model line gains a compact cost glance from datums
  that carry the new fields (e.g. `dividend +3/~1/-1 · oversight median: light`). Absent
  fields render as absent, not zero.
- `skills/delegation-rubric` (shared by dispatch-decision / execution-decision): when the
  recommendation is a dispatched mode, the emitted recommendation must name the expected
  **dispatch dividend** — what context/detail the overseer avoids vs the fixed tax listed
  above — and recommend dispatch only when plausibly positive, or when parallelism /
  cockpit protection is the explicit named benefit. Advisory prose only. Bump skill version.

## Acceptance

- Focused tests for: snapshot capture (incl. `unavailable` on failed read), new close
  flags persisted, card stamp frontmatter write, stale-continuity warning path.
- One live synthetic dispatch/accept cycle on this machine demonstrating: launch snapshot →
  `datum close` with the new flags → card stamped → continuity warning printed when stale.
- No dashboard work, no auto-router, no policy engine, no new daemon.
