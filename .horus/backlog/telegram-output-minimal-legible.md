---
status: open
priority: medium
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/notify.py (Escalation rendering) + horus/batch.py (batch message) + horus/cli.py (schedule status --brief, sessions --running) + horus/notify_listen.py (verb mapping)
---

# telegram-output-minimal-legible — the phone push + button replies are minimal, not log dumps

**Why (owner, 2026-07-19, first real batch-complete on the phone):** the batch-complete
Telegram was unreadable — it printed the whole roll-up TWICE (the telegram sink sent
`subject() + body()`, and both echoed a multi-line `summary`), the project read as the
worker's WORKTREE dir (`horus-harness-wt-auto-drill-echo-b`) not the repo, and the
Schedule/Sessions buttons relayed the FULL `schedule list` / `sessions` log — not legible
on a phone. The owner wants minimal, meaningful output: the push says what finished; the
Schedule tap shows only what's scheduled/running; Sessions shows only what's live.

## How

- Telegram sends `body()` alone (never `subject()+body()`); `body()` folds the project
  into a single header line so the summary prints exactly once. Keep `summary` one line;
  put multi-line detail in a new `Escalation.details` rendered once. An explicit
  `ok: bool|None` overrides the ✓/⚠ mark so a deadline-incomplete batch reads ⚠.
- Batch message: `✓ <repo> · batch <id> done (N/N)` + one concise line per leg
  (`glyph card: status · PR #n`). Resolve the real repo name from the worktree via
  `git rev-parse --git-common-dir` (its parent is the main repo root).
- `horus schedule status --brief` — only pending (scheduled) + running (fired, worker
  not terminal) dispatches, one line each; else `Nothing scheduled or running.` Point the
  notify-listen `schedule` verb + the batch Schedule button at it.
- `horus sessions --running` — only live sessions, one line each; else `No running
  sessions.` Point the `sessions` verb at it (owner: keep sessions, just make it minimal).

## Acceptance

- The batch-complete telegram shows the summary once, names the real repo, and lists each
  leg concisely; an incomplete/deadline batch reads ⚠.
- The Schedule tap shows only scheduled + running (no completed history); empty says so.
- The Sessions tap shows only live sessions; empty says so.
- Existing failure escalations (delivery-failed / supervise-gate / usage-band) keep their
  actionable fields (session/sha/PR/inspect).

## Non-goals

- Not removing the escalation channel's actionability — failure pushes still carry what
  the owner needs to act.
- Not a full phone UI; this is push + bounded-verb legibility only.
