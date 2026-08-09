---
status: open
topic: account-isolation
priority: medium
readiness: ready
autonomy: attended
created: 2026-07-20
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
vision_facet: "Accounts & isolation"
tier: medium
type: feature
parallel: safe
phase: converge
surface: "horus/config.py (login-provision fn), horus/cli.py (`horus account --login`), horus/dashboard.py (reuse), horus/terminal_tui.py (accounts screen), horus/launch.py (error text), horus/cli.py doctor finding"
---

# account-login-verb — provision + log into an account that has no prior login

## Why (live evidence, 2026-07-20)

The owner selected the `claude-work` account in the TUI, pressed Launch, and landed
back on the TUI. The status line read `Launch failed: account 'claude-work' login
mismatch (found no login).` — technically true, actionably useless, and with **no
remedy reachable from the TUI or the CLI**.

Root cause: `config.isolate_account()` (`config.py:786`) only works *from an existing
ambient login* — it copies `.credentials.json` out of `~/.claude`. There is no verb that
provisions a dir and drives a *fresh* login into it. So an account can be aliased and
mapped while permanently unloggable-into by any Horus surface.

Consequences observed:

- `claude-work` sat mapped-but-empty since the Windows migration; every launch under it
  failed at the guard in `launch.py:92`.
- On a machine with two Claude accounts and no ambient login, the only documented path
  is: log in ambiently → `horus account --set X --isolate` → log out → log in as the
  next account → repeat. Serially, through one shared dir — the exact contention the
  isolation model exists to prevent.

**The working code already exists and is web-only:** `dashboard.process_account_login`
(`dashboard.py:3739`) derives the canonical dir, maps the alias, and opens the native
CLI's own login. It just isn't reachable from the CLI or TUI.

## What to build

One provisioning function in `config.py`, called by three surfaces:

1. **`horus account --login <alias> [--agent codex]`** — the primitive.
2. **Dashboard** — `process_account_login` calls it instead of its own inline logic.
3. **TUI accounts screen** — a "Log in" affordance on any account with no credentials
   (the owner asked for this explicitly, 2026-07-20; it is a *consumer*, not a
   second implementation).

It must: derive `~/.horus/accounts/<agent>-<alias>`, `mkdir -p`, map the alias
(`set_account_config_dir` / `set_account_codex_home`), **write the statusline pointer**,
and open `launcher.login_argv_env(agent, dir)` in a new console.

### Bug to fix in the same change

`process_account_login` maps the alias without calling
`config.write_statusline_pointer` — so **every dashboard-wizard-created Claude account
silently gets no statusline**, the exact failure mode that `account-settings-sync` was
written about. `isolate_account` writes it (`config.py:808,823`); the wizard path does
not. `write_statusline_pointer` must stay the single writer.

### Adjacent fixes (cheap, same area, prevent the recurrence)

- **Split the launch error.** `launch.py:95` collapses "no login yet" and "logged in as
  the wrong account" into `login mismatch`. `verify_account` already distinguishes them
  (`detected_email is None` vs `aliased != account`). The first is a setup gap with a
  remedy and must name it: ``no login yet — run `horus account --login claude-work` ``.
- **`horus doctor` finding** for mapped-but-never-logged-in accounts, carrying the same
  fix command. Read-only, and unlike a first-run wizard it keeps helping on machine two.

## Acceptance

- `horus account --login <alias>` provisions, maps, writes the statusline pointer, and
  opens the native login — with **no ambient login present**, for both agents.
- A dashboard-wizard-created Claude account has `statusLine` in its `settings.json`.
- A launch against a never-logged-in account prints the remedy command, not `mismatch`.
- `horus doctor` names any mapped account with no credentials.
- Gate: full suite green on the exact SHA. Probe: map a throwaway alias, run
  `--login`, complete it, then launch that account from the TUI successfully.

## Notes from the live run (2026-07-20)

- **The hand-run flow works exactly as designed.** Executing
  `launcher.login_argv_env` + `open_terminal` by hand logged `claude-work` in on the
  first try; `verify_account` then returned
  `ok=True, detected_email=rafael.figueiredo@datanative.solutions`, and TOFU adoption
  persisted the email→alias mapping unprompted (`claude.py:196-201`). The design needs
  no revision — only packaging.
- **The login path yields *better* isolation than `--isolate`, not just better
  ergonomics.** A dir created by fresh login contains only the credential file; a dir
  created by `isolate_account` for Codex also inherits a `config.toml` full of absolute
  paths back to the ambient home (see `codex-isolated-config-leak`). Prefer login over
  copy wherever both are possible.
- **The command is `claude` bare, so the user sees onboarding, not a login screen.**
  On a dir that already has `settings.json`/`.claude.json` but no credentials, what
  happens is not obvious in advance. `--login` should print "expect onboarding, then
  run `/login`" rather than silently opening a window.

## Related

- `codex-identity-guard` — the Codex half; a `--login` that can create a duplicate
  identity in silence is worse than no `--login`. Ship the guard with or before this.
- `account-settings-sync` — owns the settings-drift question; this card owns only the
  statusline pointer at creation time. Do not build two writers.
- `new-machine-setup-guidance` — this verb is that skill's central step; the skill is
  much weaker without it.

## Source

Live friction report + hand-executed setup run, owner-attended, 2026-07-20.

## Reviews

- 2026-07-26 — **Deferred until 2026-07-28, capacity not scope.** Owner instruction: cards
  requiring an active interactive login are held until after 2026-07-28. Nothing about the
  card changed — it remains fully specified from the 2026-07-20 hand-executed run, with the
  working code path already in the dashboard and both consumers named. On 2026-07-28 it
  returns to **Ready / attended** directly, with no re-refinement pass needed.

  Worth knowing when it does return: it is now the **unblocker** for
  `codex-isolated-config-leak`, which the owner resolved the same day to remedy 3
  (re-login instead of copying config.toml). That card is Gated on this one, so this
  deferral moves both. Attended is inherent here, not conservatism — an interactive login
  cannot be dispatched to a worker.
- 2026-07-28 — **Hold extended to 2026-07-29, capacity again, not scope.** The 07-28 trigger
  fired during a refinement pass; the owner extended the hold by one day because an
  interactive login was still unavailable. Nothing about the card changed. It remains fully
  specified and returns to **Ready / attended** on 2026-07-29 with no re-refinement pass.
  Note the knock-on: `codex-isolated-config-leak` is Gated on this card and its
  `reactivate_after` moved with it, so this one-day extension moves both.

### 2026-08-02 — Rafael Figueiredo (manual)

2026-08-02 — Reactivated. The card was swept into `shelved` on 2026-08-01 as collateral of the 69-card sweep, but its own deferral had already expired: `reactivate_after: 2026-07-29`, with the card recorded as fully specified and needing no re-refinement. Shelving it also stranded `codex-isolated-config-leak` — an active BUG whose owner-chosen remedy (re-login instead of copying, 2026-07-26) depends on this verb existing, so its gate could never lift. Restored to Ready/attended, the state its own readiness_reason said it returns to.
