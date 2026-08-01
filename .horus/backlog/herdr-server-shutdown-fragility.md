---
status: shelved
shelved_on: 2026-08-01
priority: low
created: 2026-07-30
created_by: agent
readiness: gated
readiness_reason: "The defect is upstream in herdr, so Horus cannot fix it — this card exists to record the measurement and to decide what Horus does defensively. Gated on an owner call: report upstream, or accept herdr sessions as losable and lean on session recovery instead."
phase: explore
type: bug
tier: low
parallel: safe
vision_facet: "Dashboard / cockpit"
surface: horus/hosts/herdr.py (capabilities, ensure_ready), .horus/backlog/archive/herdr-host-probe.md (the 2026-07-29 measurements this extends)
---

# herdr-server-shutdown-fragility — herdr's server exits on client-triggered errors, taking every session with it

## Why — measured 2026-07-30, from `~/.config/herdr/herdr-server.log`

Not a Horus defect, and **not** what caused the 2026-07-30 session loss (that was
[[herdr-live-test-stops-owner-server]]). Recording it because it changes how much the
herdr host can be trusted, and because it was initially mistaken for the cause.

**A pane dying that the app state never registered escalates to a full server
shutdown.** The signature:

```
pane.exit  pane_id=10  status=code:1, signal:Hangup
WARN  PaneDied for unknown pane pane=10
server shutdown initiated
```

Reproduced three times in the log — `2026-07-29 16:56:00` and `16:57:56` (both
`pane=4`), and `2026-07-30 09:58:44` (`pane=10`). The trigger is a create-then-close
inside the registration window: at `09:58:44` a `workspace.create` was followed by
`pane.close` **135ms** later, before the app had registered the pane.

It does not always escalate. Panes 8 and 9 produced the same warning at `09:53:30` and
`09:53:56` and the server lived. The fatal path appears specific to closing the only pane
of a workspace the app never registered — a bookkeeping race, where the correct behaviour
is plainly to ignore an orphan rather than exit the process.

## The durability number

**35 server shutdowns against 4 client shutdowns** in this log. All three
server/client-coincident pairs are server-died-then-client-followed, not the reverse — at
`09:58:44` the server logged `shutdown initiated` **4ms before** the client logged
`exiting`. The client is the stable component; the server is not.

## Why this matters for the host

tmux's server is designed never to die from a client action: closing a pane, detaching, or
crashing a client never touches it. That is the property behind "just relaunch the TUI and
reconnect" — it reattaches to processes still alive in a daemon that outlived the crash.

herdr has the same process-ownership model (panes are the server's children on its PTYs,
so they take `SIGHUP` when it exits) **without** the durability, and no way to reconnect
after the fact: `~/.config/herdr/session.json` persists only `cwd` per pane — no command,
no agent, no session id. Restore therefore *re-creates* empty shells from a layout file
rather than reattaching anything. For a dead herdr server there is nothing to reconnect
to, by construction.

Combined with the host's already-declared `liveness=False` / `reports_exit_code=False`
(`horus/hosts/herdr.py:232-241`), the practical read is: **herdr-hosted sessions are
losable in a way tmux-hosted ones are not.**

## Options

1. **Report upstream** with the log excerpt above (herdr v0.7.5 per the 2026-07-29 probe;
   confirm the current version first). The fix is theirs: never exit the process because
   of an unrecognised pane.
2. **Accept and compensate.** Treat herdr sessions as losable and make recovery cheap
   rather than making the host durable — which is exactly [[session-restore]].
   This is the option that pays off regardless of what upstream does, since reboots and
   `tmux kill-server` lose sessions too.
3. **Declare it.** If the host stays, consider surfacing the reduced durability where the
   owner picks a target, so choosing herdr is an informed trade rather than a surprise.

Option 2 is the one with value independent of herdr; 1 is cheap and worth doing anyway.
