---
name: horus-kickstart
description: >-
  Owner-invoked, guided ONE-PASS re-baseline of a project's direction — one
  divergence→convergence loop that also doubles as the assisted onboarding path
  onto the convergence model. Use when the owner says "kickstart", "re-baseline",
  "where should this project go next", "reset the roadmap", or "onboard this
  project onto facets". A thin orchestrator that SEQUENCES existing skills
  (`market-scan` → `deep-research` → the `horus consolidate` convergence
  read-out) and pauses for owner approval at every gate: introspect the repo/PRD,
  scan the market (respecting the shipped ledger), then PROPOSE a Vision facet
  DIFF (add/rename/retire/promote — never a wholesale replacement), exploratory
  backlog cards, and an execution order. Advisory / diff-only: it never
  auto-writes the Vision, auto-creates cards, or reorders the backlog — every
  step hands the owner a proposal to accept. Onboarding folds in: on a project
  with no `## Vision` facet table it proposes the initial facets and offers to
  stamp existing cards. Confirm a token envelope before any web work. Not a
  monolithic auto-runner; not continuous monitoring.
---

<!-- horus-skill-version: 1 -->

# horus-kickstart — one guided divergence→convergence re-baseline

You are running the project's **breathing loop** once, on demand: research →
**divergence** (new directions, proposed as a facet diff) → the owner decides →
fresh backlog → later **convergence** (the `horus consolidate` read-out trims the
fat). This is the assisted twin of hand-authoring facets and stamping cards, and
it IS the onboarding path onto the convergence model — a project that has Horus
but not the facet machinery runs this once to adopt it.

You are a **thin orchestrator**. You do not reinvent research, facet mapping, or
card lifecycle — you sequence skills and CLI signals that already exist and add
**judgment** on top:

- **Deterministic signals come from the CLI / existing skills** — `horus
  consolidate` already emits the phase-aware convergence read-out (which facet
  each card maps to, which facets have open work, the exploratory bucket, the
  off-vision warnings); `market-scan` already produces the outward evidence
  receipt; `deep-research` already does fetch+verify. Read those; never fork them.
- **You supply the judgment the CLI cannot** — the facet DIFF (what to add,
  rename, retire, or promote), which directions are worth exploring, and a
  suggested execution order. That is the "lean CLI for signals, agent for
  judgment" split this repo holds to.

## Hard boundary — advisory / diff-only, gated at every step

- **Never auto-apply.** You propose diffs to the Vision and the backlog; the owner
  disposes. Vision and backlog are the load-bearing artifacts and git is the
  reversal path — you only hand over a proposal.
- **Pause for owner approval at every gate.** Each numbered step below ends with
  the owner deciding before you proceed. Do not chain steps unattended.
- **Facet DIFF, never wholesale replace.** Reconcile every proposal against the
  EXISTING facet set so a re-run does not thrash continuity. Frame each change as
  add / rename / retire / promote-proven-exploration against a named current
  facet — not a fresh table.

## Before you spend — confirm the token envelope

Step 2 fans out web research (it composes `market-scan`, which composes
`deep-research`). Before any web work, state: the trigger (re-baseline |
onboarding), the project in one line, the directions you already suspect, and the
research depth — then get the owner's confirmation. Match depth to the question; a
light comparative sweep usually beats a full adversarial report for a direction
call. If the owner only wants the introspection + convergence pass (steps 1, 3–6),
skip the market scan and say so.

## The flow (each step PROPOSES; the owner decides at every gate)

1. **Introspect (no spend).** Read the repo and `.horus/`: the current `## Vision`
   and its facet table (or note its ABSENCE — that flags the onboarding path), the
   active backlog cards and their `vision_facet`/`phase` stamps, and the `##
   Shipped` ledger. Run `horus consolidate` to get the deterministic convergence
   read-out — this is your ground truth for where each existing card maps and which
   facets already have open work. Summarize "where we are now" and STOP for the
   owner to confirm the picture before spending.

2. **Market-scan (outward, gated by the envelope above).** Invoke the `market-scan`
   skill for "where is the world now", passing the introspection summary so it
   RESPECTS the shipped ledger and never re-proposes delivered work. Its dated
   `.horus/research/` receipt (prior-art verdict + Vision draft + candidate items)
   is the outward evidence you build the diff on. STOP for the owner to react to
   the receipt.

3. **Propose the Vision facet DIFF.** Against the existing facet set, propose a
   handful of directions as a diff — **add** a new facet (with a draft
   definition-of-done), **rename**/rescope an existing one, **retire** a converged
   or abandoned one, or **promote** a proven `phase: explore` direction into a new
   facet. Never a wholesale table rewrite. Cite the introspection + market-scan
   evidence behind each change. **Onboarding fork:** if step 1 found NO facet
   table, this step instead proposes the *initial* facet set (from repo + research)
   and offers to stamp existing cards with a `vision_facet` — that offer IS the
   assisted onboarding, no separate migration. STOP for owner approval of the diff.

4. **Propose exploratory backlog cards.** One card per approved direction, the
   divergent ones as `phase: explore` (exempt from the facet/DoD gate until they
   earn or are dropped). Source each to a specific gap/assumption from the diff or
   the market-scan receipt. Propose — do not create; the owner accepts, then you
   (or they) write the cards. STOP for owner approval.

5. **Propose an execution order.** A suggested sequence over the approved cards,
   ordered by dependencies and owner priorities. This is judgment, not a CLI
   output — present it as a recommendation the owner reorders. STOP.

6. **Hand off.** The owner now has an approved facet diff, a set of accepted cards,
   and a suggested order — a fresh backlog to start or continue. Apply ONLY what
   the owner approved: fold the accepted facet changes into `## Vision` and the
   accepted cards into the backlog via the normal path (`horus-consolidate` distills
   the Vision; `horus backlog` / a new card file per accepted item). If the owner
   deferred a step, leave it unapplied and say so.

7. **Later: converge (separate session, not part of this pass).** When usage
   evidence accumulates, run the `horus consolidate` convergence read-out to trim
   the fat and continue — re-run kickstart only when a real re-baseline is needed
   again. Convergence is triggered by usage, not schedule.

## Deliberately omit

- No new CLI subcommand, module, roles, or multi-file ceremony — the deterministic
  signals this needs (`horus consolidate` read-out, `market-scan` receipt) already
  exist; kickstart is pure orchestration + judgment over them.
- No auto-run of all steps unattended; no wholesale Vision replacement; no
  continuous monitoring (that always-on category is out of scope).
- No token estimate for the research spend beyond stating the depth and getting
  confirmation — let `market-scan`/`deep-research` own the actual fan-out.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — run the same flow. Introspect `project.md`/`roadmap.md`
instead of the PRD Vision/backlog; there is no facet table, so the "diff" is a
proposed set of direction changes against `project.md`'s stated vision, and cards
become `roadmap.md` items. Feed the market-scan Vision draft into `project.md` and
accepted directions into `roadmap.md` at the owner's discretion, following that
project's six-lane closure rules. The advisory / diff-only, gate-at-every-step
boundary is unchanged.
