---
status: active
current_focus: "2026-08-07 — OpenWiki experiment on `experiment/openwiki`: installed OpenWiki 0.3.1 locally, authenticated its ChatGPT provider, and generated a source-grounded repo wiki. The visualizer serves 20 pages with 44 links; its HTML, graph API, frontmatter, relative links, workflow YAML, whitespace, and secret scan all passed. The generated workflow is manual-only because no repository provider secret is configured. Targeted affected suites pass (268); two full-suite attempts ended without a pytest verdict at about 31%, so full-suite status is unknown."
next_action: "Review the generated OpenWiki pages and visualizer, then keep, trim, or drop the experiment. If keeping it, choose and configure the CI provider secret before enabling a schedule; the committed workflow intentionally stays manual-only. The prior owner decisions remain: build `account-login-verb` to unblock `codex-isolated-config-leak`, and separately decide whether to release the eight commits after v0.0.81 so skill-usage recording becomes live."
next_prompt: "Resume horus-harness; `git fetch --all --prune` first. The OpenWiki trial is on pushed branch `experiment/openwiki`; inspect `openwiki/quickstart.md` and run `openwiki visualize openwiki --no-open` to review it. OpenWiki 0.3.1 and ChatGPT credentials are machine-local; no secret was committed. The generated workflow is manual-only pending a provider-secret decision. Targeted tests passed 268; the full suite twice ended near 31% without a verdict. If the experiment is declined, return to main's two owner decisions: `account-login-verb` and a separate v0.0.81 follow-up release."
execution_recommendation: "continue-as-is — no delegation was requested; reviewing or trimming this single experimental branch is direct work."
last_updated: 2026-08-07
last_product_audit: 0.0.79 2026-07-31
horus_min_version: 0.0.26
---

# Horus — PRD

## Vision

Horus is a lightweight, repo-local **product owner** for official coding-agent CLIs (Claude Code, Codex, more later) — a PO's memory *and* rituals, made repo-local so any native agent session can pick up the role. Continuity is the proven spine. The Vision resolves into named **facets**, each with a definition of done the backlog converges toward (cards carry `vision_facet`):

**Why this exists.** Every fresh agent session started from zero — re-explaining what the project is, what was already decided, and what to do next — while an owner running several projects across multiple provider accounts and machines had no way to see or steer them without opening each terminal. Built for **one solo owner-operator**, deliberately: multi-human collaboration is a standing non-goal, which caps the audience on purpose. Two pivots shaped what it is now: **widened from "continuity layer" to "repo-local product owner"** (2026-07-16, after dogfooded research in `research/2026-07-16-po-capabilities.md`) with continuity staying the core and PO-lifecycle the open frontier; and the **continuity value finding** (2026-07-15) — the proven spine is resume frontmatter + pushed git/PR state + fetch-first, local recovery notes are an optional fallback, and the earlier multi-lane taxonomy plus mandatory per-session prose were overhead. Telling deliberate inheritance from legacy, so a reader never has to ask: the retired lane files in `.horus/archive/` are kept **on purpose** — this repo is the worked example of its own convergence machinery, not a project that forgot to clean up. Support for that retired structure was removed from the product on 2026-08-02; the archive is history, not a live layout. The package name **`horus-harness` is legacy, not a claim**: in agent-land a "harness" runs the agent loop (Claude Code and Codex are the harnesses) and this Vision explicitly disclaims orchestration; the name predates that clarity and is tracked by `product-naming`. Sibling repo `horus-agent` is an instruction rung that deliberately never grows Python or a service.

| Facet | Definition of done |
|---|---|
| **Continuity core** | A fresh agent session resumes the exact next step from durable state alone, fetch-first, across machines. |
| **Dashboard / cockpit** | Owner sees fleet state and launches/resumes any project from web or phone, no terminal command. |
| **Accounts & isolation** | Every account runs isolated by default; cross-account corruption impossible; usage visible per account. |
| **Delegation calibration** | Agent picks execute-vs-dispatch + a model tier from live measured data, owner-gated, honest cost — never auto-routing. |
| **PO lifecycle** | The forward loop — market research → vision → vision-convergent roadmap → ship — runs repo-local (frontier: discovery + convergence are the open gap). |
| **Introspection & self-improvement** | Every recurring surface, skill, and process can be audited against reality on evidence, yielding owner-gated verdicts (demote/defer/retire/revise), never ceremony. |
| **Autonomous dispatch** | A scheduled worker+supervisor loop runs approved cards end-to-end on this machine under the owner's accounts and a standing pre-authorized envelope: dispatch attachable + worktree-isolated, independently verify (required CI on the exact SHA + freshness + live probe, never worker self-report), then merge/close/ship — or halt dependents and escalate. |
| **Distribution** | `uv tool install` yields a safe, current, isolated setup on all three OSes; the hosted app tracks releases. |

**The roadmap breathes — divergence then convergence (2026-07-16):** the facet set and their DoD are a *living hypothesis*, not a frozen contract. A project's real path is research → **divergence** (ideas explored as PoCs, some outside the first vision) → usage → **convergence** (drop, trim, rescope toward a consistent product; directions that prove out are promoted into new facets). Convergence is triggered by usage evidence, not schedule; exploratory work is expected to lack a facet/DoD until it earns one or is dropped. This repo is the worked example (multi-lane → consolidated PRD/backlog). Convergence machinery **shipped** (`roadmap-convergence`, archived); the open card is `explore-converge-lifecycle` (the explore phase).

The durable value is the **memory + planning plane, never orchestration**: repo-local `.horus/` files any native agent can use without Horus running; a read-mostly dashboard (projects, current focus, next step, sessions, accounts/usage); visibility into which agent/account/environment touched a project. Deliberately NOT the superpowers/spec-kit framework depth.

