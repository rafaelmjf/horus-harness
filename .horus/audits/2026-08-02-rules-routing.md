# Rules routing audit — where each of the 84 PRD Rules should live

**Date:** 2026-08-02 · **Card:** `prd-rules-section-outgrew-its-budget` · **Status:** proposal, nothing moved

## Why this exists

`## Rules` is 37,519 chars / 84 entries — **51% of the ~73,800-char eager tier** a session
loads before doing anything (CLAUDE.md managed block 13,997 + PRD.md 59,793).

This is not a new policy. PRD Rule 80 already evicted one category on exactly this basis:

> **Orchestration is owned by the `horus-execution` skill (v8), not PRD Rules.** …is
> behavioral text — per "PRD is state, not behavior" it lives in the skill.

That principle was applied once and never again. This audit applies it to the rest.
Anthropic's Claude-5 context-engineering guidance (removed >80% of Claude Code's system
prompt with no measurable loss; warns against "a central repository for every known
practice that you *might* run into") independently validates it, but is not the reason.

## Destinations

| Code | Destination | Rationale |
|---|---|---|
| **A** | stays eager in PRD `## Rules` | non-inferable, cross-cutting, or destructive-if-wrong |
| **A?** | eager, but owner should judge | general engineering lesson the model may already have |
| **B → skill** | the skill that performs the activity | Rule 80's category: behavioral text |
| **C → code** | module docstring / code comment | describes how the code works; read when touched |
| **D → history** | `.horus/archive/history.md` | settled; referent gone |

## The 84

| # | Rule | To | Note |
|---|---|---|---|
| 1 | herdr `agent_status` is inferred | C | `hosts/herdr.py` — a fact about herdr's API |
| 2 | The shelf holds undecided work; a bug never enters it | B → `backlog-refine` | card lifecycle policy |
| 3 | One status list, imported everywhere | A + C | keep the *shape* ("a display aggregating over states it does not distinguish"); specifics → `backlog.py` |
| 4 | Unattended merge is unevidenced; verify-and-escalate | B → `cockpit-autonomous-dispatch-contract` | |
| 5 | Name the off-limits surface in the brief | B → `execution-decision` + `horus-execution` | |
| 6 | SSH here is Tailscale, not `sshd` | **A** | `ss -ltn` finds nothing on a *working* setup — causes false diagnosis |
| 7 | Never make a critical function depend on one session host | **A** | owner design constraint, cross-cutting |
| 8 | A generated file no test compares to its generator is hand-maintained | **A** | cross-cutting, still open on the fleet half |
| 9 | If a command can produce it, prose must not cache it | **A** | core; governs this whole audit |
| 10 | A card's `surface:` list can be incomplete | B → `horus-execution` | |
| 11 | A passing test is not evidence against a network theory | A? | general reasoning trap |
| 12 | Anything PROJECTED is a product surface | **A** | governs skills + managed block |
| 13 | Derive a fixture from the writer that produces it | A? | general test discipline |
| 14 | Ask a context-dependent predicate in its context | A? | general reasoning trap |
| 15 | A skill's DESCRIPTION is where the boundary lives | B → `skill-audit` | |
| 16 | A green PR is not a landed PR | B → `horus-consolidate` | closure-time check |
| 17 | "Released to Ready—eligible" ≠ a software release | D | referent (drill legs) archived |
| 18 | `0.1` is reserved for shareable | **A** | owner rule, non-inferable |
| 19 | A mock that ignores an argument agrees with the code | A? | general test discipline |
| 20 | Test state must never escape the owner's environment | **A** | bit twice; high blast radius |
| 21 | A test reading machine state must pin ALL of it | A? / C | `conftest.py` |
| 22 | Repo-local `.horus/` is source of truth | **A** | core (154 chars) |
| 23 | Controls climb a ladder: instruction → signal → gate | **A** | core design principle |
| 24 | Card what you won't do now; fix what you will | **A** | also in managed block → **dedupe** |
| 25 | Process fixes live in the process, not memory | **A** | also in managed block → **dedupe** |
| 26 | Server-side continuity never blocks a merge on prose | C | `closure.py` design |
| 27 | Post-merge check filtering fails closed | C | |
| 28 | Never `--delete-branch` a PR another PR is stacked on | **A** | unrecoverable if wrong |
| 29 | Continuity must beat re-derivation | **A** | core |
| 30 | Readiness and autonomy are orthogonal | B → `backlog-refine` | |
| 31 | Scoping shapes; refinement makes Ready | B → `scope-cards` + `backlog-refine` | |
| 32 | Accounts get isolated config dirs | **A** | also in managed block → **dedupe** |
| 33 | Credentials never travel between machines; aliases do | **A** | secrets-at-rest |
| 34 | The notify channel is two-way and owner-locked | C | `notify.py` |
| 35 | `notify listen` runs as a systemd `--user` service | C | |
| 36 | Remote input bridge is transport-only | C | |
| 37 | A scheduled supervise needs its session id at schedule time | B → `cockpit-autonomous-dispatch-contract` | |
| 38 | One continuity rule, no granularity setting | **A** | core; overlaps block → **dedupe** |
| 39 | A launch chooses context; the posture chooses authority | **A** | core; overlaps block → **dedupe** |
| 40 | Closure does not go via PR, and is enforced | B → `horus-consolidate` | |
| 41 | Closure reaches the remote, fetch-first | B → `horus-consolidate` | |
| 42 | Acting closure reports the final state only | B → `horus-consolidate` | |
| 43 | Committed machine probes are data, never commands | C | |
| 44 | One fetch-first primitive, reused | C | `fetchcheck.py` |
| 45 | Fleet review names its truth layers | B → `fleet-curation` | |
| 46 | Resume preflight only projects deterministic data | C | |
| 47 | Three disciplines, every session | **A** | heavily duplicated with block → **dedupe** |
| 48 | Hook guard invariant | C | |
| 49 | Hooks advise and ask, never override | **A** | design invariant, cross-cutting |
| 50 | Bundled skill edits bump the skill version | B → `skill-audit` | |
| 51 | Three OS targets | B → release skill *(does not exist yet)* | |
| 52 | Every release: bump, test, publish, deploy-hosted | B → release skill *(does not exist yet)* | this is a runbook |
| 53 | An outdated CLI must never silently regress `.horus/` | **A** | also in managed block → **dedupe** |
| 54 | Dashboard contract | C | `dashboard.py` |
| 55 | Exposure is an explicit launch property | **A** | fail-closed security property |
| 56 | An account is `<agent>-<alias>`, resolved never guessed | **A** | wrong account spends another subscription |
| 57 | Usage comes from the surface the app pushes | C | `statusline.py` / `usage.py` |
| 58 | Unattended scheduling is on-disk systemd timers | B → `cockpit-autonomous-dispatch-contract` | |
| 59 | Account setup is login-driven into isolated dirs | C | `config.py` |
| 60 | Prefer login over copy when provisioning | C | |
| 61 | Aliases stay generic | **A** | publishing safety (184 chars) |
| 62 | Every agent needs its own identity guard | C | open defect, tracked by a card |
| 63 | Agent terminals on phones | D | settled ops finding |
| 64 | Mobile entry stays deliberately simple | D | settled |
| 65 | Terminal TUI stays thin and navigable | C | `terminal_tui.py` |
| 66 | Terminal persistence is prospective and capability-based | C | |
| 67 | A live row is attachable only with a tmux `target_ref` | C | |
| 68 | Git policy: branch → PR → auto-merge | **A** | every session |
| 69 | Delegation raises total cost | B → `delegation-rubric` | |
| 70 | Delegation is need-first, model-second | B → `delegation-rubric` | |
| 71 | Worker accounting captures one end reading | B → `delegation-rubric` | |
| 72 | Unattended dispatch runs under a standing envelope | B → `cockpit-autonomous-dispatch-contract` | |
| 73 | Escalation is machine-local, best-effort | C | `notify.py` |
| 74 | Unattended acceptance reproduces the gate | B → `cockpit-autonomous-dispatch-contract` | |
| 75 | Parallel writers are named | C | |
| 76 | Workers cannot destructively clean global agent state | **A** | destructive; already in code as a guard |
| 77 | Self-documentation has two truth layers | **A** | governs how agents answer "what exists" |
| 78 | Capability catalogs stay idempotent EXCEPT the stamp | C | explicitly a "don't fix this" note for code |
| 79 | Model calibration measures; the agent judges | B → `delegation-rubric` | |
| 80 | Orchestration is owned by `horus-execution`, not Rules | **A** | **generalize into the routing rule this audit implements** |
| 81 | Orphan reaping acts only on positive confirmation | **A** | destructive |
| 82 | tmux is one server per machine | **A** | destructive; bit twice |
| 83 | Machine-local registries are additive | C | |
| 84 | Platform traps (uv `--python 3.12`, pip shadowing) | **A** | install-time, non-inferable |

