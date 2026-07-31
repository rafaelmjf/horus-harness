---
status: active
current_focus: "2026-07-31 — session closed with SIX commits unreleased on top of v0.0.79, riding along by owner choice. Two arcs. (1) The bundled-skill audience arc: issue #462 found `product-audit` shipped to all 20 managed projects while its text audited Horus; #463 rescoped it to the host project, #464 fixed an unrelated clock bug found alongside it, #465 carded the fabric-build fallout, and #466 generalised the lesson — `Skill` now declares an `audience` and Horus-only skills stop projecting into consumer repos. (2) A `wildcard` divergence campaign that FAILED twice before working: runs 1-2 produced only skill/process adjustments, the owner named it, and the diagnosis (recency anchoring beat the stated grounding; the branch umbrellas were never engaged) is recorded on the `wildcard` card as its fifth instance of a defect two skill revisions already tried to fix. Run 3, pinned to the umbrellas with skills excluded by construction, produced five branch-level proposals — none of them decided. OLD (2026-07-30): three PRs merged on top of v0.0.79 and deliberately UNRELEASED, riding along until the next cut (owner call). Issue #462 reported that `product-audit` was bundled to all 20 managed projects while its text audited Horus itself; #463 rescopes it to the host project (skill v3->v4, Pin-the-subject step, ladder for projects with no facet table), #464 fixes an unrelated clock bug found alongside it (`releases_since()` cancelled to zero across a minor bump, which would have killed the release half of the staleness advisory permanently at the first 0.1.x), and #465 cards the fabric-build fallout as field evidence on `skill-drift-surfacing-and-refresh`. The bug was found by RUNNING the skill on a real consumer project rather than reading it here — `fabric-build` was on skill v2, improvised around the wrong frame, and left its audit unstamped. The reserved threshold work (`audit-advisory-interval`, drill leg 2) was left untouched on purpose."
next_action: "REVISIT THE FIVE WILDCARD PROPOSALS in `.horus/research/2026-07-31-wildcard-branch-divergence.md` and dispose of them — accept, card, or reject each. They are branch-level moves, none decided, and they are the reason this session closed. Read that file first; it carries the full scope block, risk and honest blocker for each. Ranked: (1) arm and run the away-mode drill — its `Deferred until after 2026-07-29` trigger EXPIRED and nothing re-classified it, and a pass archives the whole X3 umbrella, but the leg roster is one short so the real first step is a leg search; (2) settle the three decisions blocking `x6-continuity-contract-declaration`, which the 2026-07-20 audit says CLOSES the Continuity core facet — best value per effort, one exchange; (3) define `x6-fabric-contract-probe`'s evidence bar while the probe is still live and depositing nothing; (4) measure whether the X4 proxy statusline leak persists, which has a pre-decided revert consequence attached; (5) redraft `x4-pi-harness-via-proxy`. Caveat to weigh first: these were generated on a pathfinder bundle already 10 days and six releases old — the owner declined a refresh, so an inward-evidence refresh (this repo's own audit stamp is v0.0.73) may be the honest precondition for acting on any of them. Nothing is claimed; six commits sit unreleased. Other open work if the proposals are rejected: `refine-autonomy-hardening-lens` (`order: 10`) heads Ready—Attended and needs no owner decision first. The three that do: `stale-worktree-accumulation` (5 dead worktrees here), `herdr-server-shutdown-fragility` (report upstream vs compensate), and the native-terminal runner for honest `vanished` on `local` rows. OWED and explicitly sequenced behind the next release: refresh `fabric-build` via branch -> `upgrade-project --apply` -> PR (product-audit v2 -> v4), then re-run its audit so that run writes its own stamp — do NOT stamp the old receipt retroactively, since the anti-ceremony guard would make a retired-contract receipt the next run's baseline. This repo's own stamp is still v0.0.73 (six releases back) and `optional-host-ci-coverage` remains open."
next_prompt: "Resume horus-harness and `git fetch --all --prune` first. START by reading `.horus/research/2026-07-31-wildcard-branch-divergence.md` — five undisposed branch-level proposals are the open item, and the frontmatter `next_action` summarises them but the file carries the blockers. Two things to know before acting on any of them: they were generated on a pathfinder bundle 10 days and six releases stale (the owner declined refreshing it first), and one proposal turns on a fact worth re-verifying rather than trusting — `autotest-e2e-away-mode-drill` still reads `readiness: deferred` with a trigger date that has passed. Main is clean but NO LONGER equals the last release: v0.0.79 is published, and six commits (#463-#466 plus closures) ride unreleased on top by owner choice. That gap is itself load-bearing context — a bundled-skill fix reaches consumer projects only through a release, so until one cuts, `fabric-build` and ~125 other stale installs still hold the OLD `product-audit`. The durable lesson from this session is the new head rule: a skill bundled into every project is a product surface for THOSE projects, and it was wrong for months without anyone noticing, because nobody read it from a consumer's seat. It was found by running the skill on a real consumer project, not by reading it here — worth repeating for other bundled skills. Two things deliberately NOT done, so do not re-derive them as findings: the `audit-advisory-interval` thresholds stay untouched (reserved as drill leg 2), and fabric-build's old audit stays unstamped on purpose. If you touch the audit clock, note `releases_since()` is exact within a minor line and only a lower bound across one; the docstring says why."
execution_recommendation: "continue-as-is — no delegation was requested; the next step is an owner-gated disposition pass over five proposals, which is judgement work that cannot be delegated, with no context, parallelism, or price dividend exceeding delegation overhead."
last_updated: 2026-07-31
last_product_audit: 0.0.73 2026-07-20
horus_min_version: 0.0.26
---

