# Decisions — current rules

Durable rules in force, grouped by topic and kept concise (rule + terse why). This is
the *current* state, not a log — superseded decisions are dropped (only the rule that
won remains), and the narrative rationale / dead ends live in `history.md`. The full
68-entry dated decision log is preserved in git (the commit before the 2026-06-30
reflow) if a "why did we ever…" archaeology is ever needed.

## Product boundary & scope

- **Project-first, not Telegram-first** — the core value is durable project continuity across agents/accounts/machines; remote control is optional. The dashboard starts from projects.
- **No identity profiles (yet)** — model concrete `project + agent + account + environment + session`; use real accounts (`claude-personal`, …), nothing more abstract.
- **Omnigent is an interop target, not core** — Horus is the durable **memory plane**; Omnigent (Databricks, no project-memory) is an optional **execution plane**. Don't build a second orchestration/auth/control plane; freeze cockpit expansion. First seam (direction only, unscheduled): expose `.horus/` via a `horus mcp` continuity server. ↳ research/omnigent.md
- **Prior-art guardrails live in `research/`** — before building a substantial capability, check for a mature tool and prefer interop/adopt over reinventing.
- **First version = continuity + dashboard; execution deferred** — ship the memory/observability plane first (the `.horus/` convention already delivers most value with zero code); agent execution landed once a CLI-equipped machine was available.

## Continuity model (.horus/ lanes)

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral, usable by native Claude/Codex sessions without Horus running. Horus stays a helper, not a required runtime.
- **Six lanes, each in its lane; no fact in two files** — project (vision/focus), roadmap (open action points), features (capability ledger — shippable units, not tasks), decisions (current rules), history (rationale + bumps), execution (active plan). Cross-reference (`→ features.md`) marks an intentional split.
- **decisions = concise current rules grouped by topic; history = rationale + bumps** — neither is a dated log.
- **`execution.md` is a fluid active plan; `.horus/temp/` is gitignored worker handoffs** — replace execution.md per roadmap item (not a changelog). Workers write temp notes; the supervisor owns durable lane updates after review.
- **Resume from a generated minimum-context handoff** (`horus resume`) — fetch/prune, verify branch, load focus/next/exec-rec + latest session; lazy-load deeper lanes. A "read every lane first" startup burned ~11% of context. ↳ history.md
- **Context rollover is a closure opportunity** — surface usage/quota limits as a prompt to close before refresh; a fresh session resumes from `.horus/` instead of carrying old context.
- **Session continuity stays file-first** — no SQLite registry; `.md` sessions are ephemeral, distil upward, and re-parse instantly at solo scale. ↳ history.md
- **Distilled summaries archive, never delete** — after distillation a summary moves to `sessions/archive/` (local-only, excluded from the to-distill count), keeping the raw record recoverable.
- **Session visibility = read-only transcript discovery** — Horus surfaces every Claude/Codex session from the transcripts the CLIs already write, counts + timestamps only, never content. No hosting, no process control.

## Workflow & closure

- **Closure is part of the workflow** — a project-moving session isn't done until the lanes are updated; the dashboard renders current state, never inferred.
- **Closure is hybrid + verify-first** — `horus close --check` fails while any dashboard field is stale; closure edits only `.horus/**` + `AGENTS.md`/`CLAUDE.md`, never source after the user has walked away.
- **Closure always reaches the remote, fetch-first** — `horus close --commit --push`; committed continuity left local-only defeats the cross-machine guarantee. The push refuses when origin already has newer continuity commits (pull first) — no locking or merge machinery; git conflict resolution on markdown is the fallback. ↳ history.md
- **Git policy: branch → PR → auto-merge unless review** — a configurable per-machine `[workflow]` policy for Horus's *own* commits (onboard/close), so onboarding never leaves a local-only `.horus/`. Projecting the policy onto the in-session agent + a per-project override are deferred.
- **Both `AGENTS.md` and `CLAUDE.md` stay native** — a Horus-managed shared block (`HORUS:BEGIN/END`) kept aligned via `reconcile`/`doctor instructions`; the drift check normalizes the cross-reference line. Agent-specific instructions live outside the block. ↳ history.md
- **Three model-independent disciplines, every session** — reproduce the gate yourself; bound each pass to a green committed-and-pushed checkpoint; put safety in the code (guards), not the reviewer. ↳ history.md
- **CI tests run on the `requires-python` floor + latest** — dev interpreters are newer than the floor, so floor-only syntax breaks are invisible locally and only surface on install (v0.0.5 was dead-on-import under 3.11). `tests.yml` = pytest matrix + `compileall` gate on every PR/push; keep the matrix minimum equal to the pyproject floor. ↳ history.md
- **Python floor tracks uv provisioning, not distro pythons (>=3.12 since v0.0.7)** — uv auto-downloads the floor interpreter for tool installs, so raising the floor never degrades an install; it eliminated the PEP 701 f-string trap as a class. pip-on-old-system-python is not the audience. ↳ history.md
- **Committed hook commands are the `horus` console script, nothing interpreter-prefixed** — hook files travel with the repo to every machine; `python`/`python3`/`py -m horus` only resolves where horus happens to be importable ambiently (uv tool isolation prevents it; Linux has no `python`). uv guarantees `horus` on PATH cross-OS. ↳ history.md

