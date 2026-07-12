---
status: shipped
priority: high
tier: sonnet
created: 2026-07-12
created_by: diagnosis-session
parallel: exclusive
surface: horus/dashboard.py, horus/pty_host.py, horus/pty_session.py
supersedes: mobile-terminal-legibility, mobile-terminal-interaction-regression
proposal_doc: docs/terminal-mobile-desktop-diagnosis.md
shipped_pr: 171
shipped_sha: 68b41252f6cc00581ce632b80a08cd7d53e765cf
shipped:
---

# Mobile/desktop terminal: sizing + lifecycle + controls hardening

**[epic / redesign]** Consolidates ~8 owner-reported terminal UX symptoms
(phone + desktop, 2026-07-12) onto their shared root causes and one coherent
redesign. **Full diagnosis + live-repro evidence + redesign:**
`docs/terminal-mobile-desktop-diagnosis.md`. This card supersedes and links two
existing cards (see *Folds in* below) — their history stays for provenance.

> This card is the *authorized-implementation* target. The diagnosis doc is a
> proposal; the overseer reviews it and the owner authorizes implementation before
> any terminal behavior changes. Docs landed first (PR: "Diagnosis: mobile/desktop
> terminal sizing & lifecycle (proposal, no impl)").

## Root causes (confirmed; see doc §3 for the symptom→cause map)

- **A** heuristic `matchMedia('(pointer:coarse)')` read once at load, never
  re-evaluated (dashboard.py:3291) — mobile state persists onto desktop.
- **B** no `ResizeObserver`; only `window.resize` (3282) — host-box changes that
  aren't a window resize (orientation, soft keyboard, PWA chrome) never refit.
  *Live-confirmed:* forcing host 420→160px posted no resize until a window resize.
- **C** deferred `setTimeout(sync,30)` (3215) fits before layout settles and locks a
  stale/default size; PTY persists last dims. *Live-confirmed:* desktop load posted
  **80×24 (default), not the fitted 136×28**.
- **D** fullscreen overlay (`position:fixed;inset:0;z-index:200`, 716) covers the
  out-of-pane `.term-tabs` strip. *Live-confirmed:* tabs unreachable in fullscreen.
- **E** keybar and auto-fullscreen use *different* triggers (`||innerWidth<800` vs
  coarse-only) → inconsistent touch state.
- **F** `.xterm-host` is a fixed box (420px / 62vh), not a fill-the-region flex child.
- **G** `× close` kills the live process with no confirmation (3276); pop-out opens a
  new window with no in-page way back.

## Symptoms folded in (owner, 2026-07-12)

1. Glyphs scramble / not responsive / fixed size → **F + C + B** (glyph-scramble half
   = renderer-at-high-DPR, *device-verify only*).
2. Mobile accepts no input on hosted app → **separate family** (exposed-mode / Access
   / same-origin POST gate) — *not* the sizing cluster; investigate on the exposed
   host. Keep + strengthen the existing input-failure surfacing (3135).
3. Touch scroll leaks to the page → missing `overscroll-behavior`/`touch-action`
   containment on the host.
4. Tabs hidden in fullscreen, can't switch sessions → **D**.
5. Control buttons too small/crowded → 11px `.linkbtn`s in a tight flex (697,
   3094–3102).
6. Stray close-tap kills a live session, no confirm → **G**.
7. Pop-out breaks flow on mobile, no way back → **G**.
8. Desktop-after-mobile stays mobile size → **A + B + C**. *Refuted:* a genuine
   `window.resize` refits fine (42→136 live); it's the long-lived-page / no-window-
   resize path, not a stack limit.

## Proposed work (doc §5; no impl yet)

- **Sizing:** `.xterm-host` fills its region (`flex:1;min-height:0`); `ResizeObserver`
  + `visualViewport` refit; layout-settled initial fit that never commits the 80×24
  default.
- **State:** live `matchMedia` change listener (re-evaluate, don't latch); one
  compact/touch-mode predicate for keybar *and* fullscreen; tabs reachable in
  fullscreen; scroll containment on the host.
- **Controls:** larger spaced tap targets; confirm/guard `× close` when the session
  is alive; make pop-out reversible (prefer in-app fullscreen on touch; keep the tab).

## Genuine constraints (doc §5.4)

- Server-side PTY holds **one** geometry per terminal (pty_host.py:46–47) — multiple
  viewers of different sizes fight over it (last-writer-wins). Debounce refits and
  define resize ownership (focused viewer owns it).
- Renderer/glyph legibility, touch-scroll, soft-keyboard, and the #2 input regression
  are **owner-only, on-real-device** verification — do not claim fixed from headless.

## Execution note

One focused pass on `dashboard.py` covers the sizing+lifecycle+controls cluster
(1,3,4,5,6,7,8) — localized to the terminal CSS + `_XTERM_ATTACH_JS` +
`_TERMINAL_JS`, all shared state, so do them together, not as 8 point-fixes. Symptom
**2 (no input)** is a separate investigation (its own card, below) on the exposed
POST path. `parallel: exclusive` on the three terminal files. Tier: Sonnet; a
reusable CDP repro harness exists (doc §7) as the in-repo gate; device checks are
owner-only.

## Folds in (history preserved, not deleted)

- **`mobile-terminal-legibility.md`** — the "glyphs scramble / not responsive / fixed
  size" bug (symptom 1). Marked folded-in; its renderer + responsive-container
  hypotheses are carried into doc §5.1.
- **`mobile-terminal-interaction-regression.md`** — the "no input on hosted app" bug
  (symptom 2). Marked folded-in for tracking, but kept as the **distinct** exposed-
  mode / POST-path investigation; the redesign does not solve it.
