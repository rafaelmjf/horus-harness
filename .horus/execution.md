---
status: complete
current_feature: "Campaign launch + provider-selector guard"
created: 2026-07-16
updated: 2026-07-16
---

# Execution Plan — Campaign launch + provider-selector guard

Completed as two owner-approved, disjoint Claude worker phases from base `0e39c292`.
The supervisor owned acceptance, delivery, incident handling, and continuity.

## Phase 1 — Campaign launch prompt + TUI affordance

- status: complete
- delivery: PR #265, merge `d75bd4c1890e5ea28dbfe980601c0f8c160fdc9a`
- worker_runtime: 583.42 seconds
- evidence: required CI green on the exact PR SHA; 147 targeted tests and 1556 full-suite tests reported; supervisor drove a private-tmux TUI frame showing optional Campaign separately from Fleet Review with direct project launch intact.
- outcome: clean delivery with light oversight and a positive parallel/context dividend.

## Phase 2 — Provider-valid selector preflight + consent contract

- status: complete by supervisor salvage
- delivery: PR #266, merge `ffbb9688c648e10feeeaaa3010fe8c1ca5cb3eb6`
- worker_runtime: 571.381 seconds
- incident: during an unisolated manual cleanup probe the worker deleted `~/.horus/logs/runs`; historical machine-local streamed run logs were lost, while registry, datums, git/worktrees, tmux metadata, and PR state remained intact. The worker stopped without commit or PR.
- evidence: supervisor reviewed and committed the bounded diff, observed 313 targeted tests green, proved calibration-only labels fail before side effects and full selectors reach the adapter unchanged, then watched required CI green on the exact PR SHA.
- outcome: bounced delivery with heavy supervisor oversight and negative delegation dividend. PR #267 subsequently added the worker-only global-state deletion guard and exact isolated-probe guidance.

## Usage evidence

Both workers shared the ambient personal account and ran concurrently, so per-worker attribution is unavailable by design. The fresh account readings moved from 0% to 33% in the five-hour window and 8% to 10% weekly; these are combined observed percentage-point movements, not task estimates.
