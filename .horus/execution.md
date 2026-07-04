---
status: active
current_feature: "Orchestration pilot: three parallel features — A dashboard brainstorm, B hosted-hub design, C trustworthy session badges — delegated to claude/work (Opus 4.8) and codex (GPT-5.5) feature supervisors; this session is the orchestrator."
supervisor_tier: frontier
worker_tier: per-phase (see table)
continuity_tier: economy
delegation_basis: "Pilot of orchestrator > supervisor > worker (PRD backlog). The orchestrator (Fable, this session) plans, routes, and accepts on deterministic signals only — required CI green on the exact commit, registry/RESULT events, close --check rc — it implements nothing and reruns no suites; for the one non-visual feature (C) it runs the single gate command from the handoff note before merge. Delegated sessions act as feature supervisors: they own implementation, their own runtime gates, and the handoff note; A may spawn sonnet subagents for narrow slices. Same-repo parallelism via git worktrees (Notes). Token/effort cost to be compared against the 2026-07-03 hub rounds baseline."
last_updated: 2026-07-04
---

# Execution Plan — orchestration pilot

Three features, two delegated supervisor sessions, one orchestrator. Wave 1 runs
A and C in parallel (disjoint dashboard surfaces, separate worktrees). B is
doc-only and starts on the codex account when C's PR is up. This file is the
fluid coordination surface; durable outcomes distill into PRD.md at closure.

## Model Policy

| tier | Intended use | This batch |
|---|---|---|
| economy | mechanical continuity updates | orchestrator's continuity commits |
| standard | narrow implementation slices | sonnet subagents under A (optional) |
| frontier | feature supervision, design, acceptance | A: claude/work Opus 4.8 · B+C: codex GPT-5.5 · orchestrator: Fable (this session) |

## Active Phases

| phase | status | difficulty | mode | worker_agent | worker_tier | delegation_basis | handoff_note | review gate |
|---|---|---|---|---|---|---|---|---|
| A-brainstorm-dashboard | PR #108 open, required CI green, handoff complete — awaiting Rafa's UI eyeball before the orchestrator arms auto-merge | medium | delegated | claude (account: work, model: opus) | frontier supervisor + optional sonnet subagents | UI + prompt-design feature; user is the real reviewer for the visual half; bounded by the dashboard contract and a CLI twin with tests | `.horus/temp/A-brainstorm-dashboard.md` (worker creates in its worktree) | required CI green on the PR + Rafa eyeballs the card/flow + orchestrator reads handoff for scope |
| B-hub-design | PR #110 open (doc-only, orchestrator read done, zero bounces) — awaiting Rafa's read before the orchestrator arms the merge | medium | delegated | codex | frontier | Doc-only architecture deliverable; cross-vendor cold reader is an asset; no repo-code risk | `.horus/temp/B-hub-design.md` (worker creates in its worktree) | no CI (doc); Rafa + orchestrator read; accepted when decisions are concrete enough to scaffold the repo in a future batch |
| C-badge-liveness | PR #109 open, auto-merge armed; orchestrator reproduced the gate (726 passed) + live probe (dead PID → stale, badge counts 1 running) after one bounce | medium | delegated | codex | frontier | Backend/registry slice, low ambiguity once specced, crisp pytest gate; codex auto-edit posture (read-only .git — orchestrator owns commit/PR mechanics) | `.horus/temp/C-badge-liveness.md` (worker creates in its worktree) | required CI green + orchestrator runs the one gate command from the handoff + live probe: a killed session must not count as running |

## Phase specs

### A-brainstorm-dashboard (claude/work, Opus 4.8)

Project detail gets an **Ideas / Brainstorm** card: a topic input + Start button →
POST (PRG) that launches a **tracked brainstorm session** on the project via the
existing run/launch plumbing, plus a CLI twin (`horus brainstorm --path . "<topic>"`)
so the dashboard and CLI share one code path. The brainstorm session is seeded with
a new `BRAINSTORM_PROMPT` template carrying **minimal context**: PRD.md
vision/backlog/rules + the topic — not sessions, not archive. Its output contract:
a structured implementation-plan draft (phases, risks, suggested gates) plus
proposed backlog lines written to `.horus/temp/brainstorm-<slug>.md` for review —
it must **never edit PRD.md directly**. Constraints: dashboard contract (PRG,
async heavy panels, read-mostly); do not touch the live-sessions panel, registry,
or companion (phase C owns those); do not edit PRD.md (orchestrator owns
continuity). Branch `feat/brainstorm-dashboard` → PR; leave the PR open (the
orchestrator arms auto-merge after review).

