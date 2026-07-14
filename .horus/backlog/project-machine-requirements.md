---
status: open
priority: medium
tier: sonnet
type: feature
created: 2026-07-10
---
> Kept 2026-07-14 (owner triage): concrete consumer exists (`fabric`), so this remains
> relevant after the correctness/reliability batch. It is not required for the next
> release and should not displace observed defects.

# Project-declared machine requirements (`doctor` + `resume` + dashboard)

A project commits `.horus/requirements.md` (`kind: machine-requirements`, `tools:`
name/probe/install/needed_for + `configs:`; prose for non-probeable deps).
`doctor project` probes → warn findings; **`horus resume` prepends "⚠ this machine is
missing: …" to the seed prompt**; dashboard card gets a readiness badge. First
consumer: fabric (needs `fab`/`pbir`/PBI skills, declared there 2026-07-07).
