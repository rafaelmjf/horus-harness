---
status: shelved
shelved_on: 2026-08-01
priority: medium
created: 2026-07-29
created_by: agent
readiness: shaping
readiness_reason: "The gap is measured, not suspected — but the fix is a real trade-off (a CI job that installs a third-party binary, versus accepting demonstration-only confidence for an opt-in host). Wants an owner decision on which, not a refinement pass."
phase: explore
type: chore
tier: medium
parallel: safe
vision_facet: "Distribution"
surface: .github/workflows/tests.yml (an optional-host job), tests/test_hosts_herdr.py (the skipped live test), horus/hosts/herdr.py
---

# optional-host-ci-coverage — CI cannot exercise the herdr host at all

## Why — measured on 2026-07-29, the day the herdr host shipped

herdr is not installed on the GitHub runner, so **every herdr code path is unexercised
by CI**. The live test in `tests/test_hosts_herdr.py` skips there by design, and the
unit tests all stub `_run`, which proves the argv Horus *sends* and nothing about what
herdr does with it.

That is not a theory about risk. In one day:

- A **pre-release sweep by hand** found seven host-selection bugs, three of which
  (`launch_window` skipping `ensure_ready`, `pty_host` gating on one host and launching
  on another, `launch_detached_run` ignoring its target) were invisible to a green suite.
- The owner's **first real trial** of `uv run horus tui herdr` found two more that every
  programmatic check had passed: the cockpit attaching to a dead pane, and the cockpit
  running a different Horus than the caller.
- A **second trial** found a third: `new-window` popping a native window that duplicated
  the cockpit.
- And two shipped strings named tmux where any host now works — including a `Ctrl-b L`
  hint that does nothing on herdr.

Ten defects, none caught by CI, all in paths CI structurally cannot reach.

## The trade-off, which is why this is a decision and not a task

**Add an optional-host CI job** — install herdr on the runner (a single static binary
from a release asset) and run the live tests. Buys real regression protection on the one
host that has none. Costs: a third-party binary in CI, a job that breaks when herdr
changes its CLI (which it will — the API is young), and a version-pinning question.

**Or accept demonstration-only confidence** and say so. herdr is opt-in and `auto`
resolves to tmux, so nobody who has not deliberately switched is exposed. This is the
status quo, and it is defensible — but it means "the suite is green" carries less
meaning for one host than for the other two, and nothing currently records that where a
reader would see it.

A third, cheaper option: keep CI as-is but make the herdr host's *contract* testable —
record real herdr responses as fixtures (the probe already captured several) and replay
them, so a herdr CLI change that breaks parsing fails locally even without the binary.

## Acceptance (draft — sharpen once the option is chosen)

- Whichever option is taken, the confidence asymmetry between hosts is stated somewhere
  a reader meets it: the README's host table, the herdr host's module docstring, or both.
- If the CI job is built: it is non-blocking on herdr being unreachable (a download
  failure must not red the suite for unrelated work), and it pins a herdr version so an
  upstream CLI change is a deliberate bump rather than a surprise red.
- If fixtures are chosen: they are captured from a real herdr and dated, so a stale
  fixture is visible rather than silently authoritative.

## Open decisions

- Which of the three options. [session] — a judgment about how much the herdr path is
  worth defending, which depends on whether the owner keeps using it.
- Whether the same reasoning applies to any other optional dependency (Codex CLI, tmux
  itself on macOS runners). [refine] — probably yes for the principle, no for the effort.

## Source

Session of 2026-07-29 that built the three-host layer and released 0.0.78. The lesson is
recorded in that release's continuity; this card is the place to act on it.
