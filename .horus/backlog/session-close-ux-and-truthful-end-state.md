---
status: open
priority: high
created: 2026-07-31
created_by: owner
readiness: shaping
readiness_reason: "The defect and the evidence are settled, but the design is not: closure arrives by four different paths with four different fidelities, and it is undecided how much the native-host paths should be instrumented versus simply left honest-but-vague. Needs a working session to settle that, plus the Codex/herdr state read."
phase: converge
type: feature
tier: medium
parallel: safe
vision_facet: "Dashboard / cockpit"
surface: horus/registry.py (TERMINAL + status vocabulary), horus/terminal_sessions.py (stop_session, reap_orphans, reconcile), horus/terminal_tui.py (Sessions view rendering), horus/dashboard.py (_SESSION_STATUS_CLASS, session rows)
---

# session-close-ux-and-truthful-end-state — a closed session must not read as a failed one

## Why — audit evidence, 2026-07-31

The cockpit is the differentiator (market scan, same date: nothing else spans
multi-agent × multi-account × multi-project) and it **misreports the owner's own
behaviour on the majority of sessions**.

Measured across every registry row since the last audit stamp:

```
36  ('failed',  'stopped')     <- the owner closed these, via the intended path
16  ('exited',  'natural')
 6  ('stale',   None)
 2  ('running', None)
 1  ('failed',  'natural')     <- an actual failure
```

**36 of 38 `failed` rows are deliberate closes — 56% of all sessions in the window.**
On the hosted dashboard these render red (`dashboard.py`, `_SESSION_STATUS_CLASS`
maps `failed` → `health-fail`) while a clean exit renders muted grey. So the surface
the owner checks daily says most of their work failed.

**This is a modelling gap, not carelessness.** `registry.TERMINAL` is
`{exited, failed, orphaned, stale}` — there was no bucket for "the owner ended this
deliberately", so `stop_session` records the truth in `termination_reason="stopped"`
and then falls back to `failed` for the status. The intent is already captured; no
surface reads it.

## The real scope: four close paths, four fidelities

Found while checking whether a native shortcut already exists (it does — tmux
`Ctrl-b &` kills the window, `Ctrl-b x` the pane; tmux has **no** default
`kill-session` binding; herdr exposes `pane close` / `tab close` and a configurable
keymap). The paths do not agree:

| How the session ends | What Horus records today | Honest? |
|---|---|---|
| TUI → Sessions → Close | `failed` + `termination_reason="stopped"` | intent captured, then discarded |
| tmux `Ctrl-b &` / `Ctrl-b x` | SIGHUP → non-zero rc → `failed` | indistinguishable from a crash |
| `exit` / `Ctrl-D` in the pane | rc 0 → `exited` | **yes — the only honest path** |
| herdr native close | herdr declares `reports_exit_code=False`, so no rc is ever seen → `stale` / `vanished` | no |

The TUI path is the **best-instrumented** of the four and the one whose signal is
thrown away. Renaming only that path would fix the majority case and leave
`Ctrl-b &` still reporting a failure.

## Intended outcome

A deliberate close is a first-class terminal state that every path can land in, and
no surface shows it as a failure.

## Broad boundaries

Likely: add `stopped` to `registry.TERMINAL`; `stop_session` sets it; the TUI and
dashboard render it neutrally (grey, like `exited`). **No backfill is needed** —
`termination_reason` already carries the truth on every historical row, so old rows
become correct the moment the surfaces read the right field.

Early non-goals: no change to *how* sessions are stopped; no new keyboard shortcut
(the owner confirmed `Ctrl-b &` already suffices, and the TUI path's value is the
recorded intent, not the keystrokes); no screen-scraping of agent UI to infer intent
(`session-agent-state-awareness` already settled that as a treadmill).

## Open decisions

- [session] How far to instrument the native paths. A tmux kill and a crash are
  genuinely indistinguishable from the exit code alone — is a pre-kill hook worth it,
  or is "we cannot tell" the honest answer for that path?
- [session] Whether herdr's `pane get` / `agent` state can distinguish a deliberate
  close from a crash, given `reports_exit_code=False`. Shares a mechanism with
  `session-agent-state-awareness`.
- [refine] Whether `orphaned` and `stale` should also be re-read now that a fourth
  terminal state exists, or left alone.
- [refine] Exact vocabulary — `stopped` vs `closed`. `stopped` matches the existing
  `termination_reason` value and `stop_session`, so it is the default unless the
  owner prefers otherwise.

## Reviews

- 2026-07-31 (owner verdict, roadmap-branches gate) — **The scope may be DELETION, not
  repair.** Owner: *"no one really looks at that, not even the agents probably (unless
  this is required for the restore or the attach). The point here is to retire that
  section from the cockpit (hosted and local apps)."* So settle first whether anything
  depends on the status column — `restore` and `attach` are the named candidates — and
  if not, **retiring the section is the preferred outcome over fixing the states**. The
  four-path table below still matters, but as evidence that the field is unreliable
  rather than as a repair specification.
- 2026-07-31 (owner constraint, same gate) — **Do not solve this by depending on herdr.**
  Owner: *"we shouldn't assume that herdr will be the only host (tmux is still the most
  stable solution so far, and the native terminal remains an option when running on
  windows)."* Any fix must hold for tmux, herdr and the native terminal alike.

- 2026-07-31 — Carded from the product audit of the same date, at owner request,
  scoped deliberately as **closing UX and information** rather than a status rename.
  The four-path table above is the reason: the owner asked whether a shortcut was
  needed, and checking showed native shortcuts already exist while *none* of the
  native paths records intent. Related: `session-agent-state-awareness` (live states,
  same surfaces), `herdr-server-shutdown-fragility` (Gated, same host).
