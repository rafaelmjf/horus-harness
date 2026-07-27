---
status: open
priority: low
readiness: deferred
readiness_reason: "Reserved as `autotest-e2e-away-mode-drill` payload. Decision-complete and implementable — that is exactly why it must stay undone: the drill needs a real always-green leg, and implementing it early destroys the experiment (the drill card records that a session nearly took it). TRIGGER: released to Ready—eligible when the drill is armed and this leg is either used or dropped, or when the drill is abandoned. Deferred, not Gated: nothing is missing, it is deliberately inactive until that trigger."
created: 2026-07-18
last_refined: 2026-07-27
vision_facet: "Introspection & self-improvement"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: agent
surface: shared verification guidance — the managed-block "reproduce the gate" discipline (CLAUDE.md/AGENTS.md) and/or the bundled verify/horus-execution skill
---

# verify-guidance-long-running-services — "active + emits its signal", not "it installed"

**Why (2026-07-18, generalized from #322):** the `203/EXEC` crash-loop escaped the
live probe because it accepted `activating`/"unit installed" as proof. The general
lesson — a long-running service/daemon's verification means it reaches running
state AND emits its expected signal (journal/health), never just that it started —
belongs in SHARED guidance so it travels across models and accounts, not one
model's memory.

## How

- Add one line to the managed-block "reproduce the gate" / runtime-gate discipline
  (which already says "drive the real surface once; mocked tests bless nonexistent
  flags"): for a service/daemon, confirm it reaches `active`/running AND logs/serves
  its expected signal, not merely that the unit/process installed or started.
- Keep it concise; it's an extension of the existing runtime-gate rule, not a new
  section. If a bundled skill (verify / horus-execution) is the better home, add it
  there instead — pick ONE home, don't duplicate.
- Managed-block edits bump the block version; skill edits bump the skill version
  (existing rules).

## Acceptance

- The shared guidance names the long-running-service verification bar; it projects
  to Claude + Codex (managed block or bundled skill, whichever is chosen).
- No duplication across block and skill.

## Non-goals

- No automated service-health framework — this is the deterministic self-verify
  card's job (`service-installers-self-verify-active`); this card is the guidance rung.

## Reviews

- 2026-07-21 — **Kept Ready (eligible); tagged prime e2e-drill food** (owner, refine
  pass): a guidance one-liner — small, low-risk, tiny always-green PR — so it is a good
  *real* leg for `autotest-e2e-away-mode-drill` (one of the 3 account legs) rather than a
  throwaway fake card.

### 2026-07-27 — Rafael Figueiredo (agent)
Verdict: Ready/eligible -> Deferred (reserved as drill payload, trigger named)

2026-07-27, owner-approved from a wildcard run. This card was the ONLY card `is_autonomous_candidate()` returned, while `autotest-e2e-away-mode-drill` line 131 says it 'must NOT be implemented early — it is payload, not free work, and this session nearly took it'. So the deterministic selector was pointing an unattended loop at precisely the card that would destroy the drill, and the only thing preventing that was prose in the PRD and next_prompt — the authority the managed block explicitly says does not count. The wildcard run first proposed a NEW `reserved` frontmatter state for this; the owner's question exposed that as redundant. `deferred` is already defined as 'deliberately inactive until an explicit trigger or owner review', which is exactly this situation, and deferred cards are already excluded from `is_autonomous_candidate()` with no code change. So the defect was never a missing schema feature — it was one misclassified card. Reclassified with the trigger named in `readiness_reason`. Effect: the eligible pool now reads 0, which is the honest state (there is no autonomously-runnable work in this repo right now); it previously read 1, and that 1 was a trap.