Model concretely: `project + agent + account + environment + session` — no abstract identity profiles. Native-app-first: design capabilities on Claude/Codex's own surfaces before a Horus-owned session layer. Execution planes own orchestration (see `research/omnigent.md`); Horus stays the memory/planning plane and interops via `.horus/`.

**Surfaces and audiences.** Horus has many entry points and only ONE of them is the contract. An unlabelled surface gets mistaken for the contract — that already cost a `fabric-build` session most of its length (it read an interactive human command as the agent contract; card `vision-omits-intent-and-audiences`, #405).

| Surface | Serves | Contract? |
|---|---|---|
| **`.horus/` files** | agents, any vendor, no Horus installed | **YES — the only one.** Committed, vendor-neutral; Horus is a helper, never a required runtime |
| `horus` CLI (61 subcommands) | human operator + agent | No — a helper over the files; also the *only* authority on "what exists now" (`--help` / the argparse walk) |
| Terminal TUI | human operator, desktop + phone over Termius SSH — the daily cockpit | No — renders CLI-callable primitives, never a second parser or state path |
| Hosted dashboard | human operator, read-mostly, Cloudflare-Access-gated | No — a companion viewer; exposure is an explicit launch property, never ambient config |
| Telegram (`notify` + `notify listen`) | human operator, away-mode | No — bounded deterministic grammar, owner-locked, and it **never mints authority** |
| Statusline + hooks | the agent CLI itself (Horus is the consumer, not the caller) | No — signal injection; hooks advise and ask, never override |
| Bundled skills | agents | No — **optional workflow policy**; nothing in the code breaks if they are never invoked |
| Required PR checks | CI | No — verifies field validity + git checkpoint state; it never blocks a merge on prose |
| Managed block + projections | consumer projects across the fleet | No — vendored continuity; each project's own `horus_min_version` governs |

**Out of scope:** the *distributed* execution/orchestration plane (multi-machine worker control, agent marketplace) — the single-machine, owner-pre-authorized dispatch loop was promoted in from this line on usage evidence (2026-07-17, vision-branch-x3); multi-user SaaS; identity abstraction; continuous external monitoring (the always-on competitor-scraping SaaS category — discovery is one-shot, evidence-first, not a live feed); rebuilding a ticket system (agent-first boundary below).

**Agent-first structure, minimal overhead (boundary, 2026-07-17):** Horus adapts proven work-system concepts (kanban, epics) for *agents* doing digital work. Every structure must be machine-readable and earn its place by making a fresh agent session act more correctly or more cheaply — never by adding human-process ceremony. Adopted translations: epics → vision-branch umbrellas; kanban pull → capacity-triggered dispatch; andon → escalation halts dependent work; WIP limits → collision control via `parallel`/`surface` stamps. Declined: sprints, story-point estimation, boards, standups, extra card workflow states. Multi-human parallel collaboration is a non-goal until real usage demands it.

## Backlog

Prioritized open work. Features and bugs share one menu; jump order is allowed. Mark bugs **[bug]**, ops chores **[ops]**.
### Open by readiness — see `.horus/backlog/`

Counts and per-card state are NOT restated here — `horus backlog list` computes them exactly, and `horus backlog list --archived` shows what has shipped. Two of the away-mode drill's three legs are deliberately *reserved* (`verify-guidance-long-running-services`, `audit-advisory-interval`) via `readiness: deferred` plus a named trigger, which is the mechanism that keeps a reserved leg out of the selector. **Do not promote something to refill the autonomous queue.** The Shaping pool is deliberately unsequenced.

**A facet can read as converged because its cards were shelved (2026-08-03).** Shipping the last open `Dashboard / cockpit` card left that facet with zero open cards, which `horus consolidate` reports identically to a converged one — while the owner states they are *not using the hosted dashboard at all*, i.e. it is nowhere near "sees fleet state and launches/resumes any project from web or phone". Its six cards are `shelved`, not delivered. So read a zero-open facet against its definition of done before crediting it, and note the live cockpit is the TUI. Whether the facet gets rescoped is a convergence decision for the owner, not a hygiene fix.

**Refinement finding worth carrying (2026-07-28).** Conversion tracks the *kind* of open decision, not whether a card documents one: **30 of 36 Shaping cards already carried an explicit open-decisions section** (17 under the literal heading `## Open decisions for backlog-refine`) and the pass still converted 1 in 13. Editorial and parametric items resolve in one exchange; strategic and architectural ones do not, and should not — `merge-release-owner-gate` is the best-structured card in the repo and correctly went to its own session anyway. So cards now tag each open decision `[refine]` (answerable in a screening exchange) or `[session]` (needs a working session), and a card whose items are all `[session]` leaves the screening pool instead of costing an exchange every pass. `refine_passes:` (int, additive, seeded as a floor — 2 where a prior `last_refined` existed, else 1) makes "screened N times, never moved" deterministic, since `last_refined` overwrites and a no-change pass otherwise leaves no trace. Both land via `refine-autonomy-hardening-lens`.

## Shipped

One line per capability. Details live in git history — every entry carries its PR, tag or
SHA — and `horus backlog list --archived` lists the delivered cards with their provenance.

**A closed session reads as closed on the surface in use** (2026-08-03, #498): `registry.display_status` gives #489's `is_deliberate_close` its first production caller — it had none, so 74 of 252 rows still read `failed` under a green test. Scoped to `horus sessions`; retiring the Sessions section was refuted (`is_attachable`/`is_restorable` gate on `status`).

**Six-lane (v2) continuity support removed entirely** (2026-08-02, #495, block v18->v19): the fleet had zero v2 projects, so 19,036 chars of fallback across 20 skills, the v2 prompt variants, the one-way migration command and the `features.md` capability layer all went; `.horus/archive/` keeps this repo's own lane files as history.

**`## Rules` cut 84 -> 61 by enforcing Rule 80** (2026-08-02, #491 + #492): behavioural text routed into the skill that performs each activity; deletion-dominant, because 13 of the first 19 were already stated there. PRD 59,480 -> 48,656 chars, budget headroom 2,550 -> 11,344.

**`horus prune --worktrees` reclaims dead worktrees** (2026-08-02, #494): 5 of 5 on this machine, 104 MB; `[gone]` upstream detects a squash-merge with no `gh` and no network, and dirty/unpushed/open-PR are never touched.

**An unreachable gate is a deterministic finding** (2026-08-02, #493): an active card whose `depends-on` names a shelved or retired blocker — or no card at all — is reported, after one such gate survived three consecutive closes unseen.

**`horus-release` skill, and skill-invocation telemetry** (2026-08-02, #496 + #497): the release runbook stops living in three unversioned prose copies; `horus skill usage` counts which bundled skills are actually invoked, from a PreToolUse(`Skill`) hook verified live.

**v0.0.81 released by a dispatched worker, end to end** (2026-08-01, tag `v0.0.81`, bump #490): first delivery datum the delegation-calibration facet has ever had — gpt-5.6-luna@max ran all ten steps in 362s, touched exactly 3 files, and left `.horus/` alone.

**A session the owner closed reads as closed** (2026-08-01, #489): `registry.STOPPED` joins `TERMINAL`, `is_deliberate_close` reads the status+`termination_reason` pair so 73 historical rows self-correct without backfill, `orphaned` finally gets written by the reaper, and `delivery.NONCLEAN_STATUSES` keeps its receipt.

**v0.0.80 released, published and deployed** (2026-08-01, tag `v0.0.80`, bump #488): 33 commits carrying the honest-counts arc; PyPI live, hosted `/health` on 0.0.80 with `/` still 403, and the pinned install upgraded so the machine's CLI finally matches the repo.

**The backlog got a box, and the counts stopped lying** (2026-08-01, #485 + #486 + #487): `shelved` is a status for declining to DECIDE, distinct from `retired` and from `deferred`; 69 of 71 cards swept into it, `--shelved` is the read path, and a bug can never be shelved (`fail`-level). Fleet rows report `active N · bugs M` from the one status definition.

**The archive is the closed ledger, not the delivery ledger** (2026-08-01, #481): `--archived` headed all 132 cards "Shipped" when 22 had never been built, which misled this session into recording a retired card as delivered; `partition_archived` splits them and gives the graveyard its first read path.

**`roadmap-branches` v8 — the narrative read-out restored** (2026-08-01, #480): four runs failed to reproduce the 2026-07-17 convergence-test receipt because a 2026-07-20 calibration turned section 1 from prose into a citation, relocating facet coverage into the branch list where it forced padding. 246 -> 180 lines.

**Two settled cards, each with a defect its card had not foreseen** (2026-08-01, #484): the audit advisory needs 10 releases AND 14 days, the AND applying only within a minor line because `releases_since` is a lower bound across one; `wildcard` became the 20th bundled skill, exposing a missing v2 fallback.

**Long-running services are verified by signal, not by starting** (2026-08-01, #483, managed block v18): a service/daemon is verified when it reaches `active`/running AND emits its expected journal or health signal. Delivered by the away-mode drill's one real leg.

**Bundled skills declare an audience** (2026-07-31, #466 `7dcedfa`, from #462): `Skill` gains `audience`, so Horus-only skills stop projecting into managed projects; install, staleness, doctor and upgrade all read it together.

**Status line names the spending account** (2026-07-31, #467): row 1 becomes `user@host:cwd │ account │ model`, alias under isolation and the authenticated email outside it.

**wildcard v5 — provenance, not formatting** (2026-07-31, #468): ideas come from facet-DoD-vs-code, owner friction and outside evidence; the backlog is a duplication check only, and every idea must be buildable and self-sufficient.

**The CLI is the authority for shipped state** (2026-07-31, #469): `horus backlog list --archived` opens a read path onto the previously write-only archive; `prd_readiness_count_findings` retired with the prose cache it policed; a per-entry Shipped size signal replaces a line cap that could not see the problem.

**PRD.md trimmed to orientation** (2026-07-31, #470): Shipped returned to one line per capability and the readiness paragraph became a pointer at `horus backlog list`; ~52,400 -> ~36,600 tokens, with three lessons that lived only in Shipped prose promoted to Rules first.

**Managed block stops projecting this repo's war stories** (2026-07-31, #471): block v16->v17 keeps the rules and moves two dated incidents to `archive/history.md`; a guard fails CI on any `Observed <date>` narrative in the projected block.

**PRD size signal measures cost, not shape** (2026-07-31, #472): the line cap becomes a 45k/60k character budget, section ranking moves to characters, the unwrap advice is deleted, and `## Rules` gains its own 600-char entry contract.

**Handoff fields budgeted, and a retained previous state flagged** (2026-07-31, #473): `current_focus`/`next_action`/`next_prompt` warn past 800 chars, and an `OLD:` clause inside a current-state field is named — those fields are read by every PRD-first surface on every launch.

**Local recovery notes untracked, and the checkpoint harvest fixed** (2026-07-31, #475 + #476): five notes were tracked against a gitignore rule present since the first commit, one at 164,300 chars; the harvest appended to the newest note by mtime, and appending updates mtime, so a note could never age out — it now refuses a note whose `status` is terminal.

**The pathfinder chain corrected after three rejected runs** (2026-07-31, #477 + #478 + #479): the facet parser stopped reading the surfaces table as facets; `roadmap-branches` v4->v7 (directions not backlog, problem before mechanism, facet table restored as the spine); `pathfinder` v9->v10 (all 8 steps tabled); every skill projection pinned to source.

**Rules narratives routed to history.md** (2026-07-31, #474): 22 over-budget entries -> 0; narrative-heavy rules condensed with the story moved to `archive/history.md`, dense spec rules split so each states one thing (71 -> 77).

**`product-audit` rescoped to the host project, release clock unstuck** (2026-07-30, #463 `e3f0992` + #464 `b18358b` + #465 `477c1a4`, from #462): the skill audits the repo it runs in; `releases_since()` no longer cancels to zero across a minor bump.

**v0.0.79 released, published and deployed** (2026-07-30, tag `v0.0.79`, bump #461 `383eab4`): carries #449 and #452–#460; cut only after a pre-release sweep found the headline feature non-functional.

**Pre-release sweep for 0.0.79 — session restore broken twice over** (2026-07-30, #459 `b15fa1c` + #460 `ee191cd`): Restore was unreachable, and once reachable crashed the cockpit; both fixed and verified live.

**Delegation authorization and its substrate made explicit** (2026-07-30, #437 `240075e`): absent an explicit owner request `execution_recommendation` is `continue-as-is`; `native-subagent` split from `horus-worker`.

**Session restore — reopen a session that vanished** (2026-07-30, #456/#457/#458): launches record the agent's own thread id; the TUI lists vanished sessions and offers Restore, reusing the original registry row.

**Suite-wide isolation of test state from the owner's environment** (2026-07-30, #455): autouse private `HOME`, `TMUX_TMPDIR` and `HERDR_SOCKET_PATH`, after a test stopped the owner's herdr server.

**Everything shipped before 2026-07-30 lives in the archive, not here** — `horus backlog list --archived` lists all 113 delivered cards with PR and SHA, and since #481 separates them from the 23 closed without shipping. Nineteen dated entries were removed 2026-08-01: if a command can produce it, prose must not cache it.

**Distribution (current v0.0.81):** PyPI trusted publishing; three-OS install smoke; hosted pinned-install deployment; Apache-2.0. **Invariant: publishing a version does NOT update the hosted app — `scripts/deploy-hosted.sh` is the last step of every release.**

## Rules (load-bearing)

- **herdr's `agent_status` is inferred, not reported (2026-08-01).** It is scraped from the terminal title, so Claude reads `working`/`idle` and Codex reads `idle` with a shell prompt — and even Claude flickers between reads. The socket API exposes `pane.report_agent` with a `blocked` state, but the shipped `claude` (v7) and `codex` (v6) integrations only call `pane.report_agent_session`: an unimplemented path, not a herdr limitation. What they do give is `agent_session_id`, the same key Horus stores for session restore — a stronger correlation than `pane_id` alone.

- **One status list, imported everywhere (2026-08-01, #481/#485/#486/#489/#498).** `backlog.INACTIVE_STATUSES` is the one definition; three hand-copies each lied differently. A display that aggregates states must distinguish them: `failed` covered both a crash and deliberate close. Missing display text can hide truth without losing it—the intent remained in `termination_reason`, so reading the pair needed no backfill. A predicate with no production caller fixes nothing; assert the surface, not only the helper.

- **SSH into this machine is Tailscale SSH, not `sshd` (2026-08-01).** `openssh-server` is not installed and nothing listens on 22 *by design* — `tailscaled` intercepts at the TUN layer. So `ss -ltn | grep :22` finds nothing on a working setup, and dialing your own tailnet IP is a false negative because it bypasses that interception. Confirm with `journalctl -u tailscaled | grep -i ssh`. Any standard client works: Termius on iOS, native OpenSSH on Windows.

- **Never make a critical function depend on one session host (owner, 2026-07-31).** tmux is the most stable option, the native terminal is the Windows path, and herdr is one host among three — adopted (11 of 26 sessions since v0.0.78) but not a foundation. A capability that only works under herdr is not delivered. This caps how far host-native adoption can go: read from a host opportunistically, never require it.

- **A generated file that no test compares to its generator is hand-maintained by accident (2026-07-31).** Projection-equality was asserted for 8 of 19 skills, so `horus-consolidate`'s description drifted onto main unnoticed. One test now walks `skills.SKILLS` and both agent roots. The fleet half is still open: consumer staleness compares version MARKERS, so content edited without a version bump reaches nobody while `upgrade-project` reports "up to date".



- **If a deterministic command can produce it, prose must not cache it (2026-07-31).** PRD.md had grown to ~54k tokens, 82% retrospective, with the Vision at 9%. The `## Backlog` readiness counts were a hand-typed copy of `horus backlog list`, and a *check* (`prd_readiness_count_findings`) existed purely to catch the copy drifting — both were deleted together, since a duplication's guard is cheaper to remove than to maintain. General form: **prose in one artifact has no effect on another artifact's machine-readable state.** (#469/#470; `archive/history.md`.)

- **A passing test is not evidence against a network-dependent theory — check the precondition directly (2026-07-26).** The test that reproduced the credentials flake passes when the live call *fails*, so a green run was misread as refuting the correct hypothesis and the real fix (#406) was recorded as "not a verified fix" for days.

- **Anything PROJECTED into every project is a product surface FOR those projects—bundled skills and the managed block (2026-07-30/31).** Write and audit it from a consumer's seat; block rules must be general, while this repo's incidents belong in `archive/history.md`. A stale skill is a stale program where text is the behavior. A bundled-skill fix reaches the fleet only through a release; `upgrade-project --apply` before that release installs the pre-fix version. (#462/#463/#466/#471; `skill-drift-surfacing-and-refresh`.)

- **Derive a fixture from the writer that really produces it; never hand-write the end state (2026-07-30).** The tell is a fixture whose docstring names a producer it does not call. Build the pre-state, run the producer, then apply overrides on top. 2,400 green tests hid a TUI feature that was unreachable in life, and the test written for that exact defect passed vacuously until the fixture became real. (#460; `archive/history.md`.)

- **Ask a context-dependent predicate in its context before calling it dead (2026-07-30).** A sweep reported herdr's `switch_hint` as unreachable text because `switches_in_place()` measured False — but it returns `inside_herdr()`, so the reading was an artifact of probing from outside herdr, where the existing message is correct. Same shape as `$TMUX`: these predicates answer "am I inside this host *right now*", so a value sampled from the wrong place is not evidence about the code.

- **`0.1` is reserved for the first version the owner considers stable enough to hand to someone else to test (owner, 2026-07-29).** Until then releases stay on `0.0.x` however structural the change — the session-host layer shipped in 0.0.78, not 0.1. So do not read a patch bump as "small", and do not propose `0.1` to signal architecture; it signals shareability.

- **A mock that ignores an argument agrees with the code instead of checking it (2026-07-30).** `restore_session` silently failed to forward `reg` to `host.launch`, so a caller's registry was ignored and the host wrote to the default one — while reporting success. The unit tests passed because their fake host accepted `**kw` and never asserted on it; a live probe found it in one run, by observing that the row it handed in stayed `stale` and that the REAL registry had grown. When a collaborator's job is to receive something, assert it received it.

- **Test state must never escape into the owner's real environment, and the guard belongs in `conftest.py` — never in the test (learned twice, 2026-07-13 and 2026-07-30).** A per-test guard protects exactly the test that remembers it. `tests/conftest.py` isolates `HOME`, `TMUX_TMPDIR` and `HERDR_SOCKET_PATH` for every test, so a host added later inherits isolation instead of re-learning it by breaking something. Two corollaries: **a docstring claiming isolation is not isolation** — assert it — and **verify the lever, never assume it**. (#455; `archive/history.md`.)

- **A test that reads machine state must pin ALL of it, not the one bit it cares about (2026-07-29).** CI cannot catch this class — the runner lacks the optional dependency — so it surfaces when someone installs a tool, the worst moment. Pin the whole set and assert the set's membership, so adding a member fails loudly rather than quietly rebasing what the test means.

- **Repo-local `.horus/` is the source of truth** — committed, vendor-neutral, works without Horus installed. Horus is a helper, never a required runtime.

- **Controls climb a ladder: instruction → deterministic signal → hard gate.** Start with instructions; promote only after an observed field failure (fetch-first + branch→PR instructions failed, so SessionStart signal + block v7 followed). Never enforce preemptively.

- **Card what you won't do now; fix what you will (2026-07-26).** A card's only job is carrying work across a context boundary; fixed this session, it is pure overhead — the commit and PR are the record. Fix it **in its own commit** — that clause is load-bearing, since without it "just fix it" smuggles unrelated changes into whatever PR is open. Card it only when you genuinely are not: it needs an owner decision, is blocked, would derail the task, or is too large. **Size is not the test; surviving the boundary is.** (`archive/history.md`; `session-process-cadence` owns PR granularity.)

- **Process fixes live in the process, never only in agent memory (owner rule, 2026-07-20).** A correction to how work is done lands in a shared artifact — skill text, managed block, PRD Rules, a card — because agent memories are not shared across agents, accounts, or machines. Memory may carry a pointer; it can never be the only home. (Card: `process-fixes-live-in-process-not-memory`.)

- **Server-side continuity never blocks a merge on prose (2026-07-19, #368).** The required PR check verifies field validity + git checkpoint state; a missing canonical PRD/card update is reported, never failed, because the commit is the durable delivery receipt. There is no granularity knob — per-machine, per-project frontmatter, or per-session — that can promote it to a gate. Local PreToolUse parsing is fast feedback only and must match `gh pr merge` at shell command position, never inside quoted prompt prose.

- **Post-merge check filtering fails closed.** A literal SHA stays pinned, and only complete workflow evidence from that exact git object may remove a context proven PR-only; missing, partial, or structurally unparseable evidence leaves required contexts intact even if that means timing out.

- **Never `--delete-branch` a PR that another PR is stacked on (2026-07-27, cost PR #427).** GitHub CLOSES a pull request when its base branch is deleted, and a closed PR's base cannot be retargeted, so the stacked PR is unrecoverable. Stacks also get **no CI at all** while targeting a non-`main` base. Land a stack in one order: retarget the child to `main` and rebase it first, then merge the parent — or merge the parent without `--delete-branch` and clean the ref up after.

- **Continuity must beat re-derivation.** Every capability must give a fresh session something CLAUDE.md + git log cannot, at lower cost. PRD.md is state, not behavior; behavioral text belongs in the managed block, and Rules holds only project-specific invariants earned by failure.

- **Accounts get isolated config dirs; same-dir concurrency is advised, not blocked (#310, 2026-07-18).** Every account gets its own `CLAUDE_CONFIG_DIR`/`CODEX_HOME`, guarding accounts from *each other*. `horus run` advises on a shared dir, naming the live peer, and proceeds. The real cost of sharing is the rate-limit budget, not corruption. If corruption recurs *with isolated dirs*, re-promote to a narrow startup-window guard, never a blanket refusal.

- **Credentials never travel between machines; aliases do (2026-07-20).** Reproduce identity per machine: log in, then `horus account --set <same-alias> --isolate`, and the canonical path follows by construction. Syncing `.credentials.json`/`auth.json` puts live OAuth tokens at rest off-machine, they refresh per-machine anyway, and it cuts against per-account isolation. The only portable non-secret state is `[launch_profiles]`/`[workflow]`/`[tui]` in `config.toml` — a private repo, never a Horus feature.

- **The notify channel is two-way, deterministic and owner-locked (#313–#320, 2026-07-18).** Outbound = `notify.escalate` (best-effort push, inline-keyboard actions). Inbound = `horus notify listen`, long-polling `getUpdates` for the owner `chat_id` only, single-consumer, mapping a BOUNDED grammar 1:1 onto `horus` commands: reads plus bounded mutations (`cancel`/`release`/`supervise`/`warmup`/`answer`). Unknown input yields a help card; argv lists, never a shell; no LLM. It **never mints authority** — no envelope, no `--allow-merge`, no work-plane.

- **`notify listen` runs as a systemd `--user` service, and its kill switch is simply not running it.** `--service` is a persistent unit surviving terminal-close and reboot under linger; a second is refused. `answer <id> <reply|#n>` is special — it writes an input-bridge response, not a subcommand. Conversational free-text stays a future hermes profile in `horus-agent`, never folded in.

- **Remote input bridge is transport-only (#320, 2026-07-18).** `horus ask "<q>" [--option …] [--free-text] [--default A] [--timeout]` writes an on-disk request under `~/.horus/input-requests/` and blocks polling; the single `notify listen` loop pushes it with per-option tap buttons; a tap or typed `answer` writes the response the asker returns (exit 0 answered, 3 timed-out-with-default). It grants NO authority — it delivers the owner's choice/text; the session's own gated logic does anything privileged. Multiple open requests disambiguate by id until per-project topics land.

- **One continuity rule, no granularity setting (2026-07-19, #368/#369).** Git branches, commits, pushed refs, and PRs preserve every delivery between boundaries; canonical PRD/card/session prose is consolidated once at a real boundary — pause, session end, agent/account/machine handoff, release, or a dispatch needing durable context. Delivery safety is independent and never relaxes. Pending delivery truth derives from product commits after the latest canonical-continuity commit, so it survives machines and squash merges.

- **A launch chooses context; the posture chooses authority (2026-07-19, #368).** A launch loads exactly one of: nothing (fresh), the authored handoff (resume), or one card's scope. There is no session-"mode" prose telling a model how much process to perform — that cost a turn at launch, was enforced only by the model's reading of English, and contradicted the handoff it wrapped. What a session may do is the permission posture the agent CLI enforces. Corollary: `next_prompt` is orientation only; never author consent instructions into it, and never let a generator re-add them (#369).

- **Closure reaches the remote, fetch-first and self-reference-free** — at the configured boundary run `close --commit --push`; refuse newer remote continuity, seal the closing SHA without appending it into its own note, and refuse to push residual dirty continuity. Start each session with `git fetch --all --prune` before trusting local refs or prose; `horus sync` is the remedy when behind (ff-only, refuses on a dirty tree, local commits, divergence or a detached HEAD — never implicit, because hooks advise and ask).

- **Committed machine probes are data, never commands.** `.horus/requirements.md` tool probes are executable-name lookups and config probes are path-existence checks; doctor, resume, dashboard, and TUI render the same shared result, while non-probeable access stays prose.

- **One fetch-first primitive, reused.** `fetchcheck.fetch_and_state` (TTL-cached, read-only fetch, never pull) serves SessionStart and `status`/`fleet` gone-branch/staleness signals; no consumer reinvents it.

- **Resume preflight only projects deterministic data.** Its sole sanctioned side effect is the explicit fetch refresh; session liveness is projected without registry reconciliation, usage snapshots carry unmistakable freshness tags, and no output recommends or selects a model/account.

- **Three disciplines, every session:** reproduce the gate via a deterministic signal you observe yourself — a *required* CI check green on the exact commit counts for the test gate; the *runtime* gate always stays yours (drive the real surface once, mocked tests bless nonexistent flags); never accept on a report's claims. Bound work to green committed-and-pushed checkpoints; safety in code, not review.

- **Hook guard invariant:** hooks signal via stdout JSON + exit 0; every committed command carries a per-OS silence guard (`|| exit 0` POSIX/Git Bash; PS 5.1-safe probe for Codex Windows). Never add an exit-code-signaling hook without revisiting this. Anything committed to the repo executes on every machine it reaches — strictest portability bar; the `horus` console script is the only guaranteed spelling.

- **Hooks advise and ask, never override** — injected context defers to the user's command; Stop asks (close now vs push ahead); never strand uncommitted work. Emergency state-save never denies the tool call: worker tree = full-tree commit to the disposable branch (+push); main checkout = a `.horus/**`-only rescue ref via a temp `GIT_INDEX_FILE`, never touching the user's index/HEAD/worktree. Hook sentinels are machine-global under `/tmp`, so probe session ids must be unique across supervisor/worker probes.

- **Publishing a version does NOT update the hosted app** — it runs a pinned install that advances only on an explicit upgrade + restart, so `scripts/deploy-hosted.sh` is the last action of every release and a green publish job alone is insufficient. The full runbook (three-file bump, required checks, tag, PyPI proof, the three OS targets, and the uv/projection traps) lives in the `horus-release` skill. Fleet Projection Sync is read-only; curator launch never mass-writes targets.

- **An outdated CLI must never silently regress `.horus/` structure.** Repos stamp `horus_min_version` (PRD frontmatter); two guards honor it — the managed-block Version-floor preflight (agent checks `horus --version`; the only guard binding an *already-installed* old CLI, so it lives in block text, not code) and `_enforce_version_floor` (running CLI < floor ⇒ exit 4 on every mutating command). Set on scaffold, raise-never-lower via `upgrade-project`; bump `versioning.MIN_CLI_VERSION` only on a real structure break.

- **Dashboard contract:** read-mostly; every form POST is PRG; heavy/network panels load async, never in the page paint; a stale-build server never writes artifacts; empty nudge fragments return empty (no false "all clear"); no first-run splash/overlay (the welcome overlay looped and was removed — render straight to content).

- **Exposure is an explicit launch property, never ambient config.** The `[access]` Cloudflare gate arms ONLY under `horus dashboard --exposed`; local mode never reads `[access]`, so a machine-global block can't 403 a local `horus app`. Fail closed: `--exposed` with no `[access]` block refuses to serve. A hosted backend must pass `--exposed` (its systemd unit does), so treat the harness flag + deploy unit as one lockstep change — flipping the default without the unit would silently un-gate the public dashboard. Persist the client-side seen-flag in `localStorage`, not `sessionStorage`.

- **An account is named `<agent>-<alias>`, and names are resolved, never guessed.** Identity is (agent, alias) — `personal` is a different rate-limit pool per agent — but accounts.toml keys on the bare alias while its isolated dir is `<agent>-<alias>`, so surfaces invite the wrong name. `config.resolve_account` takes what a human writes; unresolvable or ambiguous is REFUSED, naming the real accounts, because a wrong account spends someone else's subscription. Durable artifacts store the canonical label.

- **Usage comes from the surface the app pushes, not one we poll.** Claude Code hands `rate_limits` to every statusline render (official, unauthenticated); `GET /api/oauth/usage` is experimental and 429s under real polling, so `horus usage record` captures the pushed reading into the shared cache. Codex has no equivalent, so its rollout JSONL stays the source — and each lane declares its own `window_minutes`, so never infer a window from its slot. Readings carry a source and an age; a read-out never asserts a cause it did not diagnose.

- **Account setup is login-driven into isolated dirs**, with TOFU identity adoption, the real email never landing in a commit, and forward slashes in every path written to TOML/JSON. A `CLAUDE_CONFIG_DIR` isolates renderer preferences too, including the statusLine pointer (`config.write_statusline_pointer` is the single writer, wired into `isolate_account`); compare account settings when UI behaviour differs rather than cloning ambient config.

- **Prefer login over copy when provisioning an account.** A dir made by fresh login holds only the credential file, while `isolate_account`'s copy drags along config that may carry absolute paths back to the ambient home (Codex `config.toml` does — `codex-isolated-config-leak`) and can even propagate trust decisions.

- **Aliases stay generic** (`personal`/`work`, never a client or employer name): they are non-secret by design and already appear in committed prose, so they must stay safe to publish.

- **Every agent needs its own identity guard.** Claude has `verify_account`, Codex has none, and the shared check reads `config_dirs`, which Codex does not have, so it silently skips (`codex-identity-guard`). An unguarded agent can run under the wrong account while every receipt names the right one.

- **Terminal TUI stays thin and navigable:** render canonical CLI-callable continuity/card primitives, never a second parser/state path; swipe/wheel/arrows scroll the highlighted viewport, and leave the alternate screen before blocking commands. External editors honor VISUAL/EDITOR; prefer a modeless fallback and explain how to return — vi made typing look broken. Preserve conventional SSH mouse/arrow mapping; inversion is opt-in. Account aliases are display labels while ambient launches pass `None` to the native agent adapter.

- **Terminal persistence is prospective and capability-based.** TUI and web-app session requests use a unique Horus-managed tmux session whenever tmux is available on Linux/macOS/WSL — *including when Horus itself runs inside tmux* (2026-07-29): both live on one tmux server, so attaching **switches** this client (`Ctrl-b L` returns) instead of nesting one, and being nested is never a reason to drop persistence. Browser xterm and web-requested native windows attach as viewers; native Windows and no-tmux hosts keep their direct host.

- **A live registry row is attachable only with a Horus tmux `target_ref`** — otherwise label it `original terminal only` and never offer a fake attach or close action. If a requested viewer cannot attach, reap the new tmux session. Keep scripted `horus open --target` behaviour explicit and stable.

- **Git policy:** branch → PR → auto-merge; this repo's main requires pytest checks (admins exempt so continuity pushes land directly; fallback direct merge only on repos without required checks); offboard keeps `.horus/` by default; `.vscode/` is a user surface (static, secret-free, create-only).

- **Escalation is machine-local, best-effort, and never a dependency.** The unattended push channel is a `[notify]` sink in `~/.horus/config.toml` (telegram|hermes|webhook|none, default none), firing only on actionable failures. The token lives machine-local, never in git or `fleet.toml`. `notify.escalate` NEVER raises: a dead sink yields an error result rather than a failed run, and no sink configured means every command behaves exactly as today.

- **Parallel writers are named, never silently last-writer-wins.** `close --check` and `resume` surface concurrent writers on a project — a live co-session (self excluded via `HORUS_RUN_SESSION_ID`/`CLAUDE_CODE_SESSION_ID`), open sibling PRs off the current branch, and merged PRs not yet an ancestor of the latest canonical-continuity commit — as explicit "parallel delivery pending" signals. Advisory only (no locks, no auto-merge of prose); gh absent/offline degrades to silent, never a false all-clear.

- **Tracked workers cannot destructively clean user-global agent state.** The shared host guard blocks common destructive spellings targeting `~/.horus`, `~/.claude`, and `~/.codex` only when `HORUS_RUN_WORKER=1`; every worker probe must instead create an isolated home and clean only the exact directory it allocated. This was promoted after a worker deleted historical machine-local run logs while durable registry/datums/git state survived (2026-07-16).

- **Self-documentation has two truth layers, never curated (2026-07-16).** "What exists now" is answered only by code-derived surfaces (`horus --help` / the argparse walk); `backlog/archive/` cards are the append-only historical index ("was this built, where did it live") — dated, SHA-pinned, verified against code before trusting. No supersede/tombstone metadata on archived cards, ever: curation decays, byproducts of the ship ritual don't. The capabilities project record is a display/fleet projection artifact, not an agent entry point.

- **Capability catalogs stay idempotent EXCEPT the per-project stamp, by design.** The fleet-wide catalog has no timestamps (pure function of sources; unchanged run = no write). `horus capabilities --project <name>` relaxes this ONE way — its `generated_at` refreshes every run (a regenerate-on-read publishing artifact, never a cache) while the `project` payload stays idempotent; don't "fix" the stamp or let the relaxation reach the fleet-wide catalog. The TUI calls `generate_project` once on project-open and renders the returned payload, never reading the file as a cache.

- **Behavioural text lives in the skill that performs the activity, never in `## Rules` (generalized 2026-08-02, #491/#492).** PRD is state; a rule describing *how to do* something belongs where it is loaded at the moment of use. Enforcing it is **deletion-dominant** — most such rules are already stated in their destination skill, so they are duplicated rather than homeless, and one instruction in two wordings costs both. Before adding a rule, ask which skill already owns it. (`archive/history.md`.)

- **An active card gated on a card nobody will deliver is worse than either state (2026-08-02, #493).** `depends-on` only means something while the blocker can move; a `shelved`/`retired` blocker leaves the dependent listed as open work that nothing can ever schedule. `backlog.unreachable_gate_findings` warns on it — as a signal, not a gate, because the class had never had one. The defect entered one level ABOVE the existing shelved-bug guard: the sweep could not box the bug, so it boxed the bug's blocker.

- **Orchestration is owned by the `horus-execution` skill (v8), not PRD Rules.** The parallel orchestrator > supervisor > worker contract (worktree per worker, `full-auto` claude workers, orchestrator-implements-nothing-and-alone-edits-continuity, bounce protocol, manual port-holder reaping) is behavioral text — per "PRD is state, not behavior" it lives in the skill, and the Vision disclaims orchestration. Reaping safety stays in Rules below (positive-confirmation + tmux socket isolation).

- **Orphan reaping only ever acts on positive confirmation (2026-07-13).** `reap_orphans()` kills a Horus tmux session only with a *matching* registry record that is terminal or whose pid is dead, AND unattached, AND idle past a grace window. A session with **no matching record is never touched** — absence of a record is not evidence (a stale/foreign/rebuilt registry looks identical). Extend this to any future reaper before relaxing it.

- **tmux is one server per machine, never `$HOME`-namespaced — isolate it with a private socket in every test/probe that touches real tmux (2026-07-13 incident).** A fake `$HOME` does NOT sandbox tmux (single shared server); a probe's fake registry made `reap_orphans()` kill two real pre-existing sessions. Any tmux-touching test/probe MUST unset inherited `TMUX` and route every call through `tmux -S <explicit-path>`; never `kill-server` (`-L` takes a bare name, not a path, and can mis-resolve).

- **Machine-local registries are additive and forward-readable.** Readers ignore fields they do not understand and known-field updates preserve them; source-version probes isolate HOME/registry so an installed older CLI is not fed a future row schema.

- **Platform traps:** `uv tool install horus-harness` without `--python 3.12` silently resolves an ancient version below the floor (compare `horus --version` with `uv run horus --version`; `--force --refresh --python 3.12`, never `uv tool upgrade --reinstall`). A stale `pip`-installed `horus` on PATH shadows the uv shim (`doctor machine` flags it). Also: ctypes needs argtypes/restype; Windows GUI under `pythonw.exe` + reap the tree; pin CI actions to real tags; probe the HTTP server, not the companion.

## Structure contract (prototype)

- **This file** carries vision, backlog, shipped, rules. Keep it under ~250 lines: shipped items are one line; shipped cards move to `backlog/archive/` with status + PR/SHA intact; bugs get cards as found.
- **`backlog/` (card pilot 2026-07-10, readiness 2026-07-19):** one card per item with lifecycle `status`, orthogonal `readiness: ready|shaping|gated|deferred`, `readiness_reason` on non-Ready cards, and `autonomy: eligible|attended` only on Ready cards; missing/malformed is Unclassified and never autonomously schedulable. `priority` stays orthogonal; optional execution metadata includes `parallel`/`surface`/`vision_facet`/`phase`/`branch`/`depends-on`/`last_refined`. Claim via `horus backlog claim`; after merge, `horus backlog ship <name> --pr N --sha SHA` preserves provenance under `backlog/archive/`.
- **Vision branches (2026-07-17):** an explore direction bigger than one card gets a `vision-branch-*` umbrella card (thesis, exists-vs-gaps map, ordered children, convergence criterion) with children stamped `branch: <umbrella-name>`; the branch is judged — promoted to a facet or dropped — as a unit. Keep the umbrella thin (agents-first, minimal overhead): never mirror child status into it.
- **Convergence (2026-07-16):** a `converge`-phase card (the default) names the `vision_facet` it advances, matched to a `## Vision` table facet; new/next-touched converge cards get one testable acceptance line. `phase: explore` marks a PoC exempt from that gate. `horus consolidate` emits the phase-aware read-out (per-facet coverage + exploratory bucket; warns off-vision/unknown-facet converge cards). The facet set is a living hypothesis — proven exploration is promoted into a new facet, not forced under an old one.
- **`sessions/`** unchanged: one note per session (`horus session new`); distilled notes → `sessions/archive/` (local).
- **Frontmatter:** this file carries `current_focus` / `next_action` / `next_prompt` / `execution_recommendation` / `last_updated` — the tooling reads them PRD-first (`resolve_focus`), so no shims are needed. Describe the next unit and execution posture without pinning a model name; choose the model from live calibration only after delegation earns its cost.
- **Closure:** the ritual and its enforcement are the `## Rules` above (boundary policy, direct-push exemption, fetch-first `close --commit --push`, final-state reporting); a `sessions/` recovery note is added only when durable state cannot resume the work.
