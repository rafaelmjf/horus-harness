---
status: open
priority: high
readiness: ready
autonomy: eligible
readiness_reason: "Demonstrated live (2026-07-20), not theorised: a duplicate-identity Codex account was created and mapped with no objection from any surface. The fix mirrors an existing, working Claude implementation."
created: 2026-07-20
created_by: owner
last_refined: 2026-07-21
vision_facet: "Accounts & isolation"
tier: medium
type: bug
parallel: safe
phase: converge
surface: "horus/adapters/codex.py (verify_account + _launch guard), horus/launch.py:92 (attribute-name mismatch)"
---

# codex-identity-guard — Codex launches skip the account identity check entirely

## Why — demonstrated, 2026-07-20

During a hand-run account setup, a `codex-work` alias was mapped to a freshly
logged-in dir. The browser reused the already-signed-in ChatGPT session, so the new
dir authenticated as the **same account** as `codex-personal`:

```
codex-personal -> account_id 6d67cc97-1f90-4dd5-af80-3558e3628b0e | chatgpt
codex-work     -> account_id 6d67cc97-1f90-4dd5-af80-3558e3628b0e | chatgpt
```

The alias table then contradicted itself — id `6d67cc97…` aliased to `codex-personal`,
while the *dir* was mapped as `codex-work`. **Nothing objected, at any point.** It was
caught only because a human diffed the two `auth.json` files by hand.

A `horus run --agent codex --account codex-work` in that state runs as the personal
account: it draws down the **personal** rate-limit pool while every receipt, datum, and
session record attributes the work to `codex-work`. That corrupts usage accounting and
delegation calibration silently — the failure mode this repo's rules exist to prevent
("put safety in the code, not the reviewer").

## Two independent defects

1. **`horus/adapters/codex.py` has no `verify_account` and no `_launch` guard.** The
   Claude adapter has both (`claude.py:175`, `claude.py:207`) and they work — the same
   run proved it, by refusing the empty `claude-work` dir and then adopting the correct
   identity on first login.
2. **The shared guard skips Codex on an attribute-name mismatch.**
   `launch.py:92` reads `getattr(adapter, "config_dirs", {})`. Codex stores its mapping
   in `codex_homes` (`codex.py:79`), so the check is a silent no-op for Codex **even if
   `verify_account` were added**. Fixing (1) without (2) leaves attended launches
   unguarded.

## What to build

- `CodexAdapter.verify_account(account)` mirroring the Claude contract: read
  `<CODEX_HOME>/auth.json` → `tokens.account_id`, resolve through
  `config.load_account_aliases()`, return an `IdentityCheck`. Keep TOFU adoption
  (first login in the account's own isolated dir claims the alias); refuse when the
  identity is already aliased to a *different* account — the case observed here.
- A `_launch` guard raising the Codex equivalent of `AccountMismatch`.
- Fix `launch.py:92` to resolve the mapping per-adapter rather than assuming
  `config_dirs` — e.g. a shared `account_dirs` property, or ask the adapter.

The identity key is `tokens.account_id`, not an email (Codex `auth.json` carries no
address). The alias table already keys Codex on that id, so no schema change.

## Acceptance

- Mapping an alias to a dir whose `account_id` is already aliased elsewhere is refused,
  with both alias names in the message.
- An attended Codex launch under a mismatched account refuses before spawning.
- A first login into an account's own isolated dir still adopts (no regression on the
  legitimate setup path).
- Gate: full suite green on the exact SHA. Probe: reproduce the observed case — map a
  second alias to a dir holding an already-aliased `account_id` and confirm the refusal.

## Notes

- Do not ship `account-login-verb` for Codex before this: a one-command login that can
  mint a duplicate identity in silence is strictly worse than the current friction. The
  guard is the safety half of that feature.
- Claude's guard produced the *bad UX* that opened this session (an unhelpful dead-end
  message) but it was **working** — it refused a wrong launch. Codex's silence is the
  worse failure. Fix the message (see `account-login-verb`), keep the refusal.

## Source

Hand-executed setup run, owner-attended, 2026-07-20. The duplicate `codex-work` mapping
was created and then removed (`config.remove_account`) in the same session.

## Reviews

- 2026-07-21 — **Kept Ready (eligible); NOT e2e-drill food** (owner, refine pass): it is
  the priority safety ship, but excluded from drill-leg candidates — the drill wants
  trivial always-green legs, and a safety-critical identity guard should ship on its own
  merits, with the refusal probe observed by the owner rather than merged unattended as a
  test.
