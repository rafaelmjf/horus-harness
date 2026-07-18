---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Delegation calibration"
phase: explore
tier: opus
type: feature
parallel: safe
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: horus/proxy.py + cli.py/config.py/schedule.py/terminal_tui.py — ALL on branch `wip/x4-cliproxy-stage1` (pushed), NOT on main
---

# x4-stage1-cliproxy-wiring — finish the CLIProxyAPI toggle, fix the wiring bugs

**Stage 1 of [[vision-branch-x4-model-harness-plane]]**, following the GO verdict of the
stage-0 spike [[gpt-models-in-claude-code-harness]] (receipt:
`research/2026-07-18-x4-stage0-gpt-in-claude-code-spike.md`, on main).

Stage 1 was **built and parked, not shipped** — it works and is tested (135 pass) and was
live-proven, but it has design bugs that broke a running session, so it was held back from
the v0.0.64 release. **Resume from a fresh session; the account that built it hit its usage
limit mid-fix.**

## Where the code is (do not rebuild from scratch)

All stage-1 code lives on the pushed branch **`wip/x4-cliproxy-stage1`** — not on main:
`horus/proxy.py` (new: state, guided enable/disable, docker run/login builders,
`/v1/models` reachability, settings.json env writers) + integration edits to `cli.py`
(the `horus proxy` command group), `config.py` (`write_proxy_env`/`clear_proxy_env`),
`schedule.py` (`PROXY_UNIT` + proxy systemd service), `terminal_tui.py` (Settings-pane
toggle), and tests. Read that branch first; this card is the fix list, not a redesign.

## Bugs to fix before shipping (safety in code, per repo rule)

1. **`enable()` rewires a LIVE session into a possibly-dead proxy — the self-conflict.**
   `enable()` writes the proxy `env` block (`ANTHROPIC_BASE_URL=127.0.0.1:<port>` etc.)
   into EVERY Claude `settings.json` (`_claude_config_dirs()` — every isolated account +
   ambient `~/.claude`). A Claude Code session already running on one of those config dirs
   hot-applies the new `env` into its in-memory `process.env`; if the proxy is not actually
   up/serving, that session's every request then hits a dead endpoint → **"api
   unresponsive"** (observed 2026-07-18: it took down a 3h batch session on `claude-personal`).
   Clearing settings.json does NOT recover it — a running process never *unsets* an env var
   a reload already applied; only a proxy that answers on that port revives it.
   **Fix direction:** never rewire a config dir whose live session would be redirected
   mid-run (detect/refuse, or scope the toggle to *new* launches only, not a global
   settings.json rewrite). The guard belongs in code, not in a warning.

2. **`proxy_env()` omits the alias→concrete-id mapping → bare aliases 502.**
   It sets `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` but not
   `ANTHROPIC_DEFAULT_SONNET_MODEL`/`_OPUS_`/`_HAIKU_`. A session launched `--model opus`
   that sends the bare alias `opus` gets `502 "unknown provider for model opus"` from the
   proxy (proven live). Concrete ids work (`claude-opus-4-8` / `gpt-5.5` → 200). Modern
   Claude Code usually resolves the alias to a concrete id before sending (so the spike
   session recovered without a `/model` switch once the proxy was up) — but the wiring must
   not depend on that. **Fix:** inject the `ANTHROPIC_DEFAULT_*` mappings (the spike used
   them) or alias the bare names in the proxy config, so any launch resolves.

3. **`disable()` / `systemctl stop` leaves the `--rm` container running.**
   Stopping the systemd unit kills the `docker run` client but the daemon keeps the
   container up (a known docker+systemd gotcha). Teardown must actively
   `docker rm -f <PROXY_UNIT>` (there is an `ExecStartPre=-docker rm -f` on start, but
   stop needs the symmetric removal), so `disable` genuinely returns to native Claude.

## Acceptance

- Enabling the toggle never breaks a live session (bug 1 guarded in code + a test).
- A session launched with a bare model alias resolves through the proxy (bug 2).
- `disable` leaves no container running and no proxy env in any settings.json (bug 3 + a test).
- Guided setup flow works end-to-end (branch principles 1–2: opt-in, off by default, walks
  through install/OAuth/verify-reachable before rewiring anything).
- Ships in its own PR + release; the usage-visibility gap (spike Q3) carried as a design note.

## Non-goals

- Not the harness axis (stage 2) or cross-matrix calibration (stage 3).
- Horus still owns no runtime — it points Claude Code at the proxy via the official env,
  reversibly (branch principle 4).
