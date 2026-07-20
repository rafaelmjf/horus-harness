---
status: open
priority: low
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: deferred
readiness_reason: "Still deferred, but the deferral now applies asymmetrically (2026-07-20 refine): the FROM-ZERO branch genuinely needs more platform runs, while the REPLICATE branch is fully determined and blocked only on `account-login-verb`. Reactivate the replicate half once that verb ships; keep the from-zero half waiting for the Linux/macOS runs."
phase: explore
type: feature
vision_facet: "Distribution"
---

# new-machine-setup-guidance — how a fresh machine gets set up correctly

## Why

Setting up the owner's Windows machine (2026-07-20) took a full attended session.
Most of that was *migration* (a stale pip install, repos in the wrong root, a
hand-rolled statusline) which a clean machine never hits — but the session still
surfaced a real gap: **nothing tells an agent what "set up" means, or in what
order.** Each step is already one command; knowing the sequence is the missing part.

The owner will replicate this on Linux, macOS, and a second Windows box, and
expects the same account aliases on all of them.

## Intended outcome

An agent handed a bare machine can bring Horus to a correct, verified state
without the owner naming each step — because the owner's realistic flow is
"install, open Claude, tell the agent to set it up", not typing commands.

## Broad boundaries

Three candidate shapes, deliberately NOT chosen yet (2026-07-20 discussion):

- **A `horus-machine-setup` skill.** Cheapest: one string constant + one line in
  `SKILLS` in `horus/skills.py`, projected to Claude and Codex automatically, and
  `horus skill install --user --target all` already installs machine-wide.
- **A `horus init`-style command** that loads the guidance and opens an agent with
  it. Owner's instinct; explicitly deferred as premature while the product is in
  heavy development.
- **Three findings in `doctor machine`** (no account aliased / statusline not
  pointing at `horus statusline` / `workspace_root` unset). Read-only with fix
  commands, and unlike a first-run wizard it keeps helping on machine two and
  after something breaks.

**Both agent-facing options share a bootstrap problem:** the guidance only exists
after `horus skill install --user`, so neither removes the "one command first"
step it was meant to remove. Naming note: not `horus-init` — `horus init` already
scaffolds a *project's* `.horus/`, and the collision would mislead an agent at
exactly the wrong moment.

