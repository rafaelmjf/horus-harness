---
status: shipped
priority: high
created: 2026-07-31
created_by: owner
readiness: shaping
readiness_reason: "PARTIALLY DELIVERED by #489 (v0.0.81): the one path that had a signal and discarded it now records `stopped`. What remains is undecided, not unshaped — the two native paths where no signal ever existed (a tmux kill is indistinguishable from a crash by exit code; herdr reports none), and above them the owner's standing question of whether the Sessions status column should be RETIRED rather than repaired. Needs a working session, plus the Codex/herdr state read."
topic: dashboard-cockpit
type: feature
tier: medium
parallel: safe
surface: horus/registry.py (TERMINAL + status vocabulary), horus/terminal_sessions.py (stop_session, reap_orphans, reconcile), horus/terminal_tui.py (Sessions view rendering), horus/dashboard.py (_SESSION_STATUS_CLASS, session rows)
shipped_pr: 498
shipped_sha: 3f0812d
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

- 2026-08-01 — **Partially delivered, deliberately left open.** #489 (shipped in
  v0.0.81) took the best-instrumented path only: `registry.STOPPED` joins `TERMINAL`,
  `stop_session` writes it, `is_deliberate_close(status, reason)` reads the *pair* so
  the 73 historical rows became correct with no backfill, the dashboard renders it
  muted, and `delivery.NONCLEAN_STATUSES` gained it so closing a session still yields a
  delivery receipt. One hunk went beyond the card and stands unless vetoed:
  `reap_orphans` now writes `orphaned`, which was in `TERMINAL` and written by nothing
  (zero such rows across 250 sessions) — the same defect shape.
  **Still open, and both `[session]`:** the two native paths, where the signal never
  existed rather than being discarded. **Still open and prior to them:** the owner's
  2026-07-31 verdict below — if nothing depends on the status column, retiring the
  Sessions section beats repairing it, and #489 does not settle that question. Do not
  read "the status is honest now" as the card being done.

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

### 2026-08-03 — Rafael Figueiredo (agent)
Verdict: shipped-rescoped

**Shipped RESCOPED, #498 (`3f0812d`) — the CLI only, and the retire question is answered NO.**

The card's top decision was the owner's standing verdict: retire the Sessions section rather than repair the states, *if nothing depends on the status column*. Settled by evidence, and the condition is refuted — `restore` and `attach`, the two candidates the owner named to check, both gate on it: `is_attachable` returns False on the literal `status == "stale"` (`terminal_sessions.py:133`), and `is_restorable` requires `stale` + `vanished` + `agent_session_id`. Add `Registry.snapshot/reconcile/prune`, `delivery.classify_delivery`, `datums.classify_exit` and the TUI live list. The field cannot be retired.

Deletion also turned out to be the MOST expensive option, inverting the card's assumption that it was the cheap way out: the dashboard section carries the in-app PTY tabs, the `/session-dismiss` route, the `?tab=` post-launch redirect, the nav live count and the xterm attach JS, and removing it would take the phone terminal with it.

**Two findings moved the scope.** (1) The local TUI never had a status column — it renders derived labels (`attachable` / `original terminal only` / `vanished — restorable`), so the misreport was never there and the pattern to copy already existed. (2) **#489 did not deliver its headline.** `registry.is_deliberate_close` had ZERO production callers — its definition and one test. The predicate answered correctly while every surface kept mapping the raw `status`, so all 74 deliberate closes still read as failures. The prior Review here recorded "the dashboard renders it muted" and "the 73 historical rows became correct with no backfill"; the first was false and the second was true only of the predicate, not of any surface. An isolated probe (fake persistent host, private `$HOME`) confirmed 0.0.81's `stop_session` does write `stopped` — the write path was fine, only the read path was missing.

**What shipped.** `registry.display_status(status, reason)` is that missing consumer, reading the pair in one place. `horus sessions` uses it for the status column, the `NONCLEAN_STATUSES` membership check and the receipt's word. Live probe on the real 252-row registry: **74 rows corrected**, the 10 genuine failures still `failed`, `exited`/`stale`/`running` untouched. The row that changed is the previous session — the one that pushed closure commit `96c8863` — which the default three-row view shows at the start of every new session. Stored state untouched, no backfill.

**Left out deliberately, owner's call (2026-08-03): the dashboard is not in use**, so its two `_SESSION_STATUS_CLASS` call sites keep the raw mapping and get the same helper if it returns to use. That is the only remaining work on this card's original scope, and it is worth a fresh card rather than reopening this one.

**Both `[session]` decisions are dissolved, not answered.** A derived label says `stopped` only where intent was recorded and leaves a tmux kill honestly indistinguishable from a crash — which was the honest answer the card asked whether to chase. No pre-kill hook, no screen-scraping, and no herdr dependency, so the owner's 2026-07-31 constraint holds. The two `[refine]` items lapse with the card: `orphaned`/`stale` were left alone, and the vocabulary stayed `stopped`.

**Lesson worth carrying:** a helper with a green unit test and no production caller reads as delivered. #489's test asserted the predicate, never a surface — so the defect it was written for survived the fix that cited it.
