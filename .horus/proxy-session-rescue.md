# RESCUE — a Claude session went "api unresponsive" after proxy wiring

> **Status (v0.0.65, mode B): this can no longer happen through Horus.** Enabling the proxy
> now injects env **per-launch**, never into a shared `settings.json`, so it cannot redirect
> a running session. This runbook is kept for **legacy sessions** or **manual meddling** with
> `ANTHROPIC_BASE_URL` / a hand-edited `settings.json`. The recovery steps still apply verbatim.

**Read this if a Claude Code session stopped responding (API errors / "unresponsive")
right after someone enabled the CLIProxyAPI / GPT-in-Claude-Code integration.** This is a
copy-paste recovery runbook. It needs nothing from the session that broke. Related:
backlog card `x4-stage1-cliproxy-wiring` (shipped v0.0.65) and spike
`research/2026-07-18-x4-stage0-gpt-in-claude-code-spike.md`.

## What happened (the mechanism)

Enabling the proxy writes a proxy `env` block into a Claude account's `settings.json`:
`ANTHROPIC_BASE_URL=http://127.0.0.1:8317`, `ANTHROPIC_AUTH_TOKEN=<key>`,
`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`. A Claude Code session already **running** on
that config dir hot-applies it into its in-memory `process.env` and **cannot unlearn it** —
clearing `settings.json` afterward does NOT revive an already-running session (a running
process never unsets an env var a reload applied; `/proc/<pid>/environ` won't even show it).

So a poisoned running session is stuck pointing at `127.0.0.1:8317`. It only recovers if
**that port serves** with a token it holds AND it sends a **concrete model id** (not a bare
alias). Two independent things can break it: the proxy isn't up, or the bare alias 502s.

## FIX A — revive a still-running poisoned session (fastest; keeps its context)

1. **Start the proxy** so 8317 answers. Get the client api-key from the config (do NOT
   guess it): it's the `api_key` field in `~/.horus/proxy.json` and the `api-keys:` entry in
   `~/.horus/cliproxy/config.yaml`.
   ```bash
   docker run -d --rm --name horus-cliproxy \
     -p 127.0.0.1:8317:8317 \
     -v "$HOME/.cli-proxy-api:/root/.cli-proxy-api" \
     -v "$HOME/.horus/cliproxy/config.yaml:/CLIProxyAPI/config.yaml" \
     eceasy/cli-proxy-api:latest \
     /CLIProxyAPI/CLIProxyAPI -config /CLIProxyAPI/config.yaml
   ```
2. **Verify it serves** (substitute the key from step 1):
   ```bash
   KEY=$(grep -oE '"api_key":[^,]*' ~/.horus/proxy.json | cut -d'"' -f4)
   curl -s -H "Authorization: Bearer $KEY" http://127.0.0.1:8317/v1/models -o /dev/null -w '%{http_code}\n'   # want 200
   ```
   Both the Codex (GPT) and Claude subscription tokens live in `~/.cli-proxy-api/` — so the
   proxy can serve BOTH `gpt-5.5` and `claude-opus-4-8`.
3. **In the poisoned session, switch to a CONCRETE model id** — this is the alias trap:
   - Bare `opus` / `sonnet` / `haiku` → `502 "unknown provider"`.
   - Concrete ids work: `/model claude-opus-4-8` (stays on Claude) or `/model gpt-5.5`.
   Then type anything; it should answer. (Modern Claude Code often already sends a resolved
   concrete id, so it may recover the instant the proxy is up — try typing first.)

Cost note: the first turn after switching is a cache MISS (per-model + the proxy auth is the
subscription, not the direct API) — one full-context re-read. No context is lost.

## FIX B — stop the bleed for NEW sessions (native Claude again)

This does NOT revive an already-running poisoned process (use Fix A for that), but makes the
next launch native. Remove the proxy `env` keys from every Claude `settings.json`:

- Affected files: `~/.claude/settings.json`, `~/.horus/accounts/claude-personal/settings.json`,
  `~/.horus/accounts/claude-work/settings.json`. Delete the `ANTHROPIC_BASE_URL`,
  `ANTHROPIC_AUTH_TOKEN`, and `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` entries from the
  `env` block (leave everything else).
- **Clean pre-wiring backups exist** at `~/cliproxy-spike/settings-backup/` — compare/restore
  from there if unsure what the file should look like.
- Convenience (only if a checkout of branch `wip/x4-cliproxy-stage1` is available):
  `uv run horus proxy disable` from the repo does Fix B + stops the service. NOTE: `horus proxy`
  is NOT in the released CLI (0.0.64) — it exists only on that branch.

## Tear down the proxy container

```bash
docker rm -f horus-cliproxy    # systemctl stop / disable does NOT stop the --rm container
docker ps --filter name=horus-cliproxy   # confirm gone
```

## If a session is unrecoverable

Its delivery is still durable in git + PRs + this `.horus/` state — abandon the process and
resume from a clean session. Nothing shipped is lost by killing a poisoned session.

## Assets reference (all machine-local)

| Thing | Location |
|---|---|
| Client api-key (Bearer token) | `~/.horus/proxy.json` → `api_key`; `~/.horus/cliproxy/config.yaml` |
| Subscription OAuth tokens (GPT + Claude) | `~/.cli-proxy-api/*.json` |
| Proxy config | `~/.horus/cliproxy/config.yaml` (port 8317, api-keys) |
| Docker image / container | `eceasy/cli-proxy-api:latest` / name `horus-cliproxy` |
| Clean settings.json backups | `~/cliproxy-spike/settings-backup/` |
| Which account a session uses | its `CLAUDE_CONFIG_DIR` (`tr '\0' '\n' < /proc/<pid>/environ`) |