### B-hub-design (codex, GPT-5.5 — wave 2, doc only)

`research/horus-hub-design.md`: design for a **self-hostable hub** (à la
horus.rafaelfigueiredo.com, gym-app precedent) — one place to see projects and
launch agents across accounts, explicitly **not** shipped in the uv package; a
framework others can host themselves. Must include: threat model first (remote
agent launch = remote code execution; auth is a hard gate — Cloudflare Access
precedent from gym-coach), MVP cut (read-only multi-project dashboard behind auth
before any launch capability), interop seam (repo-local `.horus/`, session
registry, run logs as the API — hub stays a *consumer*), separate-repo scaffold
plan, and explicit non-goals (multi-user SaaS stays out per PRD vision). No code.

### C-badge-liveness (codex, GPT-5.5)

Sessions the registry claims are `running` must be **verified live** before being
counted anywhere: process/PID existence + run-log RESULT events, reconciled on
read. Dead/orphaned rows are demoted to a `stale` state — never counted as running
— with a visible flag and a one-click cleanup in the dashboard live-sessions
panel. Surface freshness ("as of HH:MM:SS") on the mascot badge menu and the
live-sessions panel so the number is auditable. Registry timestamps stay
aware-UTC. Tests must cover: dead-PID demotion, RESULT-event completion, badge
counts excluding stale rows. Do not touch project-detail templates or launch
plumbing (phase A owns those). Working tree only — .git is read-only under the
auto-edit posture; fill the handoff note and stop; the orchestrator commits to
`feat/session-liveness` and opens the PR.

## Notes — orchestrator contract (the pilot)

- **Worktrees:** A runs in `~/projects/horus-wt-brainstorm` (branch
  `feat/brainstorm-dashboard`), C in `~/projects/horus-wt-liveness` (branch
  `feat/session-liveness`), both spawned with `--watch` terminals per Rafa's
  visibility preference. Registry entries appear under the worktree paths —
  known cosmetic quirk for this pilot.
- **Acceptance flows on signals:** required `pytest (3.12)/(3.13)` checks on each
  PR (never a local suite rerun by the orchestrator), handoff-note gate command
  (C only, one run), Rafa's eyeball for A's UI, RESULT events for session
  completion. No tier accepts on a model's prose claim.
- **Merge order:** whichever PR is green first merges first (strict=false); the
  second rebases only if its CI goes red after the first lands.
- **Continuity:** only the orchestrator edits `.horus/` on main. Workers write
  handoff notes in their worktrees' `.horus/temp/` (local, uncommitted).
- **Measurement:** record rounds/interventions/token feel vs the 2026-07-03 hub
  sessions at closure; the pilot's verdict goes to PRD (orchestrator tier: keep,
  adjust, or drop).
- **Pilot findings (running log):**
  - Claude workers under the *default* posture stall headless: A planned fully,
    then exited asking for Edit/Bash permissions (exit 0, zero diffs — looked
    "completed" in the task list; exactly the trust gap phase C addresses).
    Branch-owning claude workers need `--posture full-auto` (or a pre-seeded
    allowlist in the worktree). A was resumed with full-auto, context intact.
    Codex under `auto-edit` ran without stalling. Intervention count: 1.
  - C's sandbox couldn't run the suite (read-only uv cache + no network for
    deps); its handoff said so honestly instead of claiming green. The
    orchestrator's gate run caught 1 failed/725 passed (a cli tail test seeding
    a fake-PID 'running' row that the new reconciliation rightly demotes) —
    bounced back to the same codex session with the exact failure.
    Intervention count: 2. Lesson: codex worker briefs must include a
    sandbox-runnable gate (compileall + targeted tests) or accept that the
    orchestrator's gate run is the first full-suite pass.
