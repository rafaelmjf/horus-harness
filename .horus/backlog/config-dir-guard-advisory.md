---
status: open
priority: high
created: 2026-07-18
vision_facet: "Accounts & isolation"
phase: converge
tier: opus
type: bug
parallel: safe
created_by: owner
surface: horus/cli.py (_config_dir_conflict_guard + run call site), tests/test_config_dir_guard.py, CLAUDE.md/AGENTS.md managed block
---

# config-dir-guard-advisory — same-account concurrency is advised, not refused

**Why (owner, 2026-07-18, surfaced by the X3 e2e rehearsal):** the config-dir guard
hard-refused (`exit 2`) launching a second agent process on an account that already
had a live session — so the rehearsal worker couldn't dispatch to `claude-work` while
a live `horus-agent` brainstorm held that account, even though the two are independent
work on different repos. The owner's point: Claude Code natively supports concurrent
sessions on one config dir; blocking them "doesn't make much sense."

The guard over-climbed the control ladder. Its whole basis was **one** incident
(2026-07-16): two workers *cold-starting simultaneously* on a shared **ambient** dir,
both died at startup. Two things undercut a blanket hard-refusal today: (1) that
incident's premise — the ambient shared dir — largely dissolved once every account got
its own isolated dir; (2) the real corruption window is narrow (concurrent *startup*
writes), while two *settled* sessions coexist safely as the agents natively allow.

## What changed

- `_config_dir_conflict_guard` is now **advisory**: it always returns `None` (proceed)
  and prints a one-line note naming the live peer + its project, so a shared config dir
  (and its shared rate-limit budget) is never silent. It no longer refuses; `--force`
  is no longer consulted by it (the flag stays for the ≥95% usage-band guard).
- Tests rewritten to assert note-and-proceed. Full suite green (1914).
- CLAUDE.md/AGENTS.md managed block updated in lockstep: "same-dir concurrency is
  advised, not blocked."

## Acceptance

- `horus run` on a busy account prints the advisory note and launches (verified live
  against the real registry: names peer `80546ce3 (horus-agent)`, returns proceed).
- No test asserts the old `exit 2` refusal.

## Non-goals / follow-up

- Per-account **isolation by default** is unchanged — distinct accounts still get
  distinct dirs (that guards accounts from *each other*, a separate concern).
- If corruption ever recurs *with isolated dirs*, re-promote to a narrow startup-window
  guard (needs a `launched_at` on the registry record, which does not exist today) or a
  startup lockfile — not a blanket refusal.
