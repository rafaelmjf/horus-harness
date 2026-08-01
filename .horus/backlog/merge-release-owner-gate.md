---
status: shelved
shelved_on: 2026-08-01
priority: high
readiness: shaping
readiness_reason: "Held for a DEDICATED DESIGN SESSION (owner, 2026-07-28), not a refinement exchange. All four open questions are architectural: a hard gate on merge/release/deploy is a control every session lives with, and getting the envelope pass-through wrong either blocks legitimate autonomous dispatch or opens a hole. The strongest candidate answer is recorded below (reuse the existing PreToolUse chokepoint) but was deliberately not adopted in a screening pass."
created: 2026-07-19
last_refined: 2026-07-28
refine_passes: 1
vision_facet: "Accounts & isolation"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: agent
surface: a PreToolUse hook matching merge/release/deploy commands (horus/hooks or the per-account settings writer), horus/cli.py hook plumbing, .claude/settings.json + .codex/hooks.json projections
---

# merge-release-owner-gate — put the wall where the model's speed actually costs

## Why

The original motivating failure was a fast, literal agent turning a brainstorm into a
merged PR: the owner asked one small question and a few minutes later the work was
committed, PR'd and merged. v0.0.70 tried to fix that with prose — a launch "mode" whose
skill told the model to be less eager. #368 deleted that axis after the fresh-context
review found it could not work: the instruction sat in the same context window as the
model's own momentum, cost a launch turn to deliver, and could contradict the handoff it
wrapped.

The replacement is the permission posture, which the agent CLI enforces itself. That is a
real improvement, but it has a hole: **posture does not cover merge, release, or deploy.**
At `auto-edit` or `full-auto` a session can still run `gh pr merge`, push a tag, or run a
deploy script, because those are shell commands like any other. So today the guarantee
against the exact failure that started this is still "the model reads the rule and agrees
with it."

This card closes that hole with a deterministic wall, per the project's own control ladder
(instruction → deterministic signal → hard gate) — this class has now failed in the field
at least once, which is the standing bar for promoting to a gate.

## What this is not

- Not a return of session modes, and not a per-session behavioral setting.
- Not a general command allowlist or a sandbox. Scope is the small set of outward,
  hard-to-reverse actions.
- Not a replacement for CI or the exact-SHA gate — those verify *what* merged; this
  governs *whether the agent may merge at all* without the owner saying so.

## Candidate answers recorded 2026-07-28 (NOT adopted — for the design session)

There is a working precedent in-repo that bears on three of the four questions:
**`closure.direct_push_violations` already refuses at the `PreToolUse` chokepoint** and
decides from the actual branch and diff. Reuse it rather than building a second chokepoint.

Sketch offered and deliberately declined in favour of a dedicated session:

- **Where:** the existing `PreToolUse` chokepoint.
- **Token:** a short-lived file under `~/.horus/`, created only by the owner.
- **Covered:** `gh pr merge`, `git push --tags`, `gh release create`,
  `scripts/deploy-hosted.sh`.
- **Envelope pass-through:** validate a live envelope carrying `merge_authority`; never mint
  one.
- **Matching:** at shell command position only, never inside quoted prompt prose — the same
  parsing discipline the existing PR-check rule already states.

A narrower `gh pr merge`-only v1 was also offered and declined; it would leave the release and
deploy paths — the most irreversible of the four — ungated.

## Open design questions (why this is Shaping, not Ready)

1. **Where does the owner token live?** Candidates: an env var set at launch, a
   short-lived file under `~/.horus/`, an argument to an explicit `horus merge` path, or a
   Telegram `answer` via the existing input bridge (which already delivers owner choices
   without minting authority).
2. **Which commands are covered?** At minimum `gh pr merge`; probably `git push --tags`,
   `gh release create`, and `scripts/deploy-hosted.sh`. Needs to match at shell command
   position, never inside quoted prompt prose — the same parsing discipline already stated
   in the existing PR-check rule.
3. **How does an approved autonomous dispatch pass through?** The envelope already grants
   merge authority for a scheduled worker (`--allow-merge`). The gate must honour a real
   envelope without becoming a way for any session to mint one.
4. **Hook or CLI?** A `PreToolUse` hook covers ad-hoc shell use but is per-account
   settings (machine-local, must be projected to every isolated config dir). A CLI
   chokepoint is portable but only binds sessions that use it.

## Acceptance

When a session without owner authorization runs a covered command, the command should be
refused with a message naming how to obtain approval — and the refusal must hold
regardless of launch posture, agent, or model. An approved envelope, and an explicit owner
approval, should both pass through. Cover it with a test per covered command.

## Source

Deferred from #368 (`review-session-control-calibration` verdict) — named in the verdict's
follow-ups and consciously left unbuilt rather than half-wired.

## Reviews

- 2026-07-28 — **Held for a dedicated design session; candidate answers recorded** (owner,
  refine pass). Offered a full front-load of all four questions (which would have made this
  Ready—attended) and the owner chose a dedicated session instead. Recorded rather than
  re-derived next pass: the answers sketched above, and the reason they were not taken — the
  four questions are architectural, not editorial, and the envelope pass-through in
  particular has failure modes in both directions.

  **Exposure accepted in the meantime, stated plainly:** until this lands, the only control
  against the originating failure is instruction (render-confirm before merging a
  contract-bearing change), and instruction is what has already failed in the field twice —
  the original brainstorm-to-merged-PR, and #374 on 2026-07-20. Priority stays `high` on that
  basis.

  This card is the clearest evidence for the axis-2 lens minted in
  `refine-autonomy-hardening-lens` the same day: it is the best-structured card in the repo,
  with an explicit "why this is Shaping, not Ready" section, and it still correctly did not
  convert. More structure was never the missing thing.

- **2026-07-20 (fresh evidence, same failure class):** the owner dropped a format
  sketch as an example to try; the agent encoded its interpretation and opened AND
  auto-merged PRs (#374) without once rendering the format for confirmation. Pushers
  identified: the Rules' `branch → PR → auto-merge` default has no owner step for
  contract-bearing changes, and the green-checkpoint discipline rewards closing
  loops fast. This card's wall is the structural answer; until it lands, the
  working rule is render-confirm before merging any calibration/contract change.
