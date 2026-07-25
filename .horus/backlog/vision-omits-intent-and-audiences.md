---
status: open
priority: high
readiness: ready
autonomy: eligible
readiness_reason: "Root-caused from a live field failure on 2026-07-25 with the exact replacement text drafted, and the fix is prose in two known files plus their projections. The proof that the elements are the right ones is that the failed session's own deliverable converged on all of them."
created: 2026-07-25
created_by: claude
vision_facet: "Continuity core"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus/templates.py:35 + :264 (managed block + PRD template Vision), horus/skills.py:516 + :1127 (horus-infer), tests/test_templates.py, tests/test_skills.py, projected .claude/.agents skill copies"
---

# vision-omits-intent-and-audiences — the Vision contract captures the destination, never the intent

## Why — live field failure, 2026-07-25, `fabric-build`

An Opus 5 session was handed a well-authored resume prompt commissioning a full
structure-and-purpose review. The handoff was fine; the PRD was fresh. The session
still spent most of its length reaching **wrong** conclusions, and only the owner's
three interventions corrected them:

- recommended **retiring** ~193 inherited medallion files that are in fact a
  deliberate product offering and the preset path's acceptance fixture;
- identified `deploy/wizard.py` — an interactive **human** command — as the agent
  contract, instead of the `plan --profile` → `apply` path built for exactly that;
- proposed new CLI verbs (`workspace create`, `run`) that were pure passthroughs
  over `fab mkdir` / `fab job run`.

The owner's diagnosis is the useful part: *"sessions that run in the
fabric-metadata repository never get this wrong."*

## Why the parent repo is immune and the fork is not

In `fabric-metadata-driven-medallion` the **product is the framework** and
`deploy/` is tooling. A session there asks "how do I change the framework"; the
wizard is self-evidently a deployment convenience, and its audience never needs
stating.

In `fabric-build` the **product IS the command surface**. A session asks "which
contract should an agent drive?" and finds four candidates — `plan`/`apply`,
`wizard.py`, `setup_framework.ipynb`, `deploy/README.md` — with nothing ranking
them. The files travelled at the split; the audience model did not, **because in
the parent it had never needed writing down**. Moving the same files into a repo
where the interface is the product created a question that had never existed
there, so the answer had never been recorded.

## The defect in Horus

Every place Horus specifies a Vision asks for the same triplet:

```text
horus/templates.py:35    "Vision — what this project is, its shape, its boundaries."
horus/templates.py:264   "What this project is, its shape, and its boundaries."
horus/skills.py:516      "what the project is, its shape, and explicit out-of-scope"
horus/skills.py:1127     "Vision: shape and explicit boundaries"
```

Three present-tense descriptions of the **destination**. None asks for **why the
project exists**, **what it deliberately inherited**, or **who each surface
serves**.

`fabric-build`'s Vision was a textbook-correct instance of that template — what it
is, its shape, an explicit out-of-scope list — and it still misled the reader,
because filling the template faithfully produced actively wrong signals:
*"Medallion is one possible preset or adapter, **not a built-in lifecycle**"* and
*"this repository **can replace inherited code freely**"*. Read as written,
retirement is the obvious recommendation.

`horus-infer` makes it systematic on forks: it distils "the project's own
canonical docs" into the Vision, but in a fork those docs describe the **parent's**
product. Why the fork happened and what it kept on purpose is definitionally
absent from every inherited document — it exists only with the owner, and nothing
asks them for it.

## Scope — two elements added to the Vision contract, in all four places

> **Why this exists.** The originating problem, who it was built for, and — if the
> project was forked, split, or pivoted — what it inherited **on purpose** and what
> that inheritance is for. A reader must be able to tell deliberate inheritance
> from legacy without asking.

> **Surfaces and audiences.** Once a project has more than one entry point, name
> each and say who it serves (human operator, agent, CI, consumer). When the
> product *is* an interface, this is load-bearing: an unlabelled surface will be
> mistaken for the contract.

Plus, in `horus-infer`: when a project is a fork, split, or pivot, **ask the owner**
for "why this exists" rather than distilling it from inherited docs.

## Why these two elements and not others

The failed session's own deliverable converged on exactly them. What it ended up
writing into `fabric-build`'s PRD was: a surfaces-and-audiences table, a note that
the wizard is the human surface, an origin paragraph (the CLI began as
deterministic steering for the medallion), and a "what `fab` already covers"
boundary test. Four things the template never asked for, all four needed on turn
one. **The output of the review is the missing template field** — that is the
evidence, not a hypothesis about what might help.

## Acceptance

- When a scaffolded or inferred project fills its Vision, the section should ask
  for why-it-exists and per-surface audiences alongside what/shape/boundaries.
- When `horus infer` runs on a repo whose Vision cannot be derived from inherited
  docs (a fork or pivot), it should ask the owner rather than restate the parent.
- The managed block and the PRD template stay consistent with each other and with
  `horus-infer`; the projected `.claude`/`.agents` skill copies regenerate.
- Gate: full suite green on the exact SHA. Probe: scaffold a throwaway project and
  confirm the new Vision elements appear in its `PRD.md` and its `AGENTS.md` block.

## Deliberately not doing

- **No gate or lint.** A check cannot tell whether a Vision paragraph is *true*,
  only whether text exists, and "must mention audiences" would be noise for
  single-surface projects. This stays guidance until a project fills the new
  elements and a session still gets lost.
- **No review-provenance field.** An earlier draft proposed recording that a
  session reviews another model's work. Rejected by the owner: the reviewer was
  left abstract on purpose, so any model could run the review.
- **No new frontmatter field for the objective.** Also rejected — the backlog card
  is already the durable representation of the next phase.

## Related

- `intent-preserving-goal-campaign` — same principle (bind the spirit, leave the
  form advisory) applied to cards; this card applies it to the Vision.
- `fresh-vs-resume-context-split` — adjacent, inverse case (a fresh session
  wrongly receiving a resume directive).

## Source

Owner-attended `process-retrospective` on the 2026-07-25 `fabric-build` review,
with the owner supplying the parent-repo-immunity observation that located the
defect. The corrected Vision now lives in `fabric-build`'s PRD as the worked
example.