# Horus — PRD

## Vision

Horus is a lightweight, repo-local **product owner** for official coding-agent CLIs (Claude Code, Codex, more later) — a PO's memory *and* rituals, made repo-local so any native agent session can pick up the role. Continuity is the proven spine. The Vision resolves into named **facets**, each with a definition of done the backlog converges toward (cards carry `vision_facet`):

**Why this exists.** Every fresh agent session started from zero — re-explaining what the project is, what was already decided, and what to do next — while an owner running several projects across multiple provider accounts and machines had no way to see or steer them without opening each terminal. Built for **one solo owner-operator**, deliberately: multi-human collaboration is a standing non-goal, which caps the audience on purpose. Two pivots shaped what it is now: **widened from "continuity layer" to "repo-local product owner"** (2026-07-16, after dogfooded research in `research/2026-07-16-po-capabilities.md`) with continuity staying the core and PO-lifecycle the open frontier; and the **continuity value finding** (2026-07-15) — the proven spine is resume frontmatter + pushed git/PR state + fetch-first, local recovery notes are an optional fallback, and the six-lane taxonomy plus mandatory per-session prose were overhead. Telling deliberate inheritance from legacy, so a reader never has to ask: the retired six-lane files in `.horus/archive/` are kept **on purpose** — this repo is the worked example of its own convergence machinery, not a project that forgot to clean up. The package name **`horus-harness` is legacy, not a claim**: in agent-land a "harness" runs the agent loop (Claude Code and Codex are the harnesses) and this Vision explicitly disclaims orchestration; the name predates that clarity and is tracked by `product-naming`. Sibling repo `horus-agent` is an instruction rung that deliberately never grows Python or a service.

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

**The roadmap breathes — divergence then convergence (2026-07-16):** the facet set and their DoD are a *living hypothesis*, not a frozen contract. A project's real path is research → **divergence** (ideas explored as PoCs, some outside the first vision) → usage → **convergence** (drop, trim, rescope toward a consistent product; directions that prove out are promoted into new facets). Convergence is triggered by usage evidence, not schedule; exploratory work is expected to lack a facet/DoD until it earns one or is dropped. This repo is the worked example (six-lane → consolidated PRD/backlog). Convergence machinery **shipped** (`roadmap-convergence`, archived); the open card is `explore-converge-lifecycle` (the explore phase).

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

**Refinement finding worth carrying (2026-07-28).** Conversion tracks the *kind* of open decision, not whether a card documents one: **30 of 36 Shaping cards already carried an explicit open-decisions section** (17 under the literal heading `## Open decisions for backlog-refine`) and the pass still converted 1 in 13. Editorial and parametric items resolve in one exchange; strategic and architectural ones do not, and should not — `merge-release-owner-gate` is the best-structured card in the repo and correctly went to its own session anyway. So cards now tag each open decision `[refine]` (answerable in a screening exchange) or `[session]` (needs a working session), and a card whose items are all `[session]` leaves the screening pool instead of costing an exchange every pass. `refine_passes:` (int, additive, seeded as a floor — 2 where a prior `last_refined` existed, else 1) makes "screened N times, never moved" deterministic, since `last_refined` overwrites and a no-change pass otherwise leaves no trace. Both land via `refine-autonomy-hardening-lens`.

## Shipped

One line per capability. Details live in git history — every entry carries its PR, tag or
SHA — and `horus backlog list --archived` lists the delivered cards with their provenance.

