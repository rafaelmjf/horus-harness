---
status: open
priority: low
tier: sonnet
created: 2026-07-15
vision_facet: "Delegation calibration"
type: feature
parallel: unsafe
surface: horus/runlog.py, horus/registry.py, horus/terminal_sessions.py, horus/tmux_runner.py, horus/pty_session.py, horus/cli.py
---

# Worker progress heartbeat / stall detection

A dispatched one-shot worker died silently in a real campaign: it parked waiting on a
slow background job (gvfs Drive I/O), its one-shot session ended, and the process
exited **0 having produced no branch, commit, or PR**. The launcher and registry saw a
clean exit; only a manual staged-vs-produced count reconciliation revealed nothing had
been delivered. "Success that did no work" is the dangerous failure — worse than a
crash, because it reads as done.

The existing [[attachable-detached-worker-run]] and
[[deferred-supervision-completion-receipt]] cards cover process *liveness* states
(running / exited / failed / stale) and the *completion* signal (delivery-ready /
blocked / failed / unknown). Neither covers **alive-but-not-progressing**: a worker
that is still running (or exits cleanly) without advancing the task. This card adds the
missing progress dimension so a parked or no-op worker is visible as `stalled`, never as
silent success.

## Acceptance

- A worker emits a lightweight periodic progress heartbeat (e.g. last tool activity /
  output timestamp) into the run log or registry; no new daemon or control plane.
- Reconciliation classifies a session with a live process but no progress for N minutes
  (configurable) as `stalled`, distinct from running / exited / failed / stale.
- A worker that exits with **no delivery evidence** (no branch/commit/PR/continuity
  receipt when the brief expected one) is surfaced as `no-op` / `blocked`, never as a
  bare success — the completion receipt in [[deferred-supervision-completion-receipt]]
  consumes this signal.
- TUI and the scriptable CLI/JSON surface show the stalled/no-progress state without
  parsing prose.
- Tests cover: a worker parked on a long wait (stalled), a clean exit with zero delivery
  evidence (no-op flagged), and a normal delivering worker (unaffected).

## Boundaries

- Heartbeat is an observability signal, not an auto-kill or auto-resume trigger; the
  owner still decides what to do with a stalled worker.
- Reuse existing run-event / registry fields; add only the minimum progress timestamp.
- Complements, does not replace, liveness reconciliation in
  [[attachable-detached-worker-run]].

## Reviews

- 2026-07-16 — Owner session split kernel from trimmings. The failure-evidenced
  kernel (clean exit with zero delivery evidence surfaced as `no-op`, never bare
  success) moved INTO the [[attachable-detached-worker-run]] campaign — the observed
  incident (gvfs-parked worker exiting 0 with nothing delivered) is caught at exit
  by that check. What remains here is the *alive-but-parked* periodic heartbeat /
  stall timer, deferred until (a) the detached primitive has run one real campaign
  showing stall frequency and (b) a check of what progress signals the native CLIs
  have shipped by then — the timer machinery is the part most likely to be served
  natively; the delivery-evidence judgment is not and stays Horus-owned. Priority
  high→low accordingly; the campaign's schema phase reserves the progress dimension
  so adding this later is one field, not a migration.
