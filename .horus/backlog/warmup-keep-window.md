---
status: claimed
priority: medium
created: 2026-07-18
vision_facet: "Accounts & isolation"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/keepwarm.py (new loop), horus/schedule.py (per-account persistent service), horus/cli.py (warmup --keep/--service/--stop/--restart), horus/usage_snapshot.py (public reset-epoch helper)
---

# warmup-keep-window — keep a Claude account's 5h window continuously warm

**Why (owner, 2026-07-18):** `horus warmup` is a one-shot — it opens the 5h window
once. The owner wants a standing, per-account **keep-warm** loop for days they will
work *later* (not scheduled dispatch): the window is always open when they sit down.
Deterministic and cheap (one `claude -p "hi"` turn per window). The scheduler covers
this when a dispatch is actually scheduled; this is the independent "Tokenmaxxing mode"
toggle for ad-hoc later work. Feeds [[tui-control-settings-pane]] as a per-account
`[x]/[ ]` toggle. Claude-only (Codex lifted its 5h window → no-op there).

## How

- **`horus keepwarm.keep_warm(account)`** — warm now, then re-warm just after each
  window reset, forever. Best-effort: a failed warmup retries next cycle, still
  spaced by the window so a persistent failure never hammers the API.
- **Cadence — fixed-5h primary, `resets_at` correction.** Claude's 5h window is
  anchored to the FIRST turn, and the warmup *is* that turn, so it resets at
  `warmed_at + 5h`; arm the next fire ~1 min after (deterministic, no reading
  needed — and a headless `claude -p` warmup does not populate `resets_at`). If a
  fresher `resets_at` *was* recorded (interactive work rendered the statusline),
  prefer it: it can only be more accurate. Never busy-loop on a stale/past reading
  (min-delay floor).
- **Per-account persistent service** — mirrors the listener: `horus-keepwarm-<alias>`
  systemd `--user` unit, `Restart=always`, absolute `ExecStart` (the #322 lesson).
  `warmup --keep --account X` runs the foreground loop; `--service` installs,
  `--stop`/`--restart` manage, and a status reader backs the pane. Multiple allowed
  (one per account) — unlike the single-consumer listener.

## Acceptance

- `warmup --keep --account claude-personal` warms then sleeps ~5h+offset; a recorded
  future `resets_at` overrides the fixed cadence (unit-tested via injected clock).
- `--service` installs `horus-keepwarm-claude-personal.service` with an ABSOLUTE
  `ExecStart`; a live isolated probe confirms it reaches `active` + logs a warm cycle
  (the long-running-service verification bar), and `--stop` removes it.
- Codex accounts are not offered (warmup is Claude-config-dir only by construction).

## Non-goals

- No usage polling to drive the cadence — the warmup anchors its own clock.
- Not a Codex feature (no 5h window to keep warm).
- No new scheduling engine — reuses the systemd `--user` service posture.
