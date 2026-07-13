---
date: 2026-07-13T13:57:23
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "responsive terminal TUI scrolling v0.0.49"
---

# responsive terminal TUI scrolling v0.0.49

## Summary

Reproduced the owner's desktop/mobile home-screen constraints and shipped v0.0.49.
The terminal cockpit now reflows across desktop and phone widths, returns from project
scrolling to account KPIs, and translates the arrow bytes Termius actually emits.

## Key Points

- Root cause 1: prompt_toolkit kept the first project cursor visible but did not reset
  the viewport to line zero, so Accounts remained above the reachable viewport after
  scrolling. Returning to project 1 now explicitly restores the home scroll position.
- Root cause 2: the earlier inversion handled only mouse events, while Termius swipe
  gestures arrive as Up/Down escape sequences. Narrow SSH now inverts both paths;
  physical `j`/`k` navigation stays conventional and an environment override remains.
- All screens now wrap responsively, the empty status row disappears when unused, and
  the mobile footer fits. At 96+ columns, accounts render in up to three columns and
  projects in two; below that threshold the same running TUI switches to a stacked view.
- Live PTY gates: 120x36 rendered three account/two project columns; resizing that same
  process to 39x20 reflowed cleanly; a narrow SSH probe drove Up bytes down the project
  list and Down bytes back to the full account rail.
- PR #204 merged at `44037a0`; release PR #205 merged at `ccbd41a`; 1,273 tests passed
  before and after the bump. v0.0.49 published, install smoke passed on Windows/Linux/
  macOS, and hosted deploy reports 0.0.49 while `/` remains gated with 403.

## Next

- Owner verifies desktop resize/zoom, reversible Accounts scrolling, and touch direction
  in Termius. On PASS, exercise two-session detach/reattach, then return to orphan reaping.

## Checkpoints (auto-harvested)

- `44037a0` Fix responsive terminal TUI scrolling (#204)
- `ccbd41a` Release 0.0.49 (#205)
- `fd041e1` Update continuity for responsive terminal v0.0.49 (#206)