**Bundled skills declare an audience** (2026-07-31, #466 `7dcedfa`, from #462): `Skill` gains `audience`, so Horus-only skills stop projecting into managed projects; install, staleness, doctor and upgrade all read it together.

**Status line names the spending account** (2026-07-31, #467): row 1 becomes `user@host:cwd │ account │ model`, alias under isolation and the authenticated email outside it.

**wildcard v5 — provenance, not formatting** (2026-07-31, #468): ideas come from facet-DoD-vs-code, owner friction and outside evidence; the backlog is a duplication check only, and every idea must be buildable and self-sufficient.

**The CLI is the authority for shipped state** (2026-07-31, #469): `horus backlog list --archived` opens a read path onto the previously write-only archive; `prd_readiness_count_findings` retired with the prose cache it policed; a per-entry Shipped size signal replaces a line cap that could not see the problem.

**`product-audit` rescoped to the host project, release clock unstuck** (2026-07-30, #463 `e3f0992` + #464 `b18358b` + #465 `477c1a4`, from #462): the skill audits the repo it runs in; `releases_since()` no longer cancels to zero across a minor bump.

**v0.0.79 released, published and deployed** (2026-07-30, tag `v0.0.79`, bump #461 `383eab4`): carries #449 and #452–#460; cut only after a pre-release sweep found the headline feature non-functional.

**Pre-release sweep for 0.0.79 — session restore broken twice over** (2026-07-30, #459 `b15fa1c` + #460 `ee191cd`): Restore was unreachable, and once reachable crashed the cockpit; both fixed and verified live.

**Delegation authorization and its substrate made explicit** (2026-07-30, #437 `240075e`): absent an explicit owner request `execution_recommendation` is `continue-as-is`; `native-subagent` split from `horus-worker`.

**Session restore — reopen a session that vanished** (2026-07-30, #456/#457/#458): launches record the agent's own thread id; the TUI lists vanished sessions and offers Restore, reusing the original registry row.

**Suite-wide isolation of test state from the owner's environment** (2026-07-30, #455): autouse private `HOME`, `TMUX_TMPDIR` and `HERDR_SOCKET_PATH`, after a test stopped the owner's herdr server.

**Mouse-click activation throughout the terminal TUI** (2026-07-30, #453): left-button release selects and activates across list, wide-grid and priority-board layouts.

**v0.0.78 released, deployed and verified** (2026-07-29, tag `v0.0.78`, bump #448): `horus sync`, cockpit remote-freshness, the consolidate cap signal, and the three-host session layer.

**herdr layout — `Horus` and `Agents` spaces, one tab per project** (2026-07-29, #447): the tab strip is the status bar; shell-only tabs are reused so a server restart stops adding duplicates.

**Pre-release host-selection sweep — seven bugs** (2026-07-29, #446): all reachable only once a machine opts into a non-default host; guards now ask about persistence rather than matching a literal host string.

**`horus tui <host>` cockpit front door + persisted session-host default** (2026-07-29, #443): idempotent and never nesting; `hosts.enclosing()` stops a cockpit in one host launching agents into another.

**The herdr session host — three hosts, one protocol** (2026-07-29, #442): ~370 lines and no caller change; declares `liveness=False` and `reports_exit_code=False`, and adds the `state` capability tmux lacks.

**Session-host protocol — `current` · `tmux` · herdr** (2026-07-29, #441): six declared capabilities replace every `"tmux"` string match; registering a host makes it launchable everywhere via `launch_on()`.

**herdr evaluated as a third session host** (2026-07-29, #440): probe answered all four feasibility questions; no attached-flag or activity clock exists, so a herdr host declares no liveness and never reaps.

**`horus tui` works inside tmux — switch the client, don't refuse** (2026-07-29, #439): Horus and its sessions share one server, so the client is moved with `switch-client` instead of nesting a second one.

**Launchable pinned/older models + a vendor-docs refresh skill** (2026-07-29, #438): a managed `[launch_models]` table the launch form reads, plus `launch-model-refresh` researching vendor deprecation docs.

**`consolidate` cap warning names the driving section** (2026-07-29, #436): names the largest section and its share instead of blaming Shipped.

**Cockpit remote-freshness + inbound Sync, and a CI de-rot** (2026-07-29, #434 `c916d70` + #435 `1af2fbf`): per-project freshness on home rows with `g`/`y`/`Y`; Sync = project state IN, Horus Assets Refresh = assets OUT.

**`horus sync` + the wildcard skill retargeted** (2026-07-28, #433 `4c346846`): fast-forwards only when unambiguously safe and otherwise refuses with the reason; wildcard v1→v4 after five live runs and an audit.

**v0.0.77 — the drill-readiness release** (2026-07-27, tag `v0.0.77`, #425/#426/#428/#429/#430/#431, bump #432): sparse `order:` joins `readiness_sort_key`; `--resume` accepts either id form; managed block v14→v16.

**v0.0.75 — the seeded-prompt regression and a bug-clearing campaign** (2026-07-26, tag `v0.0.75`, #403–#414): `claude --remote-control` consumed the positional prompt, silently unseeding every interactive launch; twelve PRs.

**Post-release: Codex usage made trustworthy** (2026-07-26, #415–#418): rate-limit lanes were classified positionally, so every worker datum recorded a weekly percentage as `pct_5h`, corrupting calibration rather than only the display.

**Three autonomous continuity checks** (2026-07-24, #396 `2c28d3b`): canonical cockpit readiness labels and `autonomy_block_reason` in list; the PRD readiness reconciliation shipped here was retired in #469.

**Autonomous backlog librarian** (2026-07-23, #392 `2d7c4be`): one dated advisory receipt after deterministic and bounded semantic hygiene checks; no card or PRD mutations, no delivery authority.

**v0.0.74 — TUI backlog-visualisation arc + Remote Control on launch** (2026-07-21, #386–#389): grouped list, priority board with readiness filter, and a read-only Direction view over a shared `facet_standings`.

**Pathfinder-loop skills recalibrated from the live run** (2026-07-20, #373 `dd28fe8`): product-audit v3 became analysis-only; backlog-refine v2 encodes the owner-designed pass; scope-cards v7; market-scan v7.

**v0.0.73 — session-control axis deleted, closure exemption enforced** (2026-07-19, #368–#371): a launch decides only what context loads, consent moved to the launch permission posture, and `direct_push_violations` makes the closure exemption enforceable.

**Curation pipeline: shaping/refinement split** (2026-07-19, #351–#356 then #364–#367): `scope-cards` owns the dispatchable-card contract; `backlog-refine` alone owns the picture-first interactive flow.

**Autonomous away-mode dispatch, built and validated end-to-end** (2026-07-17→19, #293/#294/#298–#302 then #344–#349): standing envelopes, `horus schedule`, `horus notify`, `horus supervise`; proven by a real full-loop drill.

**Usage + account truthfulness** (2026-07-17, #295–#297): usage reads the `rate_limits` Claude Code pushes to every statusline render instead of polling an endpoint that 429s; account names resolve to exactly one account or refuse.

**Distribution (current v0.0.79):** PyPI trusted publishing; three-OS install smoke; hosted pinned-install deployment; Apache-2.0. **Invariant: publishing a version does NOT update the hosted app — `scripts/deploy-hosted.sh` is the last step of every release.**

## Rules (load-bearing)



- **If a deterministic command can produce it, prose must not cache it (2026-07-31).** PRD.md had grown to ~54k tokens, 82% retrospective, with the Vision at 9%. The `## Backlog` readiness counts were a hand-typed copy of `horus backlog list`, and a *check* (`prd_readiness_count_findings`) existed purely to catch the copy drifting — both were deleted together, since a duplication's guard is cheaper to remove than to maintain. General form: **prose in one artifact has no effect on another artifact's machine-readable state.** (#469/#470; `archive/history.md`.)

- **A card's `surface:` list can be incomplete, and a worker scoped to it will faithfully leave the rest (2026-07-26).** Two were incomplete in one day. `codex-identity-guard` (#404) passed required CI on the exact SHA with an honest worker report and was still a half-fix, because `pty_host.py` held a second copy of the guard the card never named. Every gate an unattended loop possesses would have said yes; a supervisor probing a *different* surface caught it, which is not a reproducible gate.

- **A passing test is not evidence against a network-dependent theory — check the precondition directly (2026-07-26).** The test that reproduced the credentials flake passes when the live call *fails*, so a green run was misread as refuting the correct hypothesis and the real fix (#406) was recorded as "not a verified fix" for days.

- **Anything PROJECTED into every project is a product surface FOR those projects — the managed block too, not just skills (2026-07-31).** Test it from a consumer's seat. Rules in the block must be general; this repo's own incidents belong in `archive/history.md`. Same defect class as the `product-audit` audience bug below, one surface over. (#471.)

- **A skill bundled into every project is a product surface FOR those projects — write it for the host project, not for this repo (2026-07-30).** Audit it from a consumer's seat, generalising on a real one. Two corollaries: **a stale skill is a stale program** (the block rule *behaviour is correct because it lives in code* fails where the text IS the behaviour), and **a bundled-skill fix reaches the fleet only through a RELEASE, not an upgrade** — so `upgrade-project --apply` before a release cut installs the pre-fix version. (#462/#463/#466; card `skill-drift-surfacing-and-refresh`.)

- **Derive a fixture from the writer that really produces it; never hand-write the end state (2026-07-30).** The tell is a fixture whose docstring names a producer it does not call. Build the pre-state, run the producer, then apply overrides on top. 2,400 green tests hid a TUI feature that was unreachable in life, and the test written for that exact defect passed vacuously until the fixture became real. (#460; `archive/history.md`.)

- **Ask a context-dependent predicate in its context before calling it dead (2026-07-30).** A sweep reported herdr's `switch_hint` as unreachable text because `switches_in_place()` measured False — but it returns `inside_herdr()`, so the reading was an artifact of probing from outside herdr, where the existing message is correct. Same shape as `$TMUX`: these predicates answer "am I inside this host *right now*", so a value sampled from the wrong place is not evidence about the code.

- **A skill's DESCRIPTION is where an invocation boundary has to live — the body is read only after the load decision is already made (2026-07-30).** A correct boundary section in the body did not stop the false trigger it was written for. Corollary for tests over skill prose: assert on **whitespace-normalized** content, since hard-wrapping breaks a raw-substring assertion on reflow rather than on meaning. (#437.)

- **A green PR is not a landed PR — check for your own unmerged branches before closing (2026-07-29).** PR #445 carried the only record of the real-Claude-on-herdr trial (including the false-idle finding) and sat open for eight subsequent merges while later continuity cited its evidence; the branch went stale enough that merging it would have reverted work. `horus close --check` lists unmerged remote branches for exactly this — read that line rather than skimming past it.

- **"Released to Ready—eligible" in a `readiness_reason` means the card becomes selectable — it is NOT a software release (misread twice on 2026-07-29).** The two reserved drill legs read "TRIGGER: released to Ready—eligible when the drill is armed…"; cutting v0.0.78 changed nothing for them. When a card's trigger is genuinely a version being published, say "when a version ships" and name it.

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

- **Backlog readiness and autonomy are orthogonal, machine-readable decisions (2026-07-19).** Separate axes from lifecycle `status`, `priority`, and `phase`; the field contract (the enum, `readiness_reason`, `autonomy`) lives in the Structure contract's `backlog/` entry. Missing readiness is Unclassified, never schedulable; only Ready—Eligible may arm under an approved envelope. Tooling: `backlog-readiness-disposition`.

- **Scoping shapes; refinement makes Ready.** `scope-cards` turns an approved direction into high-level Shaping drafts. `backlog-refine` alone owns the picture-first interactive flow and execution-ready contract; pathfinder sequences both, and dispatch consumers reference only the latter.

- **Accounts get isolated config dirs; same-dir concurrency is advised, not blocked (#310, 2026-07-18).** Every account gets its own `CLAUDE_CONFIG_DIR`/`CODEX_HOME`, guarding accounts from *each other*. `horus run` advises on a shared dir, naming the live peer, and proceeds. The real cost of sharing is the rate-limit budget, not corruption. If corruption recurs *with isolated dirs*, re-promote to a narrow startup-window guard, never a blanket refusal.

- **Credentials never travel between machines; aliases do (2026-07-20).** Reproduce identity per machine: log in, then `horus account --set <same-alias> --isolate`, and the canonical path follows by construction. Syncing `.credentials.json`/`auth.json` puts live OAuth tokens at rest off-machine, they refresh per-machine anyway, and it cuts against per-account isolation. The only portable non-secret state is `[launch_profiles]`/`[workflow]`/`[tui]` in `config.toml` — a private repo, never a Horus feature.

- **The notify channel is two-way, deterministic and owner-locked (#313–#320, 2026-07-18).** Outbound = `notify.escalate` (best-effort push, inline-keyboard actions). Inbound = `horus notify listen`, long-polling `getUpdates` for the owner `chat_id` only, single-consumer, mapping a BOUNDED grammar 1:1 onto `horus` commands: reads plus bounded mutations (`cancel`/`release`/`supervise`/`warmup`/`answer`). Unknown input yields a help card; argv lists, never a shell; no LLM. It **never mints authority** — no envelope, no `--allow-merge`, no work-plane.

- **`notify listen` runs as a systemd `--user` service, and its kill switch is simply not running it.** `--service` is a persistent unit surviving terminal-close and reboot under linger; a second is refused. `answer <id> <reply|#n>` is special — it writes an input-bridge response, not a subcommand. Conversational free-text stays a future hermes profile in `horus-agent`, never folded in.

- **Remote input bridge is transport-only (#320, 2026-07-18).** `horus ask "<q>" [--option …] [--free-text] [--default A] [--timeout]` writes an on-disk request under `~/.horus/input-requests/` and blocks polling; the single `notify listen` loop pushes it with per-option tap buttons; a tap or typed `answer` writes the response the asker returns (exit 0 answered, 3 timed-out-with-default). It grants NO authority — it delivers the owner's choice/text; the session's own gated logic does anything privileged. Multiple open requests disambiguate by id until per-project topics land.

- **A scheduled supervise needs its session id at schedule time (2026-07-18).** `horus supervise` resolves only a session-id/prefix or PR — neither exists before launch. So unattended dispatch+supervise is `horus run --unattended --detach` (returns the id now) THEN `horus schedule run … -- supervise <id>`. A PR-ref supervise carries no merge authority (verify+escalate-only). `horus schedule release <id>` re-arms an andon-halted dispatch (refuses cancelled/fired).

- **One continuity rule, no granularity setting (2026-07-19, #368/#369).** Git branches, commits, pushed refs, and PRs preserve every delivery between boundaries; canonical PRD/card/session prose is consolidated once at a real boundary — pause, session end, agent/account/machine handoff, release, or a dispatch needing durable context. Delivery safety is independent and never relaxes. Pending delivery truth derives from product commits after the latest canonical-continuity commit, so it survives machines and squash merges.

- **A launch chooses context; the posture chooses authority (2026-07-19, #368).** A launch loads exactly one of: nothing (fresh), the authored handoff (resume), or one card's scope. There is no session-"mode" prose telling a model how much process to perform — that cost a turn at launch, was enforced only by the model's reading of English, and contradicted the handoff it wrapped. What a session may do is the permission posture the agent CLI enforces. Corollary: `next_prompt` is orientation only; never author consent instructions into it, and never let a generator re-add them (#369).

- **Closure does not go via PR, and that exemption is enforced, not trusted (2026-07-19, #371).** A closure commit is pathspec-bounded to `.horus/`, `AGENTS.md`, `CLAUDE.md` and projected artifacts, so no required check reads it as product. `closure.direct_push_violations` decides that from the actual branch and diff, refusing in `close --push` and at the PreToolUse chokepoint when a direct push carries anything else. Where the generator lives in-repo, projections are build output and travel with their source through a PR. Fails open on non-default branches and undeterminable state.

- **Closure reaches the remote, fetch-first and self-reference-free** — at the configured boundary run `close --commit --push`; refuse newer remote continuity, seal the closing SHA without appending it into its own note, and refuse to push residual dirty continuity. Start each session with `git fetch --all --prune` before trusting local refs or prose; `horus sync` is the remedy when behind (ff-only, refuses on a dirty tree, local commits, divergence or a detached HEAD — never implicit, because hooks advise and ask).

- **Acting closure reports the final state only.** `close --commit [--push]` keeps pre-action dirtiness internal, renders the recomputed complete findings after its mutation, and still fails visibly on residual edits or an unpushed checkpoint.

- **Committed machine probes are data, never commands.** `.horus/requirements.md` tool probes are executable-name lookups and config probes are path-existence checks; doctor, resume, dashboard, and TUI render the same shared result, while non-probeable access stays prose.

- **One fetch-first primitive, reused.** `fetchcheck.fetch_and_state` (TTL-cached, read-only fetch, never pull) serves SessionStart and `status`/`fleet` gone-branch/staleness signals; no consumer reinvents it.

- **Fleet review names its truth layers.** Manifests contain repository identity/lifecycle only; fetched `origin/<default>` PRD/cards are REMOTE SHIPPED TRUTH, checkout/session/dirty state is LOCAL WORKING STATE, and neither is blended or pulled. GitHub fallback is read-only; unavailable/unstructured data is labelled, never guessed.

- **Resume preflight only projects deterministic data.** Its sole sanctioned side effect is the explicit fetch refresh; session liveness is projected without registry reconciliation, usage snapshots carry unmistakable freshness tags, and no output recommends or selects a model/account.

- **Three disciplines, every session:** reproduce the gate via a deterministic signal you observe yourself — a *required* CI check green on the exact commit counts for the test gate; the *runtime* gate always stays yours (drive the real surface once, mocked tests bless nonexistent flags); never accept on a report's claims. Bound work to green committed-and-pushed checkpoints; safety in code, not review.

- **Hook guard invariant:** hooks signal via stdout JSON + exit 0; every committed command carries a per-OS silence guard (`|| exit 0` POSIX/Git Bash; PS 5.1-safe probe for Codex Windows). Never add an exit-code-signaling hook without revisiting this. Anything committed to the repo executes on every machine it reaches — strictest portability bar; the `horus` console script is the only guaranteed spelling.

- **Hooks advise and ask, never override** — injected context defers to the user's command; Stop asks (close now vs push ahead); never strand uncommitted work. Emergency state-save never denies the tool call: worker tree = full-tree commit to the disposable branch (+push); main checkout = a `.horus/**`-only rescue ref via a temp `GIT_INDEX_FILE`, never touching the user's index/HEAD/worktree. Hook sentinels are machine-global under `/tmp`, so probe session ids must be unique across supervisor/worker probes.

- **Bundled skill edits bump the skill version, always.** The version-aware install skips same-version content, so an unbumped text change leaves committed projections silently stale (observed: #247 fleet-curation drift, caught 2026-07-16). Resync with `skill install --force`; never hand-edit the projected `SKILL.md` copies.

- **Three OS targets** (Windows/Linux/macOS); Claude/Codex projections move together and each compares with the CLI, never with its peer. Before release, project from prospective source (`uv run horus`) or repeat after install—the previous installed version can falsely look current. Fleet Projection Sync is read-only; curator launch never mass-writes targets.

- **Every release:** bump `pyproject.toml` + `horus/__init__.py` + `uv.lock`, rerun tests, publish promptly, and prove PyPI JSON/simple-index plus a fresh install on all three OSes. The final release action is `scripts/deploy-hosted.sh`: exact refreshed install, service restart, `/health` version match, and `/` still 403 behind Access. A green publish job alone is insufficient.

- **An outdated CLI must never silently regress `.horus/` structure.** Repos stamp `horus_min_version` (PRD frontmatter); two guards honor it — the managed-block Version-floor preflight (agent checks `horus --version`; the only guard binding an *already-installed* old CLI, so it lives in block text, not code) and `_enforce_version_floor` (running CLI < floor ⇒ exit 4 on every mutating command). Set on scaffold, raise-never-lower via `upgrade-project`; bump `versioning.MIN_CLI_VERSION` only on a real structure break.

- **Dashboard contract:** read-mostly; every form POST is PRG; heavy/network panels load async, never in the page paint; a stale-build server never writes artifacts; empty nudge fragments return empty (no false "all clear"); no first-run splash/overlay (the welcome overlay looped and was removed — render straight to content).

- **Exposure is an explicit launch property, never ambient config.** The `[access]` Cloudflare gate arms ONLY under `horus dashboard --exposed`; local mode never reads `[access]`, so a machine-global block can't 403 a local `horus app`. Fail closed: `--exposed` with no `[access]` block refuses to serve. A hosted backend must pass `--exposed` (its systemd unit does), so treat the harness flag + deploy unit as one lockstep change — flipping the default without the unit would silently un-gate the public dashboard. Persist the client-side seen-flag in `localStorage`, not `sessionStorage`.

- **An account is named `<agent>-<alias>`, and names are resolved, never guessed.** Identity is (agent, alias) — `personal` is a different rate-limit pool per agent — but accounts.toml keys on the bare alias while its isolated dir is `<agent>-<alias>`, so surfaces invite the wrong name. `config.resolve_account` takes what a human writes; unresolvable or ambiguous is REFUSED, naming the real accounts, because a wrong account spends someone else's subscription. Durable artifacts store the canonical label.

- **Usage comes from the surface the app pushes, not one we poll.** Claude Code hands `rate_limits` to every statusline render (official, unauthenticated); `GET /api/oauth/usage` is experimental and 429s under real polling, so `horus usage record` captures the pushed reading into the shared cache. Codex has no equivalent, so its rollout JSONL stays the source — and each lane declares its own `window_minutes`, so never infer a window from its slot. Readings carry a source and an age; a read-out never asserts a cause it did not diagnose.

- **Unattended scheduling is on-disk systemd `--user` timers.** Transient `systemd-run` units die on reboot; on-disk + `enable` + `Persistent=true` survives and catches up a missed slot, and `loginctl` linger is the away-mode precondition. systemd owns the state; `horus schedule` re-implements no part of `horus run`. **`ExecStart` must be an ABSOLUTE path** — systemd resolves a bare name against its own compiled-in PATH, not the unit's `Environment=PATH` (`203/EXEC`, #322). "Has a one-shot fired?" reads `NextElapse` plus the Persistent stamp mtime. Restart the pinned listener after an upgrade.

- **Account setup is login-driven into isolated dirs**, with TOFU identity adoption, the real email never landing in a commit, and forward slashes in every path written to TOML/JSON. A `CLAUDE_CONFIG_DIR` isolates renderer preferences too, including the statusLine pointer (`config.write_statusline_pointer` is the single writer, wired into `isolate_account`); compare account settings when UI behaviour differs rather than cloning ambient config.

- **Prefer login over copy when provisioning an account.** A dir made by fresh login holds only the credential file, while `isolate_account`'s copy drags along config that may carry absolute paths back to the ambient home (Codex `config.toml` does — `codex-isolated-config-leak`) and can even propagate trust decisions.

- **Aliases stay generic** (`personal`/`work`, never a client or employer name): they are non-secret by design and already appear in committed prose, so they must stay safe to publish.

- **Every agent needs its own identity guard.** Claude has `verify_account`, Codex has none, and the shared check reads `config_dirs`, which Codex does not have, so it silently skips (`codex-identity-guard`). An unguarded agent can run under the wrong account while every receipt names the right one.

- **Agent terminals on phones:** keep the browser terminal functional, but use native iOS Termius SSH over the private Tailscale network into `horus tui` as the reliable Claude/Codex control path; managed tmux makes app- and TUI-launched sessions attachable from either surface. `claude-work-phone` selects the isolated work account. Treat Claude in the 39-column browser/xterm viewer as best-effort; do not resume narrow-grid patching without new upstream renderer evidence.

- **Mobile entry stays deliberately simple:** Termius → connect → `horus tui`. No shortcut/forced-command machinery; revisit only if Termius adds a free one-tap saved-host/startup action or real usage changes the tradeoff.

- **Terminal TUI stays thin and navigable:** render canonical CLI-callable continuity/card primitives, never a second parser/state path; swipe/wheel/arrows scroll the highlighted viewport, and leave the alternate screen before blocking commands. External editors honor VISUAL/EDITOR; prefer a modeless fallback and explain how to return — vi made typing look broken. Preserve conventional SSH mouse/arrow mapping; inversion is opt-in. Account aliases are display labels while ambient launches pass `None` to the native agent adapter.

- **Terminal persistence is prospective and capability-based.** TUI and web-app session requests use a unique Horus-managed tmux session whenever tmux is available on Linux/macOS/WSL — *including when Horus itself runs inside tmux* (2026-07-29): both live on one tmux server, so attaching **switches** this client (`Ctrl-b L` returns) instead of nesting one, and being nested is never a reason to drop persistence. Browser xterm and web-requested native windows attach as viewers; native Windows and no-tmux hosts keep their direct host.

- **A live registry row is attachable only with a Horus tmux `target_ref`** — otherwise label it `original terminal only` and never offer a fake attach or close action. If a requested viewer cannot attach, reap the new tmux session. Keep scripted `horus open --target` behaviour explicit and stable.

- **Git policy:** branch → PR → auto-merge; this repo's main requires pytest checks (admins exempt so continuity pushes land directly; fallback direct merge only on repos without required checks); offboard keeps `.horus/` by default; `.vscode/` is a user surface (static, secret-free, create-only).

- **Delegation raises total cost; it is a time/capacity/parallelism lever, never a cost saver (measured 2026-07-17, `research/2026-07-17-delegation-cost-finding.md`).** A cheaper worker does not mean cheaper work: a fresh worker re-pays cold-start context every card while inline amortizes one compounding context, verification runs twice, and one account captures no parallelism. Dispatch only when a real dividend beats the markup — time-shift, capacity arbitrage, or true parallelism on distinct accounts.

- **Delegation is need-first, model-second.** Name a concrete context/parallelism/price dividend exceeding the fixed supervisor tax before selecting a worker; cross-project scope, phase count and calibration goals do not qualify alone, though owner-directed capacity spend may. Every launch first names the exact agent, concrete model (the CLI's executable selector, not the calibration key), effort, account, usage/reset evidence, bounded task, attempt allowance and gate — and gets approval. Any fallback re-asks.

- **Worker accounting captures one end reading, and never estimates.** Show a delta only for fresh same-window isolated readings without tracked overlap; otherwise label it unknown or confounded. Never estimate task usage, auto-route from cost, poll, or add a model call for accounting. Workflow tests require a real distinct worker, and Codex auto-edit workers get a read-only `.git` and no socket bind — the supervisor owns commit, push and every runtime gate.

- **Unattended dispatch runs under a standing envelope, or it does not run.** Authority is either the owner approving that exact launch or a bounded **expiring** envelope (`horus envelope create`) the launch validates against. An envelope *bounds* — cards/branch, accounts, tiers, effort, usage floor, attempts, dispatches/day, expiry, merge authority (default verify+escalate-only) — and never selects card, account or model. Widening means a new envelope; only `revoke` mutates. Binds at `horus run`, read at fire time. Unknown capacity refuses. Machine-local, never committed.

- **Escalation is machine-local, best-effort, and never a dependency.** The unattended push channel is a `[notify]` sink in `~/.horus/config.toml` (telegram|hermes|webhook|none, default none), firing only on actionable failures. The token lives machine-local, never in git or `fleet.toml`. `notify.escalate` NEVER raises: a dead sink yields an error result rather than a failed run, and no sink configured means every command behaves exactly as today.

- **Unattended acceptance reproduces the gate; merge is opt-in and probe-gated.** `horus supervise` accepts only on evidence it observes — required CI green on the EXACT head SHA plus freshness — never the worker's self-report. It MERGES only when the envelope granted `merge_authority` AND an owner-authored `--probe` passes; merge-authorized-without-a-probe refuses. Default is verify+escalate-only. An escalation is an **andon**: it disarms every scheduled dispatch whose card transitively `depends-on` the failed one.

- **Parallel writers are named, never silently last-writer-wins.** `close --check` and `resume` surface concurrent writers on a project — a live co-session (self excluded via `HORUS_RUN_SESSION_ID`/`CLAUDE_CODE_SESSION_ID`), open sibling PRs off the current branch, and merged PRs not yet an ancestor of the latest canonical-continuity commit — as explicit "parallel delivery pending" signals. Advisory only (no locks, no auto-merge of prose); gh absent/offline degrades to silent, never a false all-clear.

- **Tracked workers cannot destructively clean user-global agent state.** The shared host guard blocks common destructive spellings targeting `~/.horus`, `~/.claude`, and `~/.codex` only when `HORUS_RUN_WORKER=1`; every worker probe must instead create an isolated home and clean only the exact directory it allocated. This was promoted after a worker deleted historical machine-local run logs while durable registry/datums/git state survived (2026-07-16).

- **Self-documentation has two truth layers, never curated (2026-07-16).** "What exists now" is answered only by code-derived surfaces (`horus --help` / the argparse walk); `backlog/archive/` cards are the append-only historical index ("was this built, where did it live") — dated, SHA-pinned, verified against code before trusting. No supersede/tombstone metadata on archived cards, ever: curation decays, byproducts of the ship ritual don't. The capabilities project record is a display/fleet projection artifact, not an agent entry point.

- **Capability catalogs stay idempotent EXCEPT the per-project stamp, by design.** The fleet-wide catalog has no timestamps (pure function of sources; unchanged run = no write). `horus capabilities --project <name>` relaxes this ONE way — its `generated_at` refreshes every run (a regenerate-on-read publishing artifact, never a cache) while the `project` payload stays idempotent; don't "fix" the stamp or let the relaxation reach the fleet-wide catalog. The TUI calls `generate_project` once on project-open and renders the returned payload, never reading the file as a cache.

- **Model calibration measures; the agent judges.** Measured datums and hand-edited owner priors stay separate; `horus/datums.py` is never a router/policy/spend engine. Outcomes are agent-supplied: clean/nudged/bounced form quality, died/void are separate operational counts, and exit is an orthogonal mechanical axis. Every consumer emits data only—no pick, `--for`, or auto-dispatch—and aliases normalize before joins.

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
