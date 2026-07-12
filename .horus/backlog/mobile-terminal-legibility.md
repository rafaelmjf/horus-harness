---
status: folded-in
priority: high
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: exclusive
surface: horus/dashboard.py
folded_into: mobile-terminal-ux-hardening
shipped:
---

> **FOLDED IN (2026-07-12) → `mobile-terminal-ux-hardening.md`** (symptom 1). The
> diagnosis session confirmed this is the fixed-host-box + deferred-fit + no-refit
> cluster (root causes F/C/B; live-reproduced), with the glyph-scramble half a
> device-only renderer question. History kept here for provenance; do not action
> this card on its own — implement via the consolidated card. See
> `docs/terminal-mobile-desktop-diagnosis.md`.

# Hosted terminal is not mobile-responsive (glyphs scramble, fixed size)

**[bug]** Owner report (2026-07-12) on the live hosted dashboard
(`horus.rafaelfigueiredo.com` → `horus-dashboard.service`, port 8771 — the harness
dashboard's own embedded xterm.js PTY viewer, per `docs/exposed-dashboard-cutover.md`):

- **Desktop:** the terminal renders at a fixed size that **doesn't fill the space
  reserved for it** (usable, but not filling).
- **Phone:** **barely usable** — glyphs overlap/scramble and lines are cut off.

## Likely causes (overseer read of `horus/dashboard.py`)

- `.xterm-host { height: 420px }` (and `62vh` under the mobile media query) is a
  **fixed height** that doesn't grow to fill the pane → the "doesn't fill reserved
  space" symptom. Make the terminal host fill its container responsively and refit.
- **No xterm `rendererType` override** on the `Terminal({...})` options → the default
  canvas/webgl renderer **overlaps glyphs at high mobile `devicePixelRatio`** — the
  classic cause of "letters scramble together." Try `rendererType: 'dom'` (crisp on
  mobile) and confirm the FitAddon re-runs on resize/orientationchange so cols/rows
  match the phone width (fixes the cut lines).

xterm assets already served: `/assets/xterm/xterm.js` + `xterm-addon-fit.js`. The fit
addon is present; the gap is renderer choice + a responsive container + a refit on
resize.

## Overlap (READ BEFORE CLAIMING)

Same surface as **`mobile-terminal-interaction-regression.md`** (no-keyboard-input
bug), which is `parallel: exclusive` on `horus/dashboard.py`/`pty_host.py`/
`pty_session.py`. These are **distinct bugs** (rendering/legibility here vs. input
there) but on the same terminal — do NOT run them concurrently; sequence them, or
fix both in one dispatch since a worker in `dashboard.py` is already there.

## Verification

Code/CSS change is the worker's in-repo gate, but the visual **"is the phone actually
usable now?" check is OWNER-ONLY** (needs the deploy box + a real phone). Do not claim
the mobile UX fixed from code alone — state that live+phone verification is pending owner.

## Provenance

Re-dropped here after a dispatched hub worker caught that the original card
(`horus-hub` `mobile-terminal-responsiveness`) had a stale premise — it blamed the hub's
routed ttyd, but that path is retired dormant Lane B on a separate hostname; the live
terminal is this dashboard's embedded xterm. Worker wrote no config and stopped to flag.
