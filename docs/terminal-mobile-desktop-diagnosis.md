# Diagnosis: hosted terminal sizing & lifecycle (mobile + desktop)

> **Status: proposal / diagnosis only.** This document contains no implementation.
> It explains the ~8 reported terminal symptoms in terms of their shared root
> causes and proposes one coherent redesign. The overseer reviews it and the owner
> authorizes implementation separately. Consolidated backlog card:
> `.horus/backlog/mobile-terminal-ux-hardening.md`.

Author: diagnosis session, 2026-07-12. Surfaces read: `horus/dashboard.py`
(terminal CSS ~697–746; `_XTERM_ATTACH_JS` defining `window.horusAttachTerm`
3123–3219; `_TERMINAL_JS` controller 3221–3297; `render_pty_term_page` 3300–3318;
`/pty/*` routes ~4289–4312), `horus/pty_host.py` (`resize` 165–174, `start`/persistence),
`horus/pty_session.py` (`resize` → `TIOCSWINSZ`).

---

## 1. What the terminal is (so the fix stays in scope)

The in-app terminal (`target=='app'`) is a **viewer** of a host-owned PTY. The
`claude`/`codex` TUI runs under a pseudo-terminal in `pty_host` (one dashboard
process); bytes stream to the browser over SSE (`/pty/stream`), and keystrokes +
resizes POST back (`/pty/input`, `/pty/resize`). The PTY **persists on the host
independent of any viewer** — that is what lets a reload, a second window, or the
pop-out re-attach to the same live screen.

Two browser surfaces share one attach function (`window.horusAttachTerm`):

- the in-panel tabs on `/` Control (`_terminal_panel` + `_TERMINAL_JS`), and
- the standalone pop-out page (`render_pty_term_page`).

Sizing is: `sync()` → `fit.fit()` (xterm FitAddon computes cols/rows from the host
element box) → `post('/pty/resize', {cols, rows})` → `pty_host.resize` →
`pty_session.resize` → `TIOCSWINSZ` on the PTY master. **The stack can reflow.** The
bugs are in *when* and *from what box* the fit is triggered, plus control-layout and
lifecycle gaps — not a limitation of the resize plumbing.

---

## 2. Live reproduction (headless Chromium over CDP)

I stood up a local harness that serves the **real** `_terminal_panel` markup,
`_XTERM_ATTACH_JS`, `_TERMINAL_JS`, the real terminal CSS lines from `dashboard.py`,
and the vendored xterm assets, backed by a stub PTY endpoint that logs every posted
`/pty/resize`. I drove it with `chrome-headless-shell` over the DevTools Protocol
(Node 22, no npm deps), emulating viewport + devicePixelRatio, and inspected the
actual fitted cols/rows, the `.fs`/`term-fs` state, and the posted resize values.
(The fit addon derives cols/rows purely from the host box, so sizing/lifecycle
behavior reproduces faithfully even without real PTY bytes.)

**Faithful measured results** (host CSS honored — desktop `.xterm-host` 420px,
phone 62vh):

| Phase | viewport | host box | posted resize | `.fs` / `term-fs` | tabs reachable |
|---|---|---|---|---|---|
| Desktop load | 1280×900 | 1082×420 | **80×24** (default, *not* fitted 136×28) | no | yes |
| Mobile load | 390×844 | 348×523 | 42×34 (fits) | no¹ | yes |
| Widen → desktop, **no reload** | 1280×900 | 1082×420 | **136×28** (refit fired) | no | yes |
| Force host 420→160px, **no window resize** | 1280×900 | 1082×160 | **(none — no refit)** | no | yes |
| Then a window resize | 1281×901 | 1082×160 | 136×**10** (now recomputes) | no | yes |
| Coarse-pointer load² | 390×844 | (fullscreen) | 45×45 (fills viewport) | **yes / yes** | **NO — covered** |

¹ Auto-fullscreen did **not** engage here because CDP `Emulation.setEmulatedMedia`
does not flip `pointer:coarse`; the keybar still appeared via the `innerWidth<800`
fallback. ² To exercise the fullscreen branch I injected a `matchMedia` override so
`(pointer:coarse)` reports `true`, matching a real phone.

### What reproduced

