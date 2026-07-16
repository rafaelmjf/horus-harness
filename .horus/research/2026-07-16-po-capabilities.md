# Market scan: Horus product-owner capabilities (roadmap-convergence + market-research) — 2026-07-16

Trigger: new-capability scoping (dogfooding the market-research need on the agent-PO tooling landscape)
Method: two light comparative web sweeps (2 parallel agents, ~24 web calls total). Design input, not a hardened cited report.

---

## Headline findings

1. **The "product owner" reframing is validated by a real ecosystem gap.** The two leading
   open agent-skill collections (obra/superpowers, mattpocock/skills) are both (a) *inward*
   — spec/build/codebase-facing — and (b) either high-ceremony (superpowers) or a full
   opinionated SDLC pipeline (Pocock). **No lightweight, outward, evidence-first
   market-research skill exists in the open ecosystem.** So need #1 isn't reinventing a
   wheel — it's filling a hole.

2. **Your "too deep/complex" read on superpowers/Pocock is confirmed.** superpowers'
   gateway is a meta-governance layer (mandatory pre-response invocation, a 12-row
   "red flags" rationalization table, per-checklist todos); its closest-to-discovery
   skill (`brainstorming`) is a 159-line 9-step workflow that is *purely internal ideation,
   zero market research*. Pocock's catalog (~20+ skills) is individually thin but is a
   whole `/grill → /to-spec → /to-tickets → /implement` pipeline. Neither should be adopted
   wholesale.

3. **The correct vessel is the one we already use.** Anthropic Agent Skills (folder +
   `SKILL.md` + optional `references/`/`scripts/`, three-level progressive disclosure) IS
   Horus's existing skill model. No framework to import — just two more thin skills in the
   existing idiom.

4. **Every serious roadmap tool separates a stable north-star doc from a volatile backlog,
   and derives the backlog FROM it.** Horus already has this (PRD Vision/Rules vs Backlog
   cards). What's missing is the *link*, the *done-line*, and a *convergence read-out* —
   exactly the three cheapest things to add.

---

## Q1 — Roadmap-convergence: what to steal, what to leave

Tools dissected: BMAD-METHOD, claude-task-master, GitHub spec-kit, Amazon Kiro,
Cline Memory Bank, Aider/Windsurf/Roo rules.

**Recurring patterns (the durable ideas):**
- A stable north-star doc sits *above* the backlog; tasks are decompositions of it, never
  free-floating tickets. (spec-kit's `constitution`, BMAD PRD→stories, task-master
  PRD→tasks, Cline `projectbrief`.)