**Why deferred (the reasoning, so it isn't relitigated):** a skill costs one
string, but a *correct* skill costs several real from-zero runs — and those runs
are already scheduled. Writing v1 from one platform's evidence means rewriting it
after each machine. Capture the runs as card content first; promote to a skill
when the same manual sequence has been repeated twice.

## Raw material — the verified Windows sequence (2026-07-20)

Evidence for whatever gets written later. Windows-specific where noted; the
Linux/macOS equivalents are unverified and must not be asserted until run.

1. `uv tool install horus-harness` — then check for a **shadowed binary** (a stale
   `pip` install beating the uv shim; `doctor machine` catches it).
2. `horus config workspace-root <path>`.
3. Per account: log in, then `horus account --set <alias> --isolate`
   (`--agent codex` for Codex).
4. `horus statusline --install` — **the silent one**: skip it and usage data never
   appears, with no error anywhere.
5. Plugin parity for the isolated dirs — see `isolated-account-plugin-parity`.
6. `horus onboard github:owner/repo` per project.
7. `horus doctor` as the verification gate.

**Durable rule the runs must not violate: credentials never travel between
machines; aliases do.** Syncing `.credentials.json` / `auth.json` (the owner
floated Google Drive) means putting live OAuth tokens in cloud storage, they
refresh per-machine anyway, and it cuts against the isolation model. The thing
actually wanted — the same alias everywhere — is *derivable*: log in and run
`horus account --set <same-alias> --isolate`, and the canonical
`~/.horus/accounts/<agent>-<alias>` path follows by construction. The only
portable non-secret state is `[launch_profiles]` / `[workflow]` / `[tui]` in
`config.toml` — roughly ten lines, i.e. a dotfile in a private repo, not a Horus
feature.

## Raw material — migration findings (2026-07-20, retiring the Desktop checkouts)

Two assumptions in the migration tail were wrong on contact. Both are migration-only,
so they bear on the "migration or from-zero?" open decision below.

- **A clean `git status` does not make a checkout disposable.** All three Desktop
  copies were clean with nothing unpushed — but `.horus/sessions/` notes and
  `.claude/settings.local.json` are *gitignored*, so they are invisible to the check
  that was being used to authorize deletion. The fabric copy held a large earned
  permission allowlist plus three recovery notes its `projects/` twin did not have.
  Any retire-a-checkout step must inspect `git status --porcelain --ignored=matching
  -uall` and diff the machine-local content against the surviving copy first.
- **Transcript history is per-config-dir, and moving a repo orphans it.** Claude Code
  keys transcripts by cwd slug under *whichever config dir wrote them*: ambient runs
  land in `~/.claude/projects/<slug>/`, isolated accounts in
  `~/.horus/accounts/<agent>-<alias>/projects/<slug>/`. Moving a repo changes the
  slug, so history does not follow; renaming the slug dir inside the ambient config
  dir does not make it reachable from an isolated-account launch either. Owner
  decision this run: leave the stale `Desktop-*` dirs alone (43 MB) rather than
  rename or migrate them — stale history is not worth moving.

## Shape agreed with the owner (2026-07-20) — two branches, asymmetric confidence

The skill is **an ordering of existing `horus` commands, usable as a checklist** —
nothing more. Owner's framing, and it dissolves half of this card's deferral:

- **New user.** Walk the sequence, set up one account, then ask "another account, or
  continue?" — loop until done.
- **Replicate an existing setup.** Reuse the aliases already in use elsewhere, and help
  log each one in.

**Why the deferral now only binds one branch.** The original reason — "a correct skill
costs several from-zero runs, and Windows-only evidence means rewriting it" — is true of
the *from-zero* branch (which commands, what order, what is OS-specific). It is **not**
true of the *replicate* branch, which is fully determined today and is the one the owner
is about to run 2-3 times. Write the replicate branch prescriptively; write the from-zero
branch as a checklist that tells the agent to verify each step because it is unverified
on that OS. That asymmetry is honest and unblocks a v1.

**Hard dependency: `account-login-verb`.** The replicate branch's central step is "help
me log in", and no such command exists — `--isolate` requires a prior ambient login.
Without the verb, the skill's best case is a well-written apology instructing the
serial log-in/isolate/log-out dance through one shared dir. Ship the verb first; the
skill is much weaker without it.

**Alias correctness is the point of the replicate branch** (owner, 2026-07-20): the risk
is not effort, it is typing `work-claude` for `claude-work` and silently minting a new
account. So the skill must never ask the owner to *recall* an alias. Two sources, in
order: `worked_by` in remote PRDs once stamped (see `prd-worked-by-account`), else
transcribe the authoritative output of `horus account` / `horus account --agent codex`
from the machine being replicated. Never free-type from memory.

### Ordering requirements found by running it (2026-07-20)

- **Login before `horus statusline --install`.** `--install` loops *mapped* dirs
  (`cli.py:1934`), so an account must be mapped first; and a dir created by fresh login
  has no statusline pointer unless `account-login-verb` writes one. Either fix the verb
  or make the skill run `statusline --install` after the last login. Skipping it is the
  silent failure already noted below.
- **Expect onboarding, not a login screen.** `login_argv_env` runs `claude` bare, so a
  fresh dir shows Claude Code's onboarding; the user then runs `/login`. Say so.
- **Discovery returns the fleet superset.** A 2026-07-20 probe found 7 remote Horus
  projects for owner `rafaelmjf` but only 3 registered locally. The skill should present
  the union and let the owner *skip* accounts, not log into everything it finds.
- **Codex has no identity guard** (`codex-identity-guard`), so a mis-login there is
  invisible. Until that ships, the skill must tell the owner to verify the Codex
  `account_id` by hand after logging in.

### Open question that decides whether the skill is reachable at all — UNTESTED

`horus skill install --user` writes to `Path.home()/.claude/skills`
(`skills.py:2684`), but sessions run under `CLAUDE_CONFIG_DIR=~/.horus/accounts/
<agent>-<alias>`, and Claude Code resolves personal skills relative to its config dir.
On this machine **neither** `~/.claude/skills` nor `~/.horus/accounts/*/skills` exists —
every skill present is project-scoped in `.claude/skills` — so `--user` has never been
exercised here. On a fresh machine there is no project yet, making user scope the *only*
place the setup skill could live. **Test this before writing the skill**; if `--user`
installs somewhere isolated sessions never read, the skill is unreachable exactly when
it is needed, which is the same failure class as the statusline incident.

## Open decisions for backlog-refine

- ~~Which shape~~ — **decided 2026-07-20: a skill**, two branches (new user /
  replicate), as an ordering of existing commands. The `doctor` findings option is not
  an alternative but a companion, and has moved to `account-login-verb` (which adds the
  mapped-but-never-logged-in finding). The `horus init`-style command stays declined.
- Does `horus skill install --user` land where an isolated-account session can read it?
  **Blocks writing the skill** — see the open question above.
- Whether the guidance covers migration (stale installs, moving repos) or only
  from-zero. Still open; the 2026-07-20 findings below are migration-only evidence.
- Whether the from-zero branch waits for macOS too, or ships after Linux with the
  unverified-step framing.

## Source

In-session brainstorm, 2026-07-20 (owner-attended), following the Windows setup
run recorded in `windows-native-horus-setup`. Refined the same day against a
hand-executed run of the intended flow (the `claude-work` login and a mistaken
`codex-work` account, since unmapped), which produced the ordering requirements and the
`account-login-verb` / `codex-identity-guard` / `codex-isolated-config-leak` cards.
