---
date: 2026-07-14T22:32:42
agent: claude
account: personal
environment: host
project: horus-harness
status: complete
summary: "Consolidated horus-agent and added a remote-authoritative fleet review, optional TUI curator path, and owner-gated workflow."
---

# remote authoritative fleet curator

## Summary

Re-evaluated horus-agent after the TUI/SSH/Tailscale refocus. Kept it as a
separate Git-synchronized multi-machine decision workspace, removed its product
backlog, and moved all reusable behavior into horus-harness.

## Key Points

- Merged horus-agent PR #4: six-repository path-free manifest, slim curator PRD,
  zero active product cards, and 29 preserved archived cards with rationale.
- Migrated three real defects into harness: server-side freshness enforcement,
  truthful close output, and datum void/death taxonomy.
- Removed five stale inline harness candidates that sat outside the card lifecycle:
  the hub/LaunchBackend decision is on hold, catalog/machine/hook measurements had
  no current consumer, and the CI-action cleanup had no observed failure. Git keeps
  the history; any recurrence should return as a scoped card.
- Added `horus fleet --review`: local clones are fetched and remote PRD/cards are
  read through Git objects without pulling; missing clones use authenticated
  read-only GitHub access when possible.
- The review separates REMOTE SHIPPED TRUTH from LOCAL WORKING STATE, counts
  source commits newer than continuity, and labels unstructured backlogs instead
  of guessing.
- Added an optional Fleet Review TUI item/shortcut and ordinary curator-session
  launch; direct project launch remains first/default.
- Bundled `fleet-curation` for evidence-first recommendations and explicit owner
  approval before cross-project continuity edits.
- Gate: 1,440 tests passed; live CLI returned six projects; noninteractive TUI
  render showed all six plus the curator action and both truth labels.

## Next

- Merge this feature PR, install it, and ask the owner before starting
  `auto-merge-bypasses-freshness-gate`.
