---
status: shipped
priority: low
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: agent
surface: tests/ (a guard over every Horus systemd-unit writer in horus/schedule.py)
shipped_pr: 341
shipped_sha: ba658b2be777961ebb8181fb81869f37c81efd2c
---

# systemd-unit-absolute-execstart-guard — one test over all unit writers

**Why (2026-07-18, companion to #322):** the `203/EXEC` bug was a bare `ExecStart`
(systemd resolves it against the manager's own PATH, not `Environment=PATH`). The
fix added an absolute-path test for the *listener*, but a *future* unit writer
could reintroduce a bare `ExecStart` and only fail in production. A cheap
deterministic guard over ALL unit-writers prevents the whole class.

## How

- A single test that, for every systemd unit Horus generates (`_service_unit`,
  `_notify_unit`, `_listen_service_unit`, and any future writer), asserts the
  `ExecStart=` value's first token is an ABSOLUTE path (or a resolvable one that
  the writer resolves). Enumerate writers so a new one is covered by construction,
  or assert on representative outputs.
- Keep it a plain unit test (no real systemd) — it catches the authoring mistake,
  which is the escape point.

## Acceptance

- The test fails if any current/new unit writer emits a bare-name `ExecStart`.
- Runs in the normal suite (CI), so it travels across models/accounts via git.

## Non-goals

- Not a systemd exec check (that's `service-installers-self-verify-active`); this
  is the static authoring guard.
