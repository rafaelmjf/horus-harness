---
status: open
priority: low
created: 2026-07-19
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Shaped 2026-07-20 (boundary inventory + three child drafts); children need backlog-refine before any is Ready."
phase: explore
tier: high
type: research
parallel: safe
created_by: owner
surface: .horus/research/, Horus workflow skills, possible future workflow-profile selection surface
---

# vision-branch-x6 — workflow selection compatibility

## Why — the two Horus layers may be separable

The owner currently sees Horus differentiating along two related but distinct axes.

### 1. Cross-harness utility platform

Horus does not replace Claude Code, Codex, or another native harness. It helps the
owner work with them: multiple isolated accounts, desktop and phone access through the
same terminal-oriented workflow, resume/fresh launch choices, scheduling, a local but
hostable web app, skill visibility, and harness-specific utilities such as Claude
token-maximizing behavior. These capabilities emerge from concrete personal gaps — the
tool the owner repeatedly wishes already existed — and can support competing native
tools rather than asking the owner to move into a Horus execution environment.

Mobile support is not a novel remote-computing primitive by itself; today much of the
value comes from SSH through a terminal app. The useful product property is that the
same account, session, scheduler, continuity, and fleet surfaces remain usable in that
setting.

### 2. Opinionated product-development workflow

Horus began with continuity and is growing a product-development workflow around it:
market-scan, pathfinder, roadmap branches, scoping, backlog refinement, convergence,
and audit skills. That workflow is already useful to the owner and emerged from real
development needs, but it remains experimental and is being dogfooded mainly while
building Horus itself.

This layer has a higher burden of proof. It competes not only with new AI tooling but
with established product-development practice and recognized opinionated agent
workflows. It must earn its ceremony and prove that agents and the owner make better
decisions with it.

## Compatibility hypothesis

Explore whether the utility platform can remain stable while the opinionated workflow
layer is replaceable or composable. Superpowers and other recognized workflows found in
the earlier research are examples to revisit, not preselected integrations. Horus has
changed substantially since that scan, so any later comparison must re-evaluate the
current products rather than inherit the earlier verdict.

If the layers are separable, a future project or session might select `horus`,
`superpowers`, or another compatible workflow while keeping Horus's account, session,
scheduler, fleet, continuity, and hosting utilities. A selector is only one possible
outcome; selective borrowing, coexistence without a selector, keeping the Horus
workflow exclusively, or dropping this branch are equally valid verdicts.

## Convergence criterion

Establish an evidence-backed boundary between Horus's utility substrate and its
workflow policy, then choose one disposition:

1. keep the Horus workflow as the only supported path;
2. adopt selected external practices without workflow switching;
3. support compatible workflow profiles or a selector; or
4. drop the compatibility direction because the layers cannot be separated cleanly or
   the added complexity does not earn its keep.

The branch converges only after current alternatives are re-examined and at least one
real Horus project exercises the chosen compatibility hypothesis.

## Exists vs gaps (shaped 2026-07-20)

The scope-cards pass ran the inward analysis inline; findings in
`.horus/research/2026-07-20-x6-boundary-inventory.md`. **Exists:** a
workflow-agnostic substrate (no imports from backlog/continuity/closure;
`launch.py` takes a bare prompt string); a small machine-read continuity
contract already funneled through named chokepoints (`resolve_focus`, the
`backlog` parser, `closure`), splitting into a session tier and a dispatch
tier; `supervise`'s card-stamping as the one deliberate substrate→workflow
coupling; and a live tier-1 exemplar (fabric runs production on frontmatter
alone, no cards). **Gaps:** the contract is implicit, not declared; the
outward alternatives evidence is stale (2026-07-16, explicitly not
inheritable); probe evidence from real non-SWE use is only starting; the
workflow-swap question (can a foreign bundle's artifacts coexist with the
contract?) is untested.

## Proposed children, in order

1. `x6-continuity-contract-declaration` — name the contract and its two tiers.
2. `x6-workflow-alternatives-refresh` — shallow outward re-scan, judged on
   contract compatibility; gated on a separate attended owner review before
   any web work.
3. `x6-fabric-contract-probe` — live now (refresh delivered 2026-07-20);
   observational contract-sufficiency evidence from production BI use.
4. *Later draft, not pre-invented:* a workflow-swap experiment (install a
   foreign bundle in a disposable repo or pbi-ecosystem, test artifact
   conflict/coexistence) — shaped only after 2's findings exist.

The framing the children inherit: Horus's workflow is an outer loop
(direction/resume/dispatch), superpowers-class bundles are inner loops (SWE
execution practice); conflict lives only in the shared plan/spec/backlog
artifact zone. Pathfinder-class rituals are confirmed optional policy, not
core.

## Non-goals for this raw branch

- No market scan or competitor teardown yet.
- No installation or execution of a third-party workflow.
- No workflow selector, profile schema, TUI control, or compatibility adapter yet.
- No assumption that Horus's workflow is inferior, superior, or technically separable
  beyond what the boundary inventory evidenced.
- ~~No child cards until the corrected scoping flow is invoked and the owner approves
  its proposals.~~ Done 2026-07-20; the three children above are owner-approved drafts.