## Tally

| Destination | Count | Approx chars |
|---|---|---|
| **A** — stays eager | 28 | ~11,000 |
| **A?** — eager but owner-judged (5 of the 28 above) | 5 | ~2,100 |
| **B** — → skill | 22 | ~10,900 |
| **C** — → code | 30 | ~13,000 |
| **D** — → history | 4 | ~1,300 |

If every A? retires: `## Rules` lands at ~23 entries / ~9,000 chars, down from 84 / 37,519 — a
**76% cut**, and the eager tier drops from ~73,800 to ~45,000 chars.

## Judgment calls the owner should make

1. **The five `A?` entries** (11, 13, 14, 19, 21) are general software-engineering
   discipline — mocks that ignore arguments, fixtures not derived from their producer,
   probing a context-dependent predicate from the wrong context. Each was *earned by a
   real failure here*, which argues keep. Each is also the class the guidance says to let
   judgment handle, which argues retire. **I lean keep** — they are cheap, and the failures
   were recent and repeated — but this is exactly the call I said belongs to you.

2. **There is no release skill.** Rules 51 and 52 are a release runbook with nowhere to go,
   and the CLAUDE.md "Releasing horus-harness" section is the same content again. Creating
   one absorbs both and removes a duplication.

3. **Six rules duplicate the managed block** (24, 25, 32, 38, 39, 47, 53). Deduping is
   step 2's job — the block is fleet-wide and PRD is local, so which copy wins is a
   separate decision per rule, not a blanket one.

4. **`C → code` is 30 rules and the least verified part of this audit.** I classified from
   the rule text, not by opening each module. Before moving any of them, confirm the code
   does not already say it.

## What this audit does not claim

No evidence that Opus 5 performs worse here — the registry records no model across 251
sessions and `opus-5` has 0 measured datums. The case rests on Rule 80 being unenforced and
on the 51% measurement, both independent of model generation.
