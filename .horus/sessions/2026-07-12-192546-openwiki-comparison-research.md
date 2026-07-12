---
date: 2026-07-12T19:25:46
agent: codex
account: personal
environment: host
project: horus-harness-wt-research-openwiki-comparison
status: complete
summary: "OpenWiki comparison research"
---

# OpenWiki comparison research

## Summary

Researched LangChain's newly released OpenWiki against Horus's PRD continuity and
deterministic capability catalog. Wrote the requested three-section sourced note and
recommended skip-but-watch rather than adding a dependency or competing doc engine.

## Key Points

- Verified OpenWiki's local Markdown wiki, managed instruction blocks, scheduled
  diff-driven documentation PRs, interactive CLI, MIT license, and 0.1-era maturity
  from first-party launch, repository, source, workflow, and release material.
- Could not verify long-run documentation fidelity, large-repository cost, private-code
  operating evidence, independent evaluations, or a stable structured query API.
- Named the revisit gate: stable 1.x code mode plus evidence across at least 30 merged
  changes in a private polyglot repository; only then run an opt-in measured pilot.
- Verification: exact required headings asserted, one recommendation asserted, and
  `git diff --check` passed.

## Next

- Open the research PR and stop without merging. After merge, stamp
  `openwiki-vs-self-documenting-research` shipped with its PR and merge SHA.

## Checkpoints (auto-harvested)

