---
date: 2026-07-13T14:20:01
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "natural Termius scrolling and account window lines v0.0.50"
---

# natural Termius scrolling and account window lines v0.0.50

## Summary

Used the owner's second Termius result to correct the input model rather than adding
another inversion. Shipped v0.0.50 with conventional phone/desktop scrolling and the
requested vertical account-window presentation.

## Key Points

- Field evidence established that Termius already emits Up for pull-down and Down for
  swipe-up. Horus's narrow-SSH inversion was fighting that correct client translation;
  automatic inversion is now removed, with `HORUS_TUI_INVERT_SCROLL=1` opt-in only.
- Account rows now render the name alone, followed by one `5h` line and one `weekly`
  line; each reset stays on its matching window. Two/four-space indentation makes
  `weekly 83%, resets 2026-07-17 09:59` fit exactly at 39 columns.
- Live 39x20 SSH-like PTY showed the requested account layout, Down advancing through
  projects, and Up returning to the full Accounts rail. A 120x36 probe retained the
  wide account/project columns with the same window-line structure.
- PR #207 merged at `66c71cc`; release PR #208 merged at `cadeb3e`; 1,274 tests passed
  before and after the bump. v0.0.50 published, exact-merge CI and three-OS install
  smoke passed, and hosted deploy reports 0.0.50 while `/` remains gated with 403.

## Next

- Owner verifies gesture direction and account formatting in Termius. On PASS, exercise
  two-session detach/reattach, then return to orphan-process reaping.

## Checkpoints (auto-harvested)

- `66c71cc` Restore natural terminal scrolling (#207)
- `cadeb3e` Release 0.0.50 (#208)
- `5a78ad9` Update continuity for natural Termius scrolling v0.0.50 (#209)
