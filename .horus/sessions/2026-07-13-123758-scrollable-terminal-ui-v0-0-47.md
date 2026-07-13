---
date: 2026-07-13T12:37:58
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "scrollable terminal UI v0.0.47"
---

# scrollable terminal UI v0.0.47

## Summary

Reproduced the Termius failure where a phone scroll gesture sent down-arrow bytes to
the terminal launcher's `input()` prompt and printed `^[[B`. Replaced the real-TTY
surface with a full-screen, internally scrolling UI shared by phone and desktop,
then shipped it as v0.0.47.

## Key Points

- The new `prompt_toolkit` surface lists projects, next actions, accounts, and live
  sessions; arrows/`j`/`k`, Page Up/Down, Termius swipe bytes, and mouse wheel input
  move the highlighted row while the viewport follows it.
- Launch, attach, and close actions still call the existing tracked current-TTY/tmux
  substrate. The alternate screen exits before a blocking agent command and returns
  afterward; injected-input and non-TTY callers retain the old deterministic path.
- The targeted test feeds the literal `ESC [ B` byte sequence. A live 39x15 PTY probe
  sent three such sequences, observed the selection scroll from `horus-harness` to
  `horus-hub` with no raw escape text, and verified that `q` restored the shell.
- Verification: 1,265 tests passed locally and again after the version bump; clean
  wheel build/install included `prompt-toolkit`; PR #198 merged at `5e1148e`; release
  PR #199 merged at `43fe609`; Python 3.12/3.13 PR gates passed.
- v0.0.47 published successfully and installed from PyPI on Windows, macOS, and Linux
  with console-script and dashboard-health probes green. Mandatory hosted deployment
  reports 0.0.47 at `/health`, while `/` remains gated with 403.
- The framework's mouse-handler API differed from the initially assumed constructor
  hook; the targeted gate caught it before commit, and a control subclass now owns
  wheel-to-selection mapping.

## Next

- Owner tests v0.0.47 in Termius: swipe/down-arrow scrolling, project open/back,
  account selection, and absence of `^[[B`. On PASS, choose the next responsive
  desktop/launch-sheet slice or return to orphan-process reaping.

## Checkpoints (auto-harvested)

- `5e1148e` Add scrollable terminal project UI (#198)
- `43fe609` Release 0.0.47 (#199)
- `89676b8` Update continuity for scrollable terminal UI (#200)
