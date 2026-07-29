---
status: shipped
priority: medium
tier: medium
created: 2026-07-29
created_by: owner
last_refined: 2026-07-29
refine_passes: 1
readiness: ready
autonomy: attended
order: 40
phase: converge
type: feature
vision_facet: "Dashboard / cockpit"
parallel: exclusive
depends-on: tui-remote-freshness-indicator
surface: horus/terminal_tui.py, horus/sync.py, horus/gitstate.py
shipped_pr: 434
shipped_sha: c916d70
---

# cockpit-sync-action — one-tap "Sync" in the TUI (per-project + fleet), on the shipped engine

## Why

`tui-remote-freshness-indicator` (order 30) makes cross-project staleness *visible*
in the cockpit — each row shows `current` / `behind N` / `unknown`. This card is the
**act** half: once the owner sees a project is behind, a **Sync** action fast-forwards
it without dropping to a terminal. The TUI is the daily/away-mode cockpit and the one
launch surface that never fires fetch-first; seeing "behind N" and being unable to act
on it in place is the friction that started this thread.

The engine already exists: **`horus sync` shipped (PR #433)** — `sync.plan()` is a pure
decision over a git-state mapping returning CURRENT / SYNCED / REFUSED, and
`sync.fast_forward()` runs `git merge --ff-only`. This card is a thin cockpit surface
over that, not a new git client.

**Naming (resolved 2026-07-29):** this action is **"Sync"** — inbound, a project's own
state pulled in — matching the `horus sync` CLI verb so the cockpit and CLI say the
same word for the same operation. It is deliberately distinct from **"Horus Assets
Refresh"** (`tui-fleet-artifact-refresh`), the *outbound* push of Horus's managed
skills/block into consumer repos. Refresh = assets out; Sync = state in.

## How

- **Per-project Sync.** On a project row that is cleanly fast-forwardable (clean tree,
  no local commits, strictly behind), offer a `Sync` action that calls the same path
  as `horus sync`: `sync.plan(state)` then `sync.fast_forward(root, upstream)`. Reuse
  the module — do not re-implement the decision or the merge.
- **Fleet "Sync all clean-behind".** A single action fast-forwards every registered
  project that `sync.plan` classifies SYNCED, concurrently under one global deadline
  (mirror the freshness card's bounded-fetch pattern, never N × per-repo timeout).
- **Refusals are shown, never forced.** Dirty, ahead, diverged, detached, or
  no-upstream projects are listed with `sync.plan`'s exact reason and skipped — never
  auto-stashed, force-pushed, or cleaned. This inherits `horus sync`'s refusal matrix
  wholesale.
- **After a sync**, the row re-reads freshness (from `gitstate.git_state`) so the
  cockpit reflects the new HEAD without a full relaunch.

## Acceptance

- A `behind`, clean, fast-forwardable project row offers `Sync`; invoking it advances
  that checkout to its upstream and the row updates to `current`. A dirty/ahead/
  diverged/detached row shows the refusal reason and offers no Sync (or a disabled one).
- **Sync all clean-behind** fast-forwards exactly the SYNCED projects, shows a durable
  per-project result (synced → now at SHA / already current / skipped + reason), and is
  idempotent on rerun. It never mutates a project `sync.plan` refuses.
- **Gate on the delivered SHA:** focused TUI tests cover per-project sync of a
  clean-behind repo, refusal rendering for each unsafe state, fleet sync across a mixed
  clean/dirty/ahead fleet, and idempotent rerun — all driving `sync.plan`/`fast_forward`,
  asserting no second decision path is introduced. **Live probe:** on a throwaway repo
  pair (one clean-behind, one dirty), the cockpit Sync fast-forwards the clean one to its
  upstream and refuses the dirty one with the reason, without moving the dirty repo's HEAD.

## Non-goals

- No auto-sync at launch or on a timer — the action is always owner-invoked (hooks
  advise, never override; this preserves that contract).
- No new git/fetch/merge implementation — strictly a surface over `horus.sync`.
- Not the SessionStart-hook auto-ff idea (the more invasive "enact fetch-first at
  session start") — that stays an open `[session]` question in `continuity-sync-friction`.
- Not the outbound Horus Assets Refresh (`tui-fleet-artifact-refresh`).

## Source

Carved 2026-07-29 (refine pass) from the "enact fetch-first" direction of
`continuity-sync-friction` — its manual, cockpit slice — now buildable because
`horus sync` shipped the engine (PR #433). Sequenced after `tui-remote-freshness-indicator`
(see → act); shares `terminal_tui.py`, hence `parallel: exclusive`.

## Reviews

- **2026-07-29 — Minted Ready/attended, `order: 40` (owner, refine pass).** Kept
  separate from the freshness card (owner chose see→act as two cards, not a merge) and
  from `continuity-sync-friction` (which cannot go Ready while it holds `[session]`
  format questions). This is the honest home for the TUI Sync action: decision-complete,
  engine already shipped, safe by inheriting `sync.plan`'s refusal matrix.
