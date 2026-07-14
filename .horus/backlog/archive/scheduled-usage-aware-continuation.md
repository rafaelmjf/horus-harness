---
status: retired
priority: deferred
tier: sonnet
type: feature
created: 2026-07-10
archived: 2026-07-15
---
> Archived 2026-07-15 as out of shape for the current product. One hand-rolled
> systemd timer proved feasibility, while `horus run`, preflight, and usage
> guards already cover the safety Horus owns. A first-class scheduler would add
> a durable orchestration surface without a recurring workload. Reopen only
> when a specific unattended task repeats often enough that an external timer
> plus a pinned Horus command is demonstrably insufficient.

# Scheduled / usage-aware autonomous continuation (retired)

The preserved design was: usage-threshold stopping, reset-aware deferral, a
pinned resume task, unattended posture, and registry/PR visibility. Scheduling
remains local/external by design until repeated real use justifies moving any
of those mechanics into Horus.
