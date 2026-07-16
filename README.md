# Horus

> Project continuity layer for coding-agent CLIs. Horus keeps a product
> owner's working memory — PRD, backlog, shipped ledger, closure rituals —
> repo-local, so any agent, on any machine, can pick up the role.

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
horus refresh github <owner>      # force-refresh a GitHub owner snapshot now
horus config workspace-root ~/projects # where remote projects should be cloned
horus start github:<owner>/<repo> # clone/register a remote Horus repo and show its resume prompt
horus onboard github:<owner>/<repo> # clone + blank Horus scaffold + PR (Git identity preflighted)
horus resume                      # print the minimum-context fresh-session handoff for this project
horus app                         # borderless animated companion; click opens dashboard
horus app --terminal              # terminal-native project/session launcher (`horus tui` alias)
horus open . --mode resume --target tmux # persistent attended session in this project
horus attach <session-id>         # reconnect this terminal to a Horus tmux session
horus session new "<title>" --agent codex # optional local recovery note
horus close                       # verify continuity, Codex usage, and print the closure ritual
horus close --usage-threshold 90  # warn when Codex context or rate-limit usage reaches a percent
horus usage check                 # check the same native-app usage signal directly
horus hook install --target codex --kind all # install Codex usage/merge/guard/checkpoint hooks
horus execution prompt --target codex # print a supervisor prompt for phased work
horus execution handoff 1A        # create .horus/temp/1A.md worker note
horus consolidate                 # route/prune/distill .horus lanes; prints the agent ritual
horus distill-history             # compress a large log into curated history.md
horus infer                       # bootstrap/refresh .horus from canonical docs; prints the ritual
horus skill install --target all  # install/update bundled Claude Code + Codex skills
horus reconcile instructions      # deterministic AGENTS.md <-> CLAUDE.md managed-block sync
horus forget <path> | horus prune # manage the dashboard's project registry
```

## Terminal application

`horus app --terminal` (or `horus tui`) is the terminal-native peer of the web
dashboard. It lists tracked projects and their next action, launches fresh or
continuity-seeded Claude/Codex sessions under a selected account, and lists live
sessions. The home screen shows cached account usage, each project's open sessions,
backlog/bug counts, and a Projection Sync warning when a tracked project's Claude or
Codex surface differs from the installed CLI. Projection Sync is read-only: its screen
shows each surface independently and can launch the registered `horus-agent` curator
with a bounded, dirty-worktree-safe repair prompt; it never mass-writes projects. A
project's Backlog action lists open cards by priority; a
card can seed a resumed session as its first task. Wide terminals arrange accounts
and projects into columns; narrow terminals stack and wrap the same content. Swipe or
use the mouse wheel/arrow keys to scroll the highlighted row;
Enter opens it, Esc goes back, and `q` quits. The list scrolls inside the application,
so returning to the first project restores the account rail and narrow phone terminals
never print raw arrow-key escape sequences. Termius already translates touch gestures
into conventional Up/Down bytes, so Horus preserves the normal mapping on phone and
desktop. `HORUS_TUI_INVERT_SCROLL=1` is an opt-in escape hatch for clients that report
the opposite direction. Press `d` for Defaults: besides launch permissions, it controls
continuity granularity. `handoff` (the default) batches canonical PRD/card/session-note
updates until an agent/account/machine change, dispatch, pause, release, or session end;
`delivery` checkpoints every PR; `manual` waits for an explicit checkpoint. Git delivery
evidence and commit/push/test safeguards remain active in every mode, while resume and
the TUI warn about product commits pending consolidation. A project can commit
`continuity_granularity` in PRD/project frontmatter to override the user default on every
machine and in required CI.

Terminal launches from both the web app and terminal app
automatically use a unique managed tmux session on Linux, macOS, and WSL whenever tmux
is installed, so a browser terminal is now a viewer of the same detachable session the
TUI can attach. Native Windows, hosts without tmux, and shells already inside tmux fall
back to the previous direct terminal host. Set
`HORUS_TERMINAL_TARGET=current` to force that fallback or
`HORUS_TERMINAL_TARGET=tmux` to explicitly require persistence. The session list labels
each live process as `attachable` or `original terminal only`. Scripted `horus open`
calls retain their explicit `--target window|current|tmux` behavior and window default.

To run more than one phone session, detach from the current agent with tmux's
`Ctrl-b`, then `d`. Horus returns without closing the agent. Launch another project or
press `s` to attach a running session; detach again to return to Horus.

Every launch is also scriptable, which makes shell aliases and mobile SSH-client
snippets straightforward:

```sh
horus open ~/projects/horus-harness --agent claude --account work --mode resume --target tmux
horus open ~/projects/site --agent codex --mode fresh --target tmux --detach
horus sessions
horus attach <session-id>
horus stop <session-id>
```

The existing scripted `horus open` default remains `--target window`, and `horus app`
still opens the desktop companion unless `--terminal` is passed.

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
the last successful snapshot and surfaces the latest error. Use the dashboard
Refresh button, or run `horus refresh github <owner>` / `horus refresh github --all`,
to force live discovery immediately.

Set the machine-local workspace root once, then start any remote catalog entry:

```sh
horus config workspace-root ~/projects
horus start github:<owner>/<repo>
```

`horus start` clones with `gh repo clone` when needed, refuses to overwrite an
existing non-git destination, registers the local clone, refreshes Horus-managed
project projections, and prints a generated minimum-context resume handoff plus
the matching `horus open` command. `horus resume` prints the same handoff for any
local Horus project: fetch-first, verify branch state, load only the current
frontmatter/next step up front, and lazy-load the deeper lanes only if the task
needs them.

## Repo-local continuity

```text
.horus/
  PRD.md          # vision, focus/next handoff, shipped ledger, load-bearing rules
  backlog/        # one card per evidenced open item; blank after a fresh init
  execution.md    # optional active execution plan for phased/subagent work
  requirements.md # optional declarative machine readiness probes
  sessions/       # optional local recovery notes (gitignored by default)
  temp/           # fleeting worker/subagent handoff notes (gitignored)
