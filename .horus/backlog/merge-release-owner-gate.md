---
status: open
priority: high
readiness: shaping
readiness_reason: "Where the owner token lives and which commands it covers is an owner design decision."
created: 2026-07-19
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
