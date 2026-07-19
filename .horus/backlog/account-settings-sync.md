---
status: open
priority: low
readiness: gated
readiness_reason: "Keep for the next-machine installation, whose real settings drift will provide shaping evidence."
created: 2026-07-17
last_refined: 2026-07-19
vision_facet: "Accounts & isolation"
tier: medium
type: feature
parallel: safe
surface: new horus subcommand (settings sync across ~/.horus/accounts/<agent>-<alias> dirs); doctor drift check
---

# account-settings-sync — one canonical settings block across isolated account dirs

**Why (owner, 2026-07-17):** per-account isolation means every
`~/.horus/accounts/<agent>-<alias>/settings.json` is independent — no inheritance from
`~/.claude`. So a settings change (statusLine, hooks, model, theme) has to be hand-copied
into every account dir, on every machine (`~/.horus/` is machine-local + gitignored).
This bit us live: a statusLine configured in `~/.claude` never applied because sessions
run under `claude-personal`, which had none, while `claude-work` did (fixed 2026-07-17,
see the `claude-config-dir-per-account` memory). Hand-sync is error-prone and silently
drifts.

## Idea (thin, advisory — not a new config plane)

A small `horus` verb that applies/reconciles a **canonical settings block** across all of
a machine's managed account config dirs — e.g. `horus account sync-settings [--keys statusLine,hooks]`
copies chosen keys from a source (or a declared canonical block) into every
`~/.horus/accounts/<agent>-*` `settings.json`, and `horus doctor` flags when accounts
have drifted on those keys. Diff-first / dry-run by default; the owner confirms before
it writes. Deliberately narrow: it syncs a whitelist of keys, never wholesale clobbers an
account's settings, and stays machine-local.

## Open questions

- Which keys are in scope by default (statusLine, hooks) vs opt-in (model, theme, permissions)?
- Source of truth: a declared canonical block (where?) vs "copy from account X"?
- Does this belong in `horus account` or `horus doctor --fix`? Lean toward advisory
  diff + explicit apply, consistent with the repo's controls-climb-a-ladder rule
  (instruction → deterministic signal → hard gate); this is at most a deterministic
  signal + an explicit apply.

## Acceptance (drafted 2026-07-19 refine pass — owner spot-check)

- One canonical settings block (statusline command, hooks, shared preferences) is
  declared once per machine and synced into every isolated account config dir
  (`~/.horus/accounts/<agent>-<alias>`) — never hand-copied per account.
- `horus doctor` reports drift when an account dir diverges from the canonical
  block; a sync command restores it without touching account-specific state
  (credentials, session history).
- Gate: full suite green on the exact SHA. Probe: break the statusline line in one
  account dir → doctor names the drifted dir; run the sync → a session launched on
  that account renders the statusline again.

## Notes

- Scope guard: this is a convenience over machine-local isolated dirs, NOT a shared/central
  config store — isolation stays the invariant. Do not reintroduce ambient inheritance.
- **Overlaps `horus-statusline-default`** (2026-07-17), which needs
  `statusLine` written into every account dir on every machine. Whichever ships first owns
  the account-settings writer; the other consumes it. Do not build two writers. That card
  also answers this one's first open question by example: `statusLine` and `hooks` are the
  keys that actually drift, because they are the ones Horus itself has an opinion about.

## Reviews

- 2026-07-19 — **Keep, low priority, Gated (owner):** this becomes useful when Horus is
  installed on additional machines. Do not retire it merely because the current machine
  is configured; use the next real installation's drift as shaping evidence.
