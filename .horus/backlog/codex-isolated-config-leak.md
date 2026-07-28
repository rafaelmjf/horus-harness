---
status: open
priority: medium
readiness: gated
readiness_reason: "Remedy chosen by the owner 2026-07-26 — remedy 3, re-login instead of copying, making login the isolation primitive and retiring file-copying. That requires login to be a first-class verb, so this card is gated on `account-login-verb`, which is itself DEFERRED until 2026-07-29 (interactive login unavailable; the 07-28 trigger was extended one day by the owner on 2026-07-28). Earliest possible start is therefore after 2026-07-29, once its gate lands; nothing to shape in the meantime."
depends-on: account-login-verb
reactivate_after: 2026-07-29
created: 2026-07-20
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
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

## Remedy — **3 chosen by the owner, 2026-07-26**

1. **Stop copying `config.toml`; copy only `auth.json`.** Cleanest isolation, and
   evidenced: a dir created by fresh `codex login` in this run contained only
   `auth.json` — no leaked paths at all. Cost: isolated runs lose the plugin/MCP/
   marketplace block, so plugins must be re-enabled per account.
2. **Copy and rewrite** the known ambient-path keys to the isolated dir. Preserves
   setup, but the correct rewrite rules for runtime/marketplace paths are not obvious
   and would need re-deriving whenever Codex changes its config schema.
3. **Re-login instead of copy** — make `isolate_account` for Codex drive a fresh login
   (i.e. defer to `account-login-verb`) rather than copying anything.

 **Remedy 3 is the decision.** Login becomes the isolation primitive and
file-copying retires entirely — which is the only option that also fixes the
*frozen-mirror drift* second defect, since a logged-in dir is generated in place
rather than copied at a point in time. Remedy 2 was declined explicitly: the card's
own admission that the rewrite rules "are not obvious" makes it a standing
maintenance tax on a file Horus does not own. Remedy 1 was the cheaper fallback and
remains so if `account-login-verb` stalls.

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
- `isolated-account-plugin-parity` — directly affected, and still a required companion
  under the **chosen remedy 3**: a dir produced by a fresh `codex login` carries only
  `auth.json`, so it has no plugin/MCP/marketplace block either. The consequence is the
  same as remedy 1's, but it arrives because the dir is *generated clean* rather than
  because a file was deliberately not copied. (Corrected 2026-07-26 — this note still
  described remedy 1, which was not chosen; librarian receipt L3.)

## Source

Hand-executed setup run, owner-attended, 2026-07-20.

## Reviews

- 2026-07-26 — Refined with the owner. **Remedy 3 chosen: re-login instead of copying.**
  It is the only candidate that fixes all three observed problems at once — the ambient
  path leak, the silently-propagated `trust_level = "trusted"`, and the frozen-mirror
  drift — because a dir produced by `codex login` is generated in place instead of
  copied at a moment in time. Remedy 2 (copy + rewrite paths) declined: unowned schema,
  non-obvious rules, re-derived on every Codex change. Remedy 1 (copy only `auth.json`)
  noted as the cheaper fallback if `account-login-verb` stalls.

  Consequence accepted: this card is **Gated**, not Ready — it cannot be dispatched
  until `account-login-verb` (Ready—Attended) lands, which makes that card the
  unblocker and raises its practical priority. Also unresolved and deliberately
  untouched: `~/.horus/accounts/codex-codex-work/` is still unmapped on this machine
  and holds a clean `auth.json` copy for the personal account. Under remedy 3 it is not
  needed as a promotion target, so it becomes ordinary housekeeping (delete or ignore),
  not part of this card's scope.
