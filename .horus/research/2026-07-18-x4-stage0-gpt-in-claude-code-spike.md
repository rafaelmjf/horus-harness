# X4 stage-0 spike — GPT in Claude Code via the Codex subscription

**Date:** 2026-07-18 · **Card:** `gpt-models-in-claude-code-harness` (stage 0 of
`vision-branch-x4-model-harness-plane`) · **Verdict: GO.**

Ran live on this machine. GPT-5.5, driven inside the Claude Code CLI through CLIProxyAPI
bridging the owner's **ChatGPT Plus** subscription, completed a real **agentic tool-use
loop** — not just chat.

## Setup that worked (exact)

- **Proxy:** `docker run --rm -p 8317:8317 -v ~/.cli-proxy-api:/root/.cli-proxy-api -v
  <config>:/CLIProxyAPI/config.yaml eceasy/cli-proxy-api:latest /CLIProxyAPI/CLIProxyAPI
  -config /CLIProxyAPI/config.yaml` (image **v7.2.86**). The image CMD is `./CLIProxyAPI`,
  so passing flags REPLACES it — the binary path must be named explicitly (a 203-class trap).
- **Codex OAuth:** `… /CLIProxyAPI/CLIProxyAPI -config … -codex-device-login -no-browser`
  → prints a device URL (`auth.openai.com/codex/device`) + code; owner approves with the
  ChatGPT account. Token persists at `~/.cli-proxy-api/codex-<email>-plus.json`. **Device-code
  flow is the one to use** — the browser-callback `-codex-login` needs a mapped port, and
  `-it` fails under a non-TTY shell.
- **Claude Code (2.1.214):** `ANTHROPIC_BASE_URL=http://127.0.0.1:8317`,
  `ANTHROPIC_AUTH_TOKEN=<proxy api-key>`, `ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-5.5`
  (opus/haiku mapped too), `--model sonnet`. The proxy serves `/v1/messages?beta=true`.

## Spike questions — answered

1. **Tool-use / agentic parity — GO (proven).** Task: "run `buggy.py` (it divides by zero),
   fix it to print 2+2, rerun, report output." GPT ran it (Bash), **edited the file** (`1/0`
   → `2+2`, confirmed on disk), reran (Bash), reported `4`. Exit 0. Server log: **7×
   `POST /v1/messages` 200**, 2.5–4.8s/turn — usable latency for agentic work.
2. **Subscription bridge — works, fair use.** The ChatGPT Plus sub drove GPT with no API key;
   `/v1/models` exposed the live family (`gpt-5.5`, `gpt-5.6-sol/terra/luna`, `gpt-5.4(-mini)`,
   `gpt-5.3-codex-spark`, `codex-auto-review`). Stable across the full multi-turn session; token
   persists for reuse. Long-run/away stability is a longer observation, but the mechanism is
   solid. Treated as fair use per owner (2026-07-18).
3. **Usage visibility — GAP (the real stage-1 problem).** Horus's Codex usage path reads
   `~/.codex` rollout; the proxy consumes the sub via its own `~/.cli-proxy-api` token — so
   **GPT-via-proxy usage is invisible to Horus's current usage machinery**. The proxy logs
   requests + latency but not token counts by default. Stage 1+ must decide: read the proxy's
   own metering, or accept GPT sessions as unmetered in the window model.
4. **Fit — GO.** You get Claude Code's harness (tools, agentic loop, our whole launch path)
   with a GPT model on a sub already paid for. The value is *GPT model + Claude Code quality*.

## Verdict → stage 1

**GO.** Wire it: `ClaudeAdapter.build_env` injects `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`
/ `ANTHROPIC_DEFAULT_*` for a "proxied" account; GPT models appear as launch choices; the
CLIProxyAPI integration is an **optional Settings-pane toggle with guided setup** (branch
principles 1–2). Carry the **usage-visibility gap** into that card as an explicit design point.

**Dogfood note (why guided setup matters — branch principle 2):** every friction here is
something the wizard must absorb — the CMD-replacement binary-path trap, the non-TTY device
login, the config/auth-dir/port scaffolding, relaying the device code. The spike *is* the
manual version of the flow stage 1 automates.

## Artifacts (machine-local, not committed — contain/point at the sub token)

- `~/cliproxy-spike/config.yaml` (port + api-key), `~/cliproxy-spike/login.sh`
- `~/.cli-proxy-api/codex-<email>-plus.json` (the subscription token — reusable; restart the
  proxy with the docker run above to continue)
- Test evidence: `~/cliproxy-spike/{server.log, claude-gpt-test.log}`
