---
status: open
priority: medium
created: 2026-07-20
created_by: agent
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Wildcard explore: verb grammar, stub shape, and project-name resolution undecided; the drop condition is part of the design."
phase: explore
type: feature
vision_facet: "Dashboard / cockpit"
---

# telegram-idea-capture — capture ideas from the phone, triage later (wildcard)

## Why

Ideas strike away from the terminal — especially during the owner's upcoming
trip — and today they either wait in the owner's head or die. The notify
listener already runs a bounded, deterministic, owner-locked two-way grammar
(read verbs + bounded mutations, no LLM, no minted authority); `capture
<project> <text>` would be one more bounded mutation that writes a shaping
STUB card into the named project's backlog. Divergent bet: phone-capture →
later triage is a workflow Horus can host without becoming a notes app.

## Intended outcome

Five real ideas captured over a week land as stubs and get honestly
dispositioned at the next refinement. **Converges** if captured stubs turn
into refined work; **dropped** if they rot as backlog noise — which would
prove idea-capture belongs outside Horus. Either verdict closes the wildcard.

## Broad boundaries

Rides the existing listener grammar and card scaffolding; stub cards are
`readiness: shaping`, `created_by: owner`, clearly marked captured-via-phone.
Non-goals: no free-text conversational parsing (stays in the future hermes
profile); no capture without an exact project match (resolve-or-refuse, like
account names); no authority of any kind.

## Open decisions for backlog-refine

- Stub card minimal shape (title + raw text + date, or more?).
- Project-name resolution UX over Telegram (exact? fuzzy-refuse?).
- The evaluation window and who runs the converge/drop review.

## Source

Agent wildcard at the 2026-07-20 scope-cards gate, owner-approved;
`.horus/research/2026-07-20-roadmap-branches-rebaseline.md` branch C context.
