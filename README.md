# Horus

> Project-centric continuity and control panel for official coding-agent CLIs.

Horus keeps a project understandable over time — across agents (Claude Code, Codex),
accounts, environments, and days. It does not reimplement an agent loop and does not
use model API keys; it wraps the official CLIs and keeps durable project state in
repo-local `.horus/` files that native tools can read even when Horus is not running.

**Status:** early (alpha). MVP0/MVP1 shipped: continuity scaffolding, health checks,
a read-only dashboard, session/closure commands, and instruction-block sync. Agent
execution is intentionally deferred.

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
horus close                       # verify continuity and print the closure ritual
horus reconcile instructions      # deterministic AGENTS.md <-> CLAUDE.md managed-block sync
horus forget <path> | horus prune # manage the dashboard's project registry
```

## Repo-local continuity

```text
.horus/
  project.md      # purpose, current focus, shape (committed)
  roadmap.md      # roadmap + current focus (committed)
  decisions.md    # durable decisions + reasoning (committed)
  sessions/       # local session summaries (gitignored by default)
```

`AGENTS.md` and `CLAUDE.md` stay native; Horus only syncs the marked
`<!-- HORUS:BEGIN shared-instructions -->` block and detects drift elsewhere.

## License

Apache-2.0