- `4822d2b` Update Horus continuity (closure)
- `8fc762c` Research OpenWiki fit for Horus continuity (#177)
  Card: openwiki-vs-self-documenting-research
  Compares OpenWiki against the Horus PRD-continuity + capability-catalog approach. Overseer + owner reviewed and endorsed: skip-but-watch — no dependency, no competing doc engine now. Revisit trigger: OpenWiki reaches a stable 1.x code mode with evidence across 30+ merged changes in a private polyglot repo, via an opt-in measured pilot.

- `a2f9882` fix(terminal): surface gone PTY sessions instead of silently swallowing input
  Root cause of the mobile "terminal accepts no input" regression: a stale viewer
  (page/PWA kept alive across a hosted-dashboard restart, which kills every PTY)
  hit two silent failure paths at once:
  - POST /pty/input and /pty/resize ignored pty_host's False return and replied
    204 for unknown/dead terminals, so keystrokes vanished into a black hole and
    the client's rejected-input notice (36412bf) never fired.
  - /pty/stream for an unknown id yields "status: unknown", which the viewer JS
    silently ignored — EventSource then reconnected forever (each attempt a fresh
    200 + unknown), so the stream-disconnected notice never fired either.
  Now: input/resize to a gone terminal return 410 (resize gated on existence, not
  its return value — False also means debounce-drop); the viewer handles 410 and
  the 'unknown' frame with a one-time visible "[session gone]" notice, marks the
  tab exited, closes the EventSource (ends the reconnect loop), and stops posting.
  The generic network-error notice now also names the expired-access-session case.
  Not Claude Code-specific: the transport is TUI-agnostic (codex was equally
  affected). Investigation notes + on-phone diagnostic tree folded into
  .horus/backlog/mobile-terminal-interaction-regression.md; the separate
  claude-vs-codex rendering gap is tracked in terminal-claude-rendering-levers.md.

- `4e40bbc` fix(terminal): surface gone PTY sessions instead of silently swallowing input (#178)
  Root cause of the mobile "terminal accepts no input" regression: a stale viewer
  (page/PWA kept alive across a hosted-dashboard restart, which kills every PTY)
  hit two silent failure paths at once:
  - POST /pty/input and /pty/resize ignored pty_host's False return and replied
    204 for unknown/dead terminals, so keystrokes vanished into a black hole and
    the client's rejected-input notice (36412bf) never fired.
  - /pty/stream for an unknown id yields "status: unknown", which the viewer JS
    silently ignored — EventSource then reconnected forever (each attempt a fresh
    200 + unknown), so the stream-disconnected notice never fired either.
  Now: input/resize to a gone terminal return 410 (resize gated on existence, not
  its return value — False also means debounce-drop); the viewer handles 410 and
  the 'unknown' frame with a one-time visible "[session gone]" notice, marks the
  tab exited, closes the EventSource (ends the reconnect loop), and stops posting.
  The generic network-error notice now also names the expired-access-session case.
  Not Claude Code-specific: the transport is TUI-agnostic (codex was equally
  affected). Investigation notes + on-phone diagnostic tree folded into
  .horus/backlog/mobile-terminal-interaction-regression.md; the separate
  claude-vs-codex rendering gap is tracked in terminal-claude-rendering-levers.md.
- `6a250ff` release: v0.0.36 — terminal stale-session input fix (410 + session-gone surfacing) + mobile terminal UX hardening

- `6ebc555` fix(terminal): mobile rendering — xterm 6.0.0, 16px compact font, real scroll containment (#179)
  Fixes the three on-phone symptoms reported against the live hosted terminal:
  - Glyphs scrambled / cursor drawn over text mid-screen: iOS zooms the page when
    a focused input's font-size is under 16px; xterm's hidden helper textarea
    carries the 13px cell font, so every keyboard focus sheared the CSS-pixel
    grid. Compact mode now renders at fontSize 16 (tracked live on
    horus:compactchange, refit after), which removes the zoom trigger and is more
    legible at phone DPR anyway.
  - Page scrolls under the terminal: containment sat on .xterm-host, which never
    scrolls — overscroll-behavior only stops chaining on the element that
    actually scrolls, and touch-action:pan-y explicitly let the browser own
    vertical drags. Containment now also on .xterm-viewport (the real scroller)
    and the host is touch-action:none; xterm's own touch handlers still receive
    the events.
  - Vendored xterm upgraded to @xterm/xterm 6.0.0 + @xterm/addon-fit (was a
    pre-@xterm-scope 5.x bundle): years of mobile/helper-textarea fixes, and the
    new bundle supports DEC mode 2026 synchronized output, so Claude Code's
    flicker-free rendering path can actually engage in this viewer.
  Verified with the CDP repro harness (scripts/terminal-repro) on the real
  markup/CSS/JS + new bundle: all sizing/lifecycle/controls checks green, plus
  two new checks (compact >=16px font; containment on .xterm-viewport). 1236
  pytest tests pass. On-device legibility/scroll check remains owner-only.
- `caeb43a` release: v0.0.37 — mobile terminal rendering (xterm 6.0.0, 16px compact font, viewport scroll containment)

- `4e19383` fix(terminal): viewers re-claim PTY geometry; touch-drag scrolls via wheel pipeline (#180)
  The on-phone "letters not distributed properly" screenshot showed crisp glyphs
  wrapped at the wrong column — a PTY-vs-viewer geometry mismatch, not a renderer
  bug: one PTY geometry serves all viewers (last writer wins), and a viewer whose
  own box never changed could never re-post its fit (key!==lastSent suppressed
  it), so a phone attached after a desktop viewer stayed stuck rendering a ~90-col
  grid at 44 cols with mid-word wraps and a column of orphan glyphs.
  - claimSize(): drop the lastSent guard and refit when a viewer becomes the one
    the user is actually looking at — visibilitychange->visible, window focus,
    pageshow (bfcache/PWA resume), or touching the terminal. The TUI redraws for
    the claiming viewer (last-focused-wins ownership, per the diagnosis doc's
    acknowledged shared-PTY constraint).
  - Touch-drag on the host now translates into synthetic WheelEvents aimed at the
    xterm screen, so xterm's wheel pipeline applies its usual semantics: scrollback
    scrolling in the normal buffer, alternate-scroll arrows for full-screen TUIs
    that enable it — same as a desktop mouse wheel. Previously the drag scrolled
    nothing (containment fixed the page leak, but nothing routed the gesture).
  CDP harness: two new Phase 5 checks — pageshow re-posts an unchanged fit, and
  CDP-dispatched touch drags emit correctly-signed synthetic wheel events. All 21
  checks green; 1237 pytest tests pass.
- `eb5e915` release: v0.0.38 — terminal multi-viewer geometry claim + touch-drag scrolling

- `6811016` fix(backlog): lazy fcntl import — top-level import broke horus entirely on Windows (#181)
  PR #172's claim-lock added `import fcntl` at backlog.py module top; fcntl is
  Unix-only, so every `horus` CLI invocation on Windows died with
  ModuleNotFoundError (install-smoke red on v0.0.36-v0.0.38; v0.0.35 was green).
  Import it inside _claim_lock like pty_session already does, degrading the
  claim guard to advisory where flock doesn't exist — matching its intent
  (best-effort TOCTOU protection), not a correctness invariant. Regression test
  simulates the Windows path by blocking the fcntl import.

- `56feda0` feat(terminal): smallest-wins PTY geometry across simultaneous viewers (#182)
  With a desktop tab and a phone watching the same session, last-writer-wins
  geometry meant whichever viewer claimed last rendered cleanly while every
  repaint scattered across the other's grid (owner screenshot: interleaved
  fragments, same lines painted at two widths). One PTY has one size — two
  visible viewers of different sizes can't both win under claim semantics.
  Adopt tmux's answer: each viewer registers the size it fits under a viewer id
  (vid), and the PTY takes the per-dimension MINIMUM over registered viewers —
  every screen renders the full grid; larger viewers get margins. Viewers drop
  out when their SSE stream dies (subscribe teardown backstop) or when they
  report hidden via the new /pty/release (sendBeacon on visibilitychange/
  pagehide), so a backgrounded desktop tab stops constraining the phone.
  - pty_host: per-terminal viewer registry; viewer_resize/viewer_release;
    subscribe(viewer_id=...) releases on disconnect.
  - dashboard: /pty/resize routes vid posts through the registry (no-vid posts
    keep legacy direct-set for pre-vid pages still open); /pty/release route;
    /pty/stream ties the vid to the stream for cleanup.
  - attach JS: per-viewer vid; release on hidden/pagehide, re-register on
    visible/focus/pageshow/touch (claimSize now means "ensure I'm registered",
    not "steal the size").
  1245 tests pass (viewer min/release/disconnect + route + JS wiring coverage);
  CDP harness 21/21.
- `e0e7764` release: v0.0.39 — smallest-wins multi-viewer terminal geometry + Windows fcntl fix

- `4b81c1f` feat(terminal): journald diagnostics for PTY geometry posts (#183)
  One stderr line per /pty/resize and /pty/release with the poster (vid or
  LEGACY pre-vid page), the posted size, the resolved effective geometry, and
  the current viewer registry — so a multi-viewer geometry fight is
  reconstructable from journalctl instead of guessed from phone screenshots.
  Field evidence tonight: a smallest-wins pin to 38x26 was stomped to 80x24 by
  an unidentified poster; this names the culprit next time.
- `0dc4171` release: v0.0.40 — PTY geometry diagnostics (journald)

- `af80751` fix(terminal): geometry-epoch scrollback + attach handshake — stop poisoning viewers (#184)
  Journald diagnostics (v0.0.40) proved the registry works: phone registered
  38x26, desktop 164x23, effective 38x23 — yet the phone stayed scrambled while
  the desktop rendered the SAME bytes cleanly. Root cause: attach replays the
  whole scrollback, including bytes emitted for earlier grids; a 38-col viewer
  wraps 80/164-col-era lines differently than the TUI assumed, corrupting the
  cursor bookkeeping, and every later relative move compounds it — the screen
  never recovers. Wide viewers never wrap, so the desktop is immune. (Also
  caught live: xterm's 80x24 constructor default posted before the first fit.)
  - Geometry epochs: an APPLIED resize clears the host scrollback buffer (the
    TUI full-repaints on SIGWINCH anyway), so attaches replay only bytes
    consistent with the current grid.
  - Attach handshake: subscribe announces `event: geometry` first; a viewer
    whose fit differs resets its screen (term.reset()) and POSTs /pty/redraw —
    a double-TIOCSWINSZ jiggle (tmux's refresh trick) that makes the TUI paint
    a fresh frame at the viewer's just-posted size.
  - fitted-gate: onResize posts are ignored until the first successful fit, so
    the 80x24 default can never brief-resize the shared PTY again.
  1249 tests pass; CDP harness 21/21.
- `efb2a79` release: v0.0.41 — terminal geometry-epoch scrollback + attach handshake
