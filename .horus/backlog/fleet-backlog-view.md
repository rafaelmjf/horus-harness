---
status: open
priority: medium
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/cli.py, horus/backlog.py, horus/fleet or status renderer
shipped: "2026-07-12 — capability built, PR open (branch feat/fleet-backlog-view). New `horus/fleet_backlog.py`: `horus fleet --backlog` reads every registered project's `.horus/backlog/` cards (excludes stray `status: done` cards left behind despite the delete-on-completion contract), sorts by priority then name, `--type`/`--project` filters, `--stdout` JSON or a human-readable grouped default. Projects still on inline PRD `## Backlog` (not yet migrated per PR #164) or missing `.horus/backlog/` entirely degrade to a skip-with-note row via a new `backlog_migrate.inline_backlog_item_count` best-effort counter — never crash that project's row. 24 new tests (20 in test_fleet_backlog.py, 4 in test_backlog_migrate.py), full suite green (1178). Verified against the real 7-project fleet registry: card-per-file projects roll up correctly, inline-backlog projects show a migrate-hint note, `--stdout` is valid JSON."
---

# `horus fleet --backlog` — deterministic fleet-wide backlog roll-up

**Owner ask (2026-07-12):** a command that cleanly displays each registered
project's backlog items, parsed deterministically, instead of relying on an agent to
open and parse every PRD/backlog by hand at fleet-resume.

**No overlap with existing surface (confirmed):** `horus backlog list`/`claim` are
single-project (cwd/`--path`); `horus status`/`fleet` show git freshness + latest
session, never cards. A fleet-wide backlog aggregation is new.

## Scope

- `horus fleet --backlog` (or `horus backlog --fleet`) reads the registry
  (`projects` in `~/.horus/config.toml`), loads each project's `.horus/backlog/`
  cards, and renders a grouped roll-up: per project, the open cards with
  `status`/`priority`/`tier`/`type`/`surface`. Deterministic, read-only, no fetching
  (same discipline as `capabilities`/`status`).
- **Agent-first:** `--stdout` JSON so an agent consumes it directly; human-readable
  default. This is the fleet-resume input the cockpit currently derives by hand.
- Sort/filter sensible defaults (e.g. by priority, `--type bug`, `--project`).

## Depends on

`unify-backlog-cards-fleet-standard` — a fleet roll-up only reads cleanly when every
project is on cards. Until then, degrade gracefully for inline-`## Backlog` projects
(best-effort or skip-with-note), don't crash a project's row (cf. the projects-section
resilience rule).

## Verification

Fixture registry with 2–3 projects (mixed priorities/types) renders a stable grouped
roll-up; `--stdout` emits valid JSON; a project with no `backlog/` degrades without
erroring. CI green. Overseer probe: run it against the live fleet and eyeball.
