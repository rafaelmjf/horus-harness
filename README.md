# Horus

> Project-centric continuity and control panel for official coding-agent CLIs.

Horus keeps a project understandable over time - across agents (Claude Code,
Codex), accounts, environments, and days. It does not reimplement an agent loop
and does not use model API keys; it wraps the official CLIs and keeps durable
project state in repo-local `.horus/` files that native tools can read even when
Horus is not running.

**Status:** early (alpha). MVP0/MVP1 shipped: continuity scaffolding, health
checks, a read-only dashboard, session/closure commands, instruction-block sync,
and agent-delegated continuity routines. Agent execution is still intentionally
small and incremental.

## Install

With [uv](https://docs.astral.sh/uv/):

```sh
uv tool install horus-harness     # installs the `horus` command
# or run without installing:
uvx --from horus-harness horus --help
```

With pip:

```sh
pip install horus-harness
```

## Commands

```sh
horus init [path]                 # scaffold .horus/ + managed AGENTS.md/CLAUDE.md blocks
horus doctor [project|instructions|all]   # continuity + instruction-drift health checks
horus upgrade-project             # report stale repo-local Horus projections
horus upgrade-project --apply     # refresh managed blocks, skills, and hooks
horus overhead                    # estimate Horus prompt footprint + observed token usage
horus dashboard                   # local, read-only multi-project web view (127.0.0.1:8765)
horus discover github <owner> --save # show remote Horus repos for a GitHub user/org
horus config workspace-root ~/projects # where remote projects should be cloned
horus start github:<owner>/<repo> # clone/register a remote Horus repo and show its resume prompt
horus app                         # borderless animated companion; click opens dashboard
horus session new "<title>"       # create a dated session summary from the template
horus close                       # verify continuity, Codex usage, and print the closure ritual
horus close --usage-threshold 90  # warn when Codex context or rate-limit usage reaches a percent
horus usage check                 # check the same native-app usage signal directly
horus hook install --target codex --kind all # install Codex usage/merge/guard hooks
horus consolidate                 # route/prune/distill .horus lanes; prints the agent ritual
horus distill-history             # compress a large log into curated history.md
horus infer                       # bootstrap/refresh .horus from canonical docs; prints the ritual
horus skill install --target all  # install/update bundled Claude Code + Codex skills
horus reconcile instructions      # deterministic AGENTS.md <-> CLAUDE.md managed-block sync
horus forget <path> | horus prune # manage the dashboard's project registry
```

## GitHub remote catalog

The lightweight dashboard can also show Horus-enabled repos that are on GitHub
but not cloned on this machine yet. It uses the authenticated `gh` CLI and treats
GitHub as a remote catalog for durable `.horus/` files, not as a live session
store:

```sh
gh auth login
horus discover github <user-or-org> --save
horus dashboard
```

Remote repos appear when `.horus/project.md` is readable. The dashboard shows
their current focus, next action, whether this machine already has a matching
local clone, and a `horus start github:<owner>/<repo>` command for remote-only
projects. Once a GitHub owner has been fetched successfully, Horus stores a
machine-local snapshot under `~/.horus/github-cache/`; later dashboard loads can
render that snapshot immediately with a last-refreshed note while live discovery
refreshes the cache separately. If live refresh fails, the dashboard keeps showing
the last successful snapshot and surfaces the latest error.

Set the machine-local workspace root once, then start any remote catalog entry:

```sh
horus config workspace-root ~/projects
horus start github:<owner>/<repo>
```

`horus start` clones with `gh repo clone` when needed, refuses to overwrite an
existing non-git destination, registers the local clone, refreshes Horus-managed
project projections, and prints the repo's stored `next_prompt` plus the matching
`horus open` command.

## Repo-local continuity

```text
.horus/
  project.md      # vision, shape, boundaries, current focus
  roadmap.md      # open action points
  features.md     # shipped / in-progress / planned capability ledger
  decisions.md    # durable decisions + reasoning
  history.md      # curated lessons / "bumps in the road"
  sessions/       # local session summaries (gitignored by default)
```

`AGENTS.md` and `CLAUDE.md` stay native; Horus only syncs the marked
`<!-- HORUS:BEGIN shared-instructions -->` block and detects drift elsewhere.
Horus project skills are scaffolded for both Claude Code (`.claude/skills`) and
Codex (`.agents/skills`).

## Adding Horus to a project

Run this once from the project root:

```sh
horus init -y --skill-target all
horus hook install --target codex --kind all
horus hook install --target claude --kind all
horus doctor
```

For an existing project with useful README/status/roadmap docs, run `horus infer`
after init and let the in-app `horus-infer` skill distill the docs into `.horus/`.

## Keeping projected artifacts current

Upgrading the Horus CLI updates the command code, but not repo-local projected
artifacts that were copied into each project. To check and refresh those safely:

```sh
uv tool upgrade horus-harness
cd /path/to/project
horus upgrade-project          # dry-run/report
horus upgrade-project --apply  # refresh managed blocks, skills, and hooks
horus doctor
```

`upgrade-project` only touches Horus-managed/projection surfaces: the managed
blocks in `AGENTS.md`/`CLAUDE.md`, bundled skills, and native hooks. It does not
rewrite source files or author `.horus/` lane content.

## Measuring Horus overhead

To quantify the token cost Horus adds to a native-agent workflow:

```sh
horus overhead
horus overhead --sessions
horus overhead --agent codex
horus overhead --agent claude
horus overhead --baseline
horus overhead --baseline --without-horus codex:<A_SESSION> --with-horus codex:<B_SESSION>
```

The report has two parts: a rough static prompt footprint for Horus-managed
instructions, skills, and hook prompts; and observed local usage from native
agent logs. Observed attribution is intentionally labeled as an upper bound:
when a turn touches Horus files or commands, the whole turn is counted as
Horus-related because local logs do not expose the counterfactual cost of the
same turn without Horus.

With `--sessions`, Horus also joins the machine-local session registry to native
logs by session id and reports per tracked-session token totals where the native
app exposes a matching id. Claude sessions and headless Codex sessions can match;
interactive Codex PTYs may show as unmatched because Codex does not accept
Horus's preassigned session id.

For a controlled incremental-cost estimate, run `horus overhead --baseline`.
The recipe is intentionally strict: run the same task on the same repo commit,
account, model, and permission posture once without Horus projection and once
with the normal Horus-enabled project. Then pass only the native session ids via
`--without-horus` and `--with-horus`. If the clean run happened in a separate
clone, add `--without-horus-path /path/to/clean-copy`. The comparison stays
aggregate-only: matched sessions, turn counts, token totals, and delta. It does
not print transcript content.

`horus close` also performs a best-effort read of local Codex rollout telemetry
from `$CODEX_HOME/sessions` when available. If the latest project turn is near
the configured usage threshold, Horus nudges you to run the closure ritual before
starting another large turn.

For native Codex warnings and gates, run `horus hook install --target codex --kind all --path .`.
That writes project-local `.codex/hooks.json` hooks for usage closure, pre-merge
closure, and hosted-session self-restart safety. Codex may ask you to review/trust
the hook with `/hooks` before it runs.

## License

Apache-2.0
