---
status: open
priority: medium
readiness: ready
readiness_reason: "Observed concretely on 2026-08-03 in fabric-build: `close --check` printed 'Fresh — canonical continuity and work are checkpointed' with the continuity commit on a pushed but unmerged branch, and the agent read green as done and stopped. The surface is two known lines (`closure.py:588`, `cli.py:3176`) and the check's own docstring already states the intended semantics, so no design question is open — only which of two remedies to apply."
created: 2026-08-03
created_by: owner
last_refined: 2026-08-03
refine_passes: 0
vision_facet: "Continuity core"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus/closure.py:580-588 (_enforce_push upstream comparison, ok finding text), horus/cli.py:3176 (the 'Fresh — canonical continuity and work are checkpointed' summary)"
---

# close-check-claims-canonical-while-unmerged — a green gate that the default branch does not back

## Why — measured in fabric-build, 2026-08-03

A continuity close ran the full routine, committed to a branch, pushed it, and opened a PR.
`horus close --check` then printed:

```
  [ ok ] dashboard lanes are fresh (NEXT + focus authored, lanes updated this session)
  [ ok ] canonical continuity covers all product commits
  [ ok ] working tree clean
  [ ok ] local commits pushed to upstream

Fresh — canonical continuity and work are checkpointed.
```

Every line was true of the *branch*. None was true of `origin/main`, which still carried the
previous session's `current_focus` and none of the new Rules. The agent reported the close as
"fully green" and stopped with the PR open; the owner had to ask why it was still open.

## The defect is the wording, not the check

`_enforce_push` compares `HEAD` to `@{upstream}` — for a feature branch that is
`origin/<branch>`, so pushing the branch satisfies it. That is **correct and deliberate**: the
docstring says so explicitly.

> Reports only — never pushes — so the branch-first rule is respected by construction
> (an agent decides whether to push to a protected default).

So the check is doing exactly its job: proving nothing is *stranded on this machine*. The bug is
that the finding is worded `local commits pushed to upstream` and the summary escalates it to
**"canonical continuity … checkpointed"** — and *canonical continuity* is a defined term in this
project meaning the durable state everything else reads. `horus fleet --backlog`, `horus resume`
and the merge freshness gate all read `origin/<default>`. A gate that says "canonical" while the
default branch has none is making a claim it did not verify.

That gap is load-bearing precisely because the gate exists to replace a remembered habit with an
observed signal. An agent that trusts it — which is the whole instruction — stops one step short.

## Two candidate remedies, pick one

1. **Reword only (smallest).** Say what was actually verified: `local commits pushed to
   <upstream>` stays, and the summary becomes something like *"Fresh — continuity is committed
   and pushed to `<upstream>`"*, dropping "canonical" unless HEAD is the default branch. No
   behaviour change, no new git calls.
2. **Add an advisory finding.** When HEAD is not the default branch and the continuity commit is
   not an ancestor of `origin/<default>`, emit an `info`/`warn`: *"continuity is on
   `<branch>`; `origin/<default>` does not carry it yet"*. Advisory only — never blocking, never
   pushing.

Remedy 2 is the more useful signal but must stay non-blocking, because
[`session-process-cadence`](session-process-cadence.md) deliberately wants capture work batched
on an unmerged branch and treats the session branch as a recovery vehicle. This card must not
turn that into a failure — it only makes the state legible.

## Acceptance

- When the continuity commit is on a branch that `origin/<default>` does not contain, `horus
  close --check` no longer describes the result as *canonical* continuity being checkpointed.
- The exit code is unchanged in that situation — this is a truthfulness fix, not a new gate.
- A close performed directly on the default branch still reports exactly as it does today.
- `enforce_push: false` repos and repos with no upstream are unaffected.

## Related

- `session-process-cadence` (shelved) — owns the *granularity policy* of when to merge, and
  argues for batching on a branch. This card does not touch that policy; it only stops the gate
  from overstating what a green run proves. Its own note that "an unmerged card is invisible to
  `origin/<default>`" is the same underlying fact seen from the card side.
- `concurrency-safe-continuity` — mentions `close --check` for a different reason (PRD.md as a
  merge-conflict hotspot).

## Source

Observed by Claude Opus 5 during a fabric-build continuity close, 2026-08-03. The close itself
landed as fabric-build PR #96 (`674fecc`); the gate reported Fresh while that PR was still open.
