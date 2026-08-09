---
status: open
topic: remote-project-visibility
priority: medium
readiness: ready
autonomy: attended
created: 2026-08-09
created_by: owner
last_refined: 2026-08-09
refine_passes: 0
vision_facet: "Dashboard / cockpit"
tier: small
type: research
parallel: safe
phase: explore
surface: "research only — no code; receipt under .horus/research/"
---

# backstage-catalog-prior-art-scan — study the mature version before building the catalogue site

## Why (2026-08-09)

The owner is reworking the **Dashboard / cockpit** facet. The landing idea is a deployed
site that mixes PM/issue-tracking visibility with self-documenting capability docs. The
original build deliberately skipped exploring prior art — the focus then was a minimal
version that made sense for agents.

Two findings from the same session make a scan cheap and timely:

- The **OpenWiki/Graphify benchmark** produced a drop verdict for both tools as agent
  context (see `openwiki-graphify-value-benchmark`). The owner then checked the published
  OpenWiki site and rejected its *form* — closing question 2 as well. So the idea survives
  and both implementations of it did not.
- Evaluation is now cheap here: two tools, six runs, a clean verdict inside a day, with the
  condition-branch setup reusable.

**Backstage** (Spotify's developer portal) is the mature product for exactly this shape: a
software catalog carrying component metadata and status, plus TechDocs generated from the
repo. Studying it is high-information regardless of whether any of it is adopted.

## Scope — SHALLOW by default

One bounded pass, evidence-first, top public sources. Explicitly NOT a deep evaluation and
NOT an adoption decision. Deepening is a separate owner call, not an assumption.

Answer only:

1. **Catalog model** — what fields does Backstage's software catalog actually carry, and
   which of them earn their place for a 7-project single-operator fleet? This is the
   transferable part: it tells us which fields a Horus catalogue view needs.
2. **TechDocs** — is its doc generation *derived* or *authored*? Derived matches the
   verdict from the benchmark; generated prose does not.
3. **Cost shape** — license vs inference. The benchmark's sharpest maintenance finding was
   that a free MIT tool (OpenWiki, LangChain) carries a recurring model-quota cost per
   refresh, while a free unlicensed tool (Graphify) costs ~nothing. Record both axes.
4. **Weight** — how much machinery is required to stand up the smallest useful instance,
   measured against the Vision's explicit non-goal: *"Deliberately NOT the
   superpowers/spec-kit framework depth."*
5. **Anything else current in the category** the owner has not seen. My knowledge cutoff
   predates both OpenWiki and Graphify, so the live web is the authority here, not the
   model.

## Non-goals

- No PM-tool scan. That question is already structurally answered: every PM tool is a
  database with an API, the backlog is files in git, and the Vision makes those files
  *"the only contract — vendor-neutral; Horus is a helper, never a required runtime."*
  Adopting means either a two-source-of-truth sync engine (a drift generator — see the
  stale published wiki and `codex-isolated-config-leak`) or agents needing API credentials
  on every machine forever. GitHub Issues/Projects is the only candidate worth revisiting
  if that ever changes, since `gh` is already a dependency and the dashboard already reads
  GitHub via `github_catalog`.
- No standing up a Backstage instance.
- No Vision edits and no card creation from the findings — those are convergence decisions.

## Acceptance

- A dated receipt under `.horus/research/` answering the five questions with fetched
  evidence, each claim carrying its source.
- An explicit recommendation on the only real question: **which catalog fields to borrow**,
  and whether anything in the category is worth adopting rather than rendering ourselves.
- One line stating whether a deeper pass is warranted, and why — never assumed.

## Related

- `openwiki-graphify-value-benchmark` — the drop verdict that motivates this, and the
  source of the derived-vs-generated principle.
- The **authoring rule** the owner set on 2026-08-09: one catalogue, identical for owner
  and outsider, self-explanatory to a reader with zero project context. That constrains
  `## Shipped` authoring (enforced at `horus-consolidate`), not the renderer — a derived
  catalogue can never be clearer than its source. Any borrowed field must survive it.
- The catalogue's own defects, found the same day and independent of this scan:
  `horus capabilities` clips entries at a line boundary in projects whose PRD hard-wraps
  (all 11 `horus-agent` entries and 5 of 6 `horus-hub` entries cut mid-clause, while
  `horus-harness` entries run to 1,323 chars intact), and fleet mode omits `vision`
  (empty for 7 of 7) plus `generated_at`/`horus_version`, which project mode populates.

## Source

Owner brainstorm, 2026-08-09, after the benchmark verdict and a review of the published
OpenWiki site.
