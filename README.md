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
horus dashboard                   # local, read-only multi-project web view (127.0.0.1:8765)
horus session new "<title>"       # create a dated session summary from the template
horus close                       # verify continuity, Codex usage, and print the closure ritual
horus close --usage-threshold 90  # warn when Codex context or rate-limit usage reaches a percent
horus usage check                 # check the same native-app usage signal directly
horus hook install --target codex # install a Codex Stop hook for automatic usage nudges
horus consolidate                 # route/prune/distill .horus lanes; prints the agent ritual
horus distill-history             # compress a large log into curated history.md
horus infer                       # bootstrap/refresh .horus from canonical docs; prints the ritual
horus skill install --target all  # install/update bundled Claude Code + Codex skills
horus reconcile instructions      # deterministic AGENTS.md <-> CLAUDE.md managed-block sync
horus forget <path> | horus prune # manage the dashboard's project registry
```

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

`horus close` also performs a best-effort read of local Codex rollout telemetry
from `$CODEX_HOME/sessions` when available. If the latest project turn is near
the configured usage threshold, Horus nudges you to run the closure ritual before
starting another large turn.

For a native Codex warning, run `horus hook install --target codex --path .`.
That writes a project-local `.codex/hooks.json` `Stop` hook which calls
`horus usage check --hook` after turns. Codex may ask you to review/trust the hook
with `/hooks` before it runs.

## License

Apache-2.0
