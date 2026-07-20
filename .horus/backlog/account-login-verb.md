---
status: open
priority: medium
readiness: ready
autonomy: attended
readiness_reason: "Fully specified by a live run (2026-07-20): the flow was executed by hand end-to-end, the working code path already exists in the dashboard, and the two consumers are named. Nothing left to shape."
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
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