- **Definition of Done = a testable acceptance criterion attached to the item.** Serious
  tools put a pass/fail contract on the work unit — EARS ("WHEN [cond] THE SYSTEM SHALL
  [behavior]", Kiro), INVEST ACs (BMAD), measurable success criteria (spec-kit). Weak
  tools (task-master, Cline) just flip a status — and are visibly weaker for it.
- **A "Ready" entry gate** mirrors Done: spec-kit refuses to start work with unresolved
  `[NEEDS CLARIFICATION]` markers; Kiro requires requirements approval first.
- A deterministic "what's next" from dependencies + priority.
- A living "what works vs what's left" convergence view (Cline `progress.md`).

**Minimal subset for Horus (2 lines/card, 1 line/vision facet, 1 advisory skill):**
- **Give each Vision facet a one-line measurable definition of done** — so "converged" is a
  *stateable condition*, not a vibe. (The lightest possible "constitution.")
- **Per backlog card: one testable acceptance line (EARS-lite: "when X, the tool should Y")
  + a one-line link to which Vision facet it advances.** A card that can't state either is
  parked — that's the "Ready" gate, and it's exactly what stops ad-hoc "added because we
  hit a bug" cards from silently accreting off-vision.
- **Frame Backlog explicitly as "the gap between Vision and Shipped"** — so an empty/closing
  backlog against stated Vision-DoD *is* the definition of converged.
- **A thin skill (`horus-converge`, or fold into `consolidate`):** reads Vision facets +
  their DoD + Shipped, emits per-facet a one-line coverage verdict (converged /
  partial-with-open-cards / uncovered-no-cards), and flags cards with no vision link and
  vision facets with no cards (the reactive-backlog smell). Advisory only.

**Deliberately OMIT:** agent-persona zoos (BMAD), per-feature multi-file spec trees
(spec-kit 6 files, Kiro triad) — the one-PRD invariant is a feature, don't fragment; a JSON
task DB / complexity-scoring LLM passes / MCP (task-master); pre-impl architecture gates &
INVEST checklists (keep DoD at the *instruction* rung per Horus's ladder unless a real
failure earns a gate).

---

## Q2 — Market-research: what to bake in

**Lightweight methods catalog (sweet spot in bold):**
- **JTBD job statement + current alternatives** — "When [situation] I want [motivation] so I
  can [outcome]"; alternatives = the competitive set. (From a skill, frame as *hypothesis to
  validate* — we can't run real interviews.)
- **Competitive teardown grid** — 3-6 rivals × {does well / gap / positioning / price},
  each row evidence-backed by a fetched URL.
- **PR-FAQ vision paragraph** (Amazon working-backwards) — 1-para "the headline is…" + 3-5
  hard FAQ questions. Feeds PRD Vision almost verbatim.
- Problem/solution validation (assumptions log) as the evidence discipline.
- TAM/SAM/SOM — **capped to one sentence** ("big enough / saturated?"), never a spreadsheet.
- Lean Canvas — optional one-pager. Wardley mapping — first thing to omit.

**Minimal subset for Horus — a thin `market-scan` skill (outward twin of `product-audit`)
that COMPOSES the existing `deep-research` harness (do not rebuild search/verify):**
- Bake in exactly the outward trio: **JTBD + competitive teardown + PR-FAQ vision**, plus a
  one-sentence market-size sanity check.
- Output = a dated repo-local receipt mirroring `.horus/audits/` convention, e.g.
  `.horus/research/YYYY-MM-DD-<slug>.md`:

```
# Market scan: <idea/pivot> — <date>
Trigger: new-idea | pivot
Problem / JTBD (hypothesis): "When ___, I want ___, so I can ___"
Current alternatives: [list + links]
Competitive teardown: | Competitor | Does well | Gap | Positioning | Evidence(URL) |
Prior art verdict: green(gap) | yellow | red(saturated)
Vision draft (PR-FAQ, 1 para): ...
Open questions / hard FAQ: [3-5]
Market-size sanity: <one line>
Candidate backlog items: - [ ] <candidate> — rationale, from which gap
Sources: [URLs from deep-research]
```
- **Hand-off:** Vision draft + prior-art verdict distill into PRD Vision via
  `horus-consolidate`; candidate items become candidate cards, each sourced to a specific
  gap/assumption. Advisory only — proposes, never auto-writes Vision or auto-creates cards.
- **Omit:** Wardley, full Lean Canvas (optional appendix), multi-interview JTBD, continuous
  monitoring/scraping (that's the commercial SaaS category — Datagrid/Beam/etc.), any
  superpowers-style mandatory-invocation ceremony.

---

## Net recommendation

Two thin skills + small PRD additions, both in the existing Horus idiom, both advisory,
both landing dated repo-local receipts that feed PRD Vision + Backlog:

| | Inward (exists) | Outward / new |
|---|---|---|
| Discovery | — | **`market-scan`** (composes `deep-research`) → `.horus/research/` |
| Grooming | — | **`horus-converge`** (or fold into consolidate) → convergence read-out |
| Health check | `product-audit`, `process-retrospective` | — |

This completes the PO lifecycle Horus already 70% implements, without importing a framework,
without fragmenting the one-PRD invariant, and while holding the memory/planning-plane
(not execution) boundary.

### Sources
Q1: bmad-code-org/bmad-method · eyaltoledano/claude-task-master · github/spec-kit · kiro.dev/docs/specs · docs.cline.bot memory-bank · aider.chat conventions · docs.windsurf.com rules/memories.
Q2: anthropic.com agent-skills · platform.claude.com skills docs · obra/superpowers (+brainstorming SKILL.md) · mattpocock/skills · workingbackwards.com PR-FAQ · aakashg.com lean-canvas · steveblank.com JTBD · antler.co TAM/SAM/SOM · datagrid.com AI research agents.