```

Older projects may still use the six-lane `project.md` / `roadmap.md` /
`features.md` / `decisions.md` / `history.md` structure. Migration is explicit;
`horus init` never changes an existing project's structure.

`AGENTS.md` and `CLAUDE.md` stay native; Horus only syncs the marked
`<!-- HORUS:BEGIN shared-instructions -->` block and detects drift elsewhere.
Horus project skills are scaffolded for both Claude Code (`.claude/skills`) and
Codex (`.agents/skills`).

Projects that depend on machine-local tools or configuration can commit an
optional `.horus/requirements.md`. `doctor project`, resume prompts, the web
dashboard, and the terminal TUI all render the same read-only readiness result;
see [machine requirements](docs/machine-requirements.md) for the schema and
safe probe rules.

When `PRD.md` (or `roadmap.md` on a six-lane project) recommends `plan-execution`, use `horus execution prompt
--target claude|codex` to frame the supervisor session and `horus execution
handoff <phase>` to create the worker note each native subagent should fill before
review. The temp handoff stays local; accepted outcomes are distilled into the
durable lanes during closure.

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
Otherwise leave the scaffold blank until the first real use case; init does not
create a fake backlog card or require an immediate inference pass.

`horus onboard` checks for a complete Git author identity before clone/init. If the
new target has none but the invoking repository does, Horus copies that identity as
target-local Git config; it never changes global Git configuration.

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

If `uv tool upgrade` keeps reporting success while `horus --version` stays at an
old release, the tool env was created under an interpreter older than the
current `requires-python` floor — uv then resolves the newest *old* release
that still fits. Migrate the env once:

```sh
uv tool install --force --python 3.12 horus-harness
```

The dashboard's Update button detects this pin and runs the migration itself.
After any CLI upgrade, restart Horus: a running dashboard keeps serving its old
in-memory build (it will refuse artifact writes and show a restart banner until
you do).

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
closure, hosted-session self-restart safety, and a Stop-time commit-and-push
checkpoint (warns when a session ends with a dirty tree or unpushed commits — opt out
per repo with `enforce_push: false` in `.horus/PRD.md`). Codex may ask you to
review/trust the hook with `/hooks` before it runs.

## License

Apache-2.0