## Execution & delegation

- **Delegation is a runtime-aware judgment call (volume × ambiguity × runtime)** — not a default, not "the supervisor reviews the worker." Delegate high-volume/low-ambiguity/clear-gate work (then reproduce the gate); stay inline for small/ambiguous/exploratory/debugging; the user is the gate for visual/UI. ↳ history.md, `delegation-decision-heuristic` memory
- **Every NEXT carries an `execution_recommendation`** — authored with `next_action`; `plan-execution` only for high-volume/low-ambiguity work with a clear gate, else `continue-as-is`. Missing = stale.
- **Execution plans justify delegation per agent** — `worker_tier` matters only *if* delegated; `delegation_basis` names what delegation buys on *this* runtime. `mode` (direct/delegated/test-delegation) is separate from tier.
- **Workflow tests require real delegation** — when validating the supervisor/worker model, a distinct worker must actually implement the phase and leave a handoff; a supervisor-written handoff doesn't count. ↳ history.md
- **Project execution via prompts, skills, and handoffs first** — `horus execution` prompts + `.horus/temp/` notes + the bundled `horus-execution` skill, before generating native agent config; model tiers stay symbolic (frontier/standard/economy).

## Accounts & auth

- **Account setup is login-driven, not path-entry** — the wizard takes agent + alias, derives an isolated dir, and opens the CLI's own login with `CLAUDE_CONFIG_DIR`/`CODEX_HOME` set; the sign-in populates it.
- **Onboarding uses GitHub auth; work uses agent-account aliases** — `horus onboard github:…` clones/inits/integrates via `gh`; the Claude/Codex account choice happens at the first work session. Two separate auth domains.
- **The real account email never lands in a commit** — sessions record a local alias (`acct-<sha6>` fallback); the identity→alias map stays per-machine.
- **Usage hook advises and asks; never overrides a command or strands work** — UserPromptSubmit = advisory context (do the user's request fully, incl. push); Stop = ask (close now vs push ahead); both use `horus close --commit --push`. ↳ history.md

## Dashboard & companion

- **Control cockpit retired; continuity is the dashboard's job** — session hosting/orchestration is ceded to Omnigent, and the cockpit only ever saw Horus-launched sessions. Usage + launch folded into the Projects tab.
- **Dashboard is read-mostly: explicit next-step + clickable roadmap** — renders current state, never infers it.
- **Heavy panels load async; pages paint instantly** — token-overhead, context-cache, and the project grid load via `data-horus-src` fetch (they parse session logs, ~seconds); the page never blocks on them, and account usage never blocks on the OAuth `/usage` call.
- **`horus app` pre-warms the dashboard in the background** — the mascot shows immediately (not blocked on the dashboard coming live); the dashboard window opens during startup; `--no-open` for mascot-only.
- **Owned dashboard window is default only where the raise is reliable (Windows)** — dedup is cross-OS but raise/focus isn't (Wayland has no API; `webbrowser.open` ignores `new=` on Windows); `--tab`/`--app-window` force either anywhere. ↳ history.md
- **Light mode is the default** — persisted per-browser (localStorage) with a header toggle + a Settings control.
- **The companion adopts only a same-version Horus dashboard** — a live 8765 server must identify via `/health` with the current `__version__`; stale/legacy Horus servers are replaced, a foreign server is never killed. ↳ history.md
- **Self-update is a passive pill + an explicit button — never automatic** — cached PyPI check, `uv tool upgrade` on click, and an honest "restart Horus to load it" banner (no hot reload; auto-respawn belongs to the MVP5 lifecycle work).
- **Offboard keeps `.horus/` by default; purge is opt-in** — `.horus/` is the durable committed memory and the most irreversible to delete; `--purge` (or the UI checkbox) removes it. Dry-run by default, like `upgrade-project`.

## Routines & skills

- **Cognitive routines ship as Claude/Codex skills; agent-delegated first** — `consolidate`/`distill-history`/`infer` run a deterministic read-only pre-pass + emit a ritual prompt for the in-loop agent (which sees the live context a file-only script can't). Edit scope `.horus/**` only. Autonomous (Horus-spawns-the-agent) variant deferred. ↳ history.md
- **Infer is LLM-based** — the deterministic inference path was removed (it produced drifting, truncated `.horus/`); `horus infer` distils `.horus/` from canonical docs and points at them rather than duplicating. ↳ history.md
- **rulesync is the eventual portability path, deferred behind Claude-first** — author native `SKILL.md` now and keep skills self-contained; Horus projects its own Claude/Codex skills + hooks directly for now and never embeds rulesync (npm/Node).

## Distribution & licensing

- **Distribute on PyPI via Trusted Publishing; build with `uv`** — OIDC, no stored token; publish real working code (anti-squat); package author name-only (no email). ↳ history.md
- **License: Apache-2.0** — permissive with an explicit patent grant; as sole holder, relicensing stays possible (loosening later is easy, tightening is hard).
