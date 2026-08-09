---
status: open
topic: account-isolation
priority: medium
created: 2026-08-08
created_by: agent
readiness: shaping
readiness_reason: "The limitation is measured and the honest read-out shipped with it, but the remedy is undecided: Codex exposes no account-level usage API here, so the options are a cross-machine snapshot exchange, an explicit 'local-only' marker on the surface, or accepting it as a documented boundary."
phase: explore
type: spike
vision_facet: "Accounts & isolation"
surface: horus/usage_snapshot.py:206 (_read_codex), horus/terminal_tui.py (_refresh_all_account_usage)
---

# codex-usage-blind-across-machines — a Codex usage reading cannot see another machine

## Why — measured 2026-08-08, while adding the TUI's all-accounts usage refresh

The owner's reported friction was stale usage "especially working across different
machines and with the native apps". The `U` refresh (#504) fixes that for Claude, whose
read is a live OAuth call against the provider's own accounting and is therefore
machine-independent.

It cannot fix it for Codex. `_read_codex` derives usage from the newest **local rollout
file**, so a Codex reading is bounded by two things no keypress can change:

- **It is only as fresh as that account's last local turn.** An idle account yields a
  reading hours old while the read happens right now — measured at 2.9h during the live
  probe.
- **It is local-only.** Usage spent on another machine, or in a native app, leaves no
  rollout here and is therefore invisible — the reading is not merely stale, it is
  structurally incomplete.

`#504` made this honest rather than hidden: the refresh counts provider-captured
freshness separately, so an idle Codex account reports "still reporting an older
capture" instead of a confident wrong number. That closes the *misleading* half of the
problem and leaves the *coverage* half open.

## Why it matters beyond display

Dispatch decisions read these percentages. A Codex reading that omits another machine's
spend understates usage, which is the failure direction that lets a launch proceed
against capacity that is already gone — the mirror of the 2026-07-23 incident, where an
over-stated stale reading refused a valid dispatch.

## Open questions

- Does Codex expose any account-level usage surface reachable without a turn? If not,
  the honest ceiling is local evidence plus an explicit marker.
- Is a cross-machine snapshot exchange worth its cost, given the fleet is one owner on a
  small number of machines, and given `.horus/` is the only contract and is per-repo?
- Should the accounts surface mark Codex rows as local-evidence-only, rather than
  relying on the age read-out to imply it?

Non-goals: inventing a usage number Codex did not report; polling; adding a second model
call for accounting.

## Source

Found while implementing #504 (owner request for a manual all-accounts usage refresh).
The distinction between the two agents' reads is at `horus/usage_snapshot.py:185-233`,
whose own comments record the 2026-07-23 / 2026-07-26 stale-reading incident.