- **Deferred fit locks a stale/default size (Mechanism C).** On desktop load the
  terminal posted **80×24 (xterm's built-in default), not the fitted 136×28**, in a
  host that fits 136 cols. `setTimeout(sync, 30)` (dashboard.py:3215) ran the fit
  before layout settled, so the size stayed at the default until a *later* window
  resize corrected it to 136×28. This is symptom 1 on desktop ("doesn't fill the
  space reserved for it") reproduced directly.
- **No refit on a host-size change that isn't a window resize (Mechanism B).**
  Shrinking the host 420→160px produced **no `/pty/resize`**; only a subsequent
  `window.resize` recomputed rows (28→10). There is no `ResizeObserver` — only the
  `window.addEventListener('resize', …)` at dashboard.py:3282.
- **Tabs are unreachable in fullscreen (symptom 4).** With auto-fullscreen engaged,
  `elementFromPoint` at the tab-strip location returned a `<div>` inside
  `.term-pane` — the fullscreen overlay (`position:fixed; inset:0; z-index:200`,
  dashboard.py:716) covers the tab strip, which lives *outside* the pane and has no
  stacking context above it. You cannot tap another session's tab.
- **Horizontal refit on a genuine window resize works** (42→136 cols). Important
  differential: for a real `window.resize` event the stack reflows correctly.

### What did NOT reproduce headless (stated honestly)

- **Glyph scramble / legibility at high DPR (symptom 1, rendering half).** Needs a
  real display; canvas rasterization at `devicePixelRatio:3` is not observable in
  the headless shell. The "canvas renderer overlaps glyphs at high DPR" hypothesis
  from the legibility card is *plausible but unverified* here.
- **Touch-scroll leaking to the page (symptom 3).** Needs real touch input.
- **Mobile "no input" regression (symptom 2).** My harness has no auth gate, so
  input POSTs succeed. This symptom is almost certainly a *different* root cause
  family (see §4) — the exposed-mode / Access / same-origin POST path — not the
  sizing/lifecycle cluster this redesign targets.

---

## 3. Root-cause map (8 symptoms → shared causes)

Confirming/refuting the pre-supplied mechanisms and adding what the read + repro
surfaced:

- **A — touch heuristic evaluated once at load, never re-evaluated.**
  `matchMedia('(pointer:coarse)')` at dashboard.py:3291 runs one time in the IIFE and
  drives auto-fullscreen; nothing re-checks it. **CONFIRMED (static).** Live-confirmed
  that the branch engages fullscreen when coarse; the "never re-evaluated" half is
  static (the only other `toggleFs` caller is the button).
- **B — no `ResizeObserver`; only `window.resize`.** **CONFIRMED (live).** Host-box
  changes decoupled from a window resize (orientation, `visualViewport`/soft-keyboard,
  PWA chrome show/hide, display handoff, the keybar appearing) never refit.
- **C — deferred initial fit races layout; persisted PTY holds last dims.**
  **CONFIRMED (live).** `setTimeout(sync, 30)` can fit before layout settles and lock
  a stale/default size; and the PTY keeps its previous cols/rows (pty_host.py:46–47,
  169) until a viewer posts a new resize, so a fresh viewer briefly shows the last
  attach's geometry.
- **D — fullscreen overlay covers out-of-pane chrome (NEW).** `.term-pane.fs` is
  `position:fixed; inset:0; z-index:200`; the `.term-tabs` strip is a sibling of
  `.term-panes`, outside the pane, with no higher stacking context, so it is
  physically covered. **CONFIRMED (live).**
- **E — two different triggers for two touch affordances (NEW).** The keybar shows on
  `matchMedia(coarse) || innerWidth<800` (dashboard.py:3150); auto-fullscreen shows on
  `matchMedia(coarse)` only (3291). A narrow desktop window gets the keybar but not
  fullscreen; a wide coarse-pointer tablet gets fullscreen. Inconsistent, and neither
  reacts to later change. **CONFIRMED (static).**
- **F — fixed host height, not a fill-the-pane box (NEW, related to C).**
  `.xterm-host{height:420px}` / `62vh` is a hard-coded box, not `flex:1` of an
  available region (except inside `.fs`). Even a perfect fit only fills 420px, so on a
  tall desktop card the terminal is a short letterbox. **CONFIRMED (static + live: host
  measured exactly 420px on desktop).**
- **G — destructive lifecycle actions with no guardrail (NEW).** `termclose`
  (dashboard.py:3276–3281) POSTs `/pty/close` — which *kills the live process*
  (pty_host.py:183 → terminate) — and removes the tab immediately, no confirmation.
  Pop-out (3271–3275) opens a new OS window with no in-page way back. **CONFIRMED
  (static).**

### Mapping

| # | Symptom | Root cause(s) |
|---|---|---|
| 1 | Glyphs scramble; not responsive; fixed size | **F** (fixed host box) + **C** (deferred fit locks default 80×24) + **B** (no refit on later layout change); glyph-scramble half is a **renderer-at-high-DPR** hypothesis (unverified headless) |
| 2 | Mobile accepts no input on hosted app | **Separate family** — exposed-mode / Access / same-origin POST gate on `/pty/input` (see §4); *not* the sizing cluster |
| 3 | Touch scroll leaks to page under terminal | Missing scroll containment on `.xterm-host` (`touch-action` / `overscroll-behavior`); page only locks (`body.term-fs{overflow:hidden}`) *in* fullscreen — a facet of the same "terminal isn't an owned scroll region" gap as **B/F** |
| 4 | Tabs hidden in fullscreen — can't switch sessions | **D** (overlay covers the out-of-pane tab strip) |
| 5 | Control buttons too small / crowded → misclick | Control layout: three 11px `.linkbtn`s in a 12px-gap flex (dashboard.py:697, 3094–3102) — no root cause beyond styling; folds into the control redesign |
| 6 | Stray close-tap kills a live session, no confirm | **G** (destructive action, no guard) — amplified by **5** |
| 7 | Pop-out breaks flow on mobile, no way back | **G** (pop-out is a new window with no in-page return; on mobile a new tab strands the user) |
| 8 | Desktop after mobile stays at mobile size | **A** (fullscreen state persists) + **B** (host grew via a path that isn't `window.resize`) + **C** (persisted PTY dims / deferred-fit lock). **Refuted:** a genuine `window.resize` *does* refit (42→136 live), and a fresh desktop page load re-evaluates the heuristic correctly — so #8 is the long-lived-page / PWA / no-window-resize path, not a stack limit |

**Bottom line:** symptoms 1, 3, 4, 8 (and the amplifiers 5–7) collapse onto **one
sizing+lifecycle model** — *the terminal is not modeled as a self-contained, self-
observing, fill-its-region scroll surface, and its fullscreen/touch state is decided
once from a point-in-time heuristic instead of tracked.* Symptom 2 is a distinct
network/access-path bug and should be triaged separately (it is the pre-existing
`mobile-terminal-interaction-regression` card's core), though the redesign should add
the input-failure surfacing already present (dashboard.py:3135) as a first-class check.

---

## 4. Symptom 2 is out of this redesign's spine (but must be tracked)

The "no input" regression is most consistent with the exposed-mode / Cloudflare
Access / same-origin-POST changes (per the existing interaction-regression card), not
with sizing. It cannot be reproduced in a headless harness with no auth gate. The
redesign below keeps and strengthens the existing "input not delivered (status)"
surfacing so a blocked POST is never silent, but the *fix* for #2 is a separate
investigation into the POST path on the exposed host. This document flags it and the
consolidated card links it; it does not solve it.

---

## 5. Proposed redesign (one coherent model)

Four coordinated changes. No code here — this is the target behavior and the change
surface.

### 5.1 Sizing: make the terminal a self-observing, fill-its-region surface

Replace "fixed-height host + fit on window.resize + a 30ms deferred initial fit" with:

1. **Fill the region, don't pin a height.** The `.xterm-host` becomes `flex:1;
   min-height:0` inside a flex-column pane that owns a real region (a sensible
   `min-height`/`max-height` on desktop; the visual viewport on phone), instead of
   `height:420px`/`62vh`. Fixes **F**, the desktop "letterbox" half of #1, and makes
   fullscreen and inline use the same box model.
2. **Observe the box, not the window.** Attach a `ResizeObserver` to the host element
   and refit on *its* size changes (debounced), replacing sole reliance on
   `window.resize`. Fixes **B** and the #8 "grew without a window resize" path.
3. **Track the visual viewport on touch.** Subscribe to `visualViewport`
   `resize`/`scroll` so the soft keyboard and mobile browser chrome resize the
   terminal instead of overlapping it. Complements #2 for the keyboard case.
4. **Fit *after* layout, and only commit a real size.** Replace `setTimeout(sync,30)`
   with a layout-settled trigger (`requestAnimationFrame` after `term.open`, or first
   `ResizeObserver` callback) and guard the post so xterm's 80×24 default is never
   committed as a "fit" when the box is measurable and larger. Fixes **C** and the
   desktop "posted 80×24" lock reproduced above.

Optional, gated on the legibility repro the owner can run on a real phone: evaluate
`rendererType:'dom'` (or the current WebGL/canvas addon config) for the glyph-scramble
half of #1. Keep this as a *verify-on-device* item, not an assumed fix — it did not
reproduce headless.

### 5.2 Fullscreen + tabs + touch state: track it, don't decide it once

1. **Re-evaluate, don't latch.** Drive the touch/fullscreen affordances from a live
   `matchMedia('(pointer:coarse)')` **change listener** (and a `visualViewport`/resize
   signal), not a one-shot read at load. A mobile→desktop transition (or the reverse)
   updates state. Fixes **A** and the state half of #8.
2. **Unify the two triggers.** One "compact/touch mode" predicate feeds both the
   keybar and the fullscreen default, so they can't disagree. Fixes **E**.
3. **Keep session-switching reachable in fullscreen.** Either lift the `.term-tabs`
   strip into the fullscreen overlay (render tabs *inside* the `.fs` pane, or a
   compact session switcher in the `term-bar`), or raise its stacking context above
   the overlay. Fixes **D** / #4 — the concrete requirement is: *with two sessions and
   fullscreen on, both tabs are tappable.*
4. **Scroll containment.** Give `.xterm-host` `overscroll-behavior: contain` and an
   appropriate `touch-action`, and route touch-drag to the xterm viewport (the code
   already concedes touch can't wheel-scroll xterm — dashboard.py:3172 — and adds
   scroll buttons; containment stops the drag leaking to the page). Fixes #3.

### 5.3 Controls: fewer misclicks, reversible actions

1. **Bigger, spaced tap targets.** The `term-bar` controls adopt the keybar's sizing
   floor (min 40–44px, real gap) instead of 11px `.linkbtn`s. Fixes #5.
2. **Confirm the destructive one.** `× close` kills a live process (pty_host
   `close`→`terminate`). Gate it: a confirm step (or a two-tap "tap again to end")
   **when the session is still alive**; an already-exited tab closes freely (it's just
   removing dead scrollback). Fixes #6. Put the guard in the handler, not in the user's
   attention.
3. **Make pop-out reversible / less trap-like on mobile.** On touch, prefer in-app
   fullscreen (the same box model as 5.1) over `window.open`; if pop-out is kept,
   the panel keeps its tab (it already can re-attach — the PTY persists) so there is
   an obvious way back. Fixes #7.

### 5.4 Genuine constraints (called out honestly)

- **PTY holds one geometry for all viewers.** `pty_host` stores a single `cols/rows`
  per terminal (pty_host.py:46–47) and every viewer's fit posts to it. Two viewers of
  different sizes (panel + pop-out, or two devices) will fight over the PTY size —
  last writer wins. This is inherent to a shared server-side PTY; the redesign should
  *acknowledge* it (e.g. the active/focused viewer owns the resize, or accept last-
  writer-wins) rather than pretend per-viewer sizing is free. Not a blocker for the 8
  symptoms, but the fit-on-observe change makes cross-viewer resize chatter more
  frequent, so debounce and a clear ownership rule matter.
- **Renderer/legibility is device-dependent.** The glyph-scramble fix can only be
  *confirmed* on a real phone; keep it verify-gated.

---

## 6. Change surface & rough effort (no implementation here)

| Area | File / symbol | Change shape | Effort |
|---|---|---|---|
| Sizing box model | `dashboard.py` terminal CSS ~711–729 | `.xterm-host` fill-region; unify fs/inline box | S |
| Self-observing fit | `_XTERM_ATTACH_JS` `sync`/init ~3189, 3215 | `ResizeObserver` + `visualViewport` + layout-settled fit + guard default | M |
| Heuristic tracking | `_TERMINAL_JS` ~3291, keybar predicate ~3150 | live `matchMedia`/viewport listeners; one compact-mode predicate | M |
| Tabs in fullscreen | `_terminal_panel` markup 3092–3104 + `.fs` CSS 714–719 + `_TERMINAL_JS` `toggleFs`/`activate` | tabs reachable in `.fs` (lift or restack) | M |
| Scroll containment | terminal CSS | `overscroll-behavior`/`touch-action` on host | S |
| Controls sizing | markup 3094–3102 + `.linkbtn` CSS 697 | larger spaced targets | S |
| Close confirmation | `_TERMINAL_JS` `termclose` 3276–3281 | guard when alive | S |
| Pop-out reversibility | `_TERMINAL_JS` popout 3271–3275 | touch → in-app fs; keep tab on pop-out | S–M |
| (separate) Input regression #2 | `pty_host`/exposed POST path | investigate Access/same-origin gate | — (own card) |

Overall: **one focused implementation pass on `dashboard.py`** for the sizing +
lifecycle + controls cluster (symptoms 1,3,4,5,6,7,8), plus a **separate** investigation
for the input regression (2). Estimated **M** as a single dispatch (the changes are
localized to three JS/CSS blocks and share state), with an **owner-only on-device
verification gate** for the legibility/glyph and touch-scroll halves.

---

## 7. Verification plan (for the implementation phase, later)

- **Repro harness (reusable):** the CDP driver used here asserts, per phase, the
  posted `/pty/resize` and the `.fs`/tab-reachability state. Post-fix expectations:
  desktop load posts the *fitted* size (not 80×24); host-height change without a
  window resize *does* refit (ResizeObserver); coarse-load fullscreen keeps both tabs
  tappable; a mobile→desktop `matchMedia` change drops fullscreen and refits.
- **Owner-only, on real phone (cannot be claimed from code):** glyph legibility at
  device DPR, touch-scroll containment, soft-keyboard behavior, and the input
  regression on the exposed host. State these as pending owner verification — do not
  mark #1's rendering half or #2 fixed from headless evidence.
