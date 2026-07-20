---
status: open
priority: medium
readiness: shaping
readiness_reason: "The defect is confirmed on disk, but the correct remedy is a real choice (rewrite paths vs stop copying config.toml vs re-login into a clean dir) with a plugin/MCP tradeoff the owner has not made."
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
vision_facet: "Accounts & isolation"
tier: medium
type: bug
parallel: safe
phase: explore
surface: "horus/config.py:696-698 (_ACCOUNT_AUTH_FILES), isolate_account copy step; horus doctor drift check"
---

# codex-isolated-config-leak — an isolated Codex account still points at the ambient home

## Why — confirmed on disk, 2026-07-20

`isolate_account` copies `("auth.json", "config.toml")` for Codex
(`config.py:698`). Codex's `config.toml` contains **absolute paths back to the ambient
`CODEX_HOME`**. Verbatim from `~/.horus/accounts/codex-codex-personal/config.toml`:

```toml
[mcp_servers.node_repl.env]
CODEX_HOME = 'C:\Users\Rafa\.codex'
NODE_REPL_TRUSTED_CODE_PATHS = 'C:\Users\Rafa\.codex'

[marketplaces.openai-bundled]
source = '\\?\C:\Users\Rafa\.codex\.tmp\bundled-marketplaces\openai-bundled'

[projects.'c:\users\rafa']
trust_level = "trusted"
```

So an "isolated" Codex session hands its MCP server the **shared** home and resolves
marketplaces out of the shared home's temp dir. The isolation is nominal. Claude's two
copied files (`.credentials.json`, `.claude.json`) do not have this property — this is
Codex-specific, and it is a direct consequence of copying a config file rather than
letting the tool generate its own.

**Second defect — the copy is a frozen mirror.** Both files were byte-identical to
their ambient originals at inspection (`auth.json` 4235 b / Jul 16 08:11;
`config.toml` 3039 b / Jul 20 08:08), while the Codex **desktop app** was actively
writing the ambient dir the same day (`.codex-global-state.json` 12:23,
`goals_1.sqlite` 12:25). A point-in-time copy drifts from the moment it is made, and
nothing reports the drift. This is `account-settings-sync`'s predicted failure, already
real, on Codex.

Also note `[projects.'c:\users\rafa'] trust_level = "trusted"` was copied along —
a *trust* decision propagated by a file copy, which is not a thing an isolation
mechanism should do silently.

## Candidate remedies (not chosen — this is the shaping question)

1. **Stop copying `config.toml`; copy only `auth.json`.** Cleanest isolation, and
   evidenced: a dir created by fresh `codex login` in this run contained only
   `auth.json` — no leaked paths at all. Cost: isolated runs lose the plugin/MCP/
   marketplace block, so plugins must be re-enabled per account.
2. **Copy and rewrite** the known ambient-path keys to the isolated dir. Preserves
   setup, but the correct rewrite rules for runtime/marketplace paths are not obvious
   and would need re-deriving whenever Codex changes its config schema.
3. **Re-login instead of copy** — make `isolate_account` for Codex drive a fresh login
   (i.e. defer to `account-login-verb`) rather than copying anything.

Option 1 or 3 is likely right; both make "log in" the isolation primitive and retire
file-copying, which also removes the trust-propagation surprise. Decide with the owner
against how much the plugin block is actually used in *CLI* runs (the desktop app keeps
its own ambient config regardless).

## Acceptance (draft)

- A newly isolated Codex account contains no absolute path referencing another
  account's or the ambient home.
- `horus doctor` reports a Codex account dir whose `config.toml` references a home
  other than its own.
- Gate: full suite green on the exact SHA. Probe: isolate a throwaway Codex alias and
  grep its dir for the ambient home path — zero hits.

## Open item on this machine

`~/.horus/accounts/codex-codex-work/` was created during the 2026-07-20 run, is now
**unmapped**, and still holds a live token copy for the personal account. It is a
*clean* dir (only `auth.json`), so it is a candidate for remedy 3 above — promoting it
to be `codex-personal`'s dir would fix this card's defect for free. Owner has not
decided delete-vs-promote; nothing was removed.

## Related

- `account-settings-sync` — owns settings *drift* across dirs; this card owns what gets
  copied at *creation*. Whichever ships first should not build a second writer.
- `account-login-verb` — remedies 1 and 3 depend on login being a first-class verb.
- `isolated-account-plugin-parity` — directly affected: remedy 1 makes plugin parity a
  required companion rather than a nice-to-have.

## Source

Hand-executed setup run, owner-attended, 2026-07-20.
