---
status: open
priority: low
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: deferred
readiness_reason: "Deliberately deferred until 2-3 real from-zero runs exist (Linux/macOS/Windows are planned). Writing it now means guessing which steps are hard, from Windows-only evidence, while the setup surface still changes daily. Reactivate after the second machine, or when someone who is not the owner sets Horus up."
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

## Open decisions for backlog-refine

- Which shape (skill / command / doctor findings / some pair) — decide **after**
  the Linux and macOS runs, from what actually proved hard.
- Whether the guidance covers migration (stale installs, moving repos) or only
  from-zero.

## Source

In-session brainstorm, 2026-07-20 (owner-attended), following the Windows setup
run recorded in `windows-native-horus-setup`.
