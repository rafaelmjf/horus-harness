---
title: "[bug] Add datum void/aborted state and separate death from quality rate"
status: shipped
priority: medium
tier: sonnet
parallel: safe
type: bug
surface:
  - horus/datums.py
  - horus/cli.py
created: 2026-07-12
created_by: overseer
migrated_from: rafaelmjf/horus-agent
execution: "inline Sonnet-class correctness fix; focused tests + live CLI probe"
shipped_pr: 241
shipped_sha: b591bd9
---

# Add datum void/aborted state and separate death from quality rate

Migrated from horus-agent during its fleet-curator consolidation.

An operator-aborted pre-test run currently has no truthful outcome: forcing it
to `died` makes an untested model look failed, while leaving it open creates
staleness. Add a supported void/aborted path excluded from calibration.

`died` is an operational outcome (usage/crash), not a quality result, but the
current clean-rate denominator includes every closed datum. Compute quality over
`clean|nudged|bounced` only and show deaths/voids separately, e.g.
`3/3 clean · 1 died`. Verify a voided run does not affect quality and a died
run remains visible without reducing the quality denominator.
