---
status: shipped
priority: medium
tier: sonnet
type: feature
created: 2026-07-10
surface:
  - horus/machine_requirements.py
  - horus/cli.py
  - horus/routines.py
  - horus/dashboard.py
  - horus/terminal_tui.py
shipped_pr: 237
shipped_sha: 2f2c7b3
---
> Kept 2026-07-14 (owner triage): concrete consumer exists (`fabric`), so this remains
> relevant after the correctness/reliability batch. It is not required for the next
> release and should not displace observed defects.

# Project-declared machine requirements (`doctor` + `resume` + dashboard + TUI)

A project commits `.horus/requirements.md` (`kind: machine-requirements`, `tools:`
name/probe/install/needed_for + `configs:`; prose for non-probeable deps).
`doctor project` probes → warn findings; **`horus resume` prepends "⚠ this machine is
missing: …" to the seed prompt**; dashboard and TUI project views get a readiness
warning. All four consumers must render one shared read-only parser/probe result,
never introduce a second requirements path. First consumer: fabric (needs
`fab`/`pbir`/PBI skills, declared there 2026-07-07).

## Reviews

- 2026-07-14 — Owner expanded scope before implementation: include the TUI so a
  missing requirement is visible before launching from a terminal as well as the
  web dashboard.
