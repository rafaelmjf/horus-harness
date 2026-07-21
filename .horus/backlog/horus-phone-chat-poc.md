---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Deliberately a one-shot spike — casual exploration. Scope and pass/fail are drafted; owner to confirm SDK-vs-stream-json before running. Do not expand into an architecture commitment from this card."
phase: explore
type: spike
vision_facet: "Distribution"
---

# horus-phone-chat-poc — one-shot spike: text chat frontend to an agent session with phone-side tool approval

## Why

Explored 2026-07-21: a self-hosted **text** (not terminal) chat frontend to
**Horus-owned** agent sessions is feasible, and its durable value is (a) **one
unified phone UI across Claude + Codex** and (b) **the owner's own account-switching
layer** (enroll each account once, no re-verify on switch) — the two things that
survive even after vendors ship native mobile parity. The old Horus webapp failed on
*terminal* streaming (pty geometry scramble on a phone viewport); streaming
*structured events* as reflowing chat avoids that class of problem entirely.

Before committing to a meaningful architecture, prove the single riskiest unknown
cheaply. The owner's call, and the right one: a well-scoped one-shot PoC first.

## Intended outcome (owner intent: a rough thing to actually TRY)

The point (owner, 2026-07-21) is **not** a pure technical de-risk — it is a rough but
**genuinely usable** first version the owner can live with for a few days and then
decide whether to invest in building it properly. So the bar is "usable enough to
judge the experience," not "throwaway demo."

The thinnest slice that clears that bar: from a phone browser, watch one agent
session's **structured events render as chat**, **approve/deny a tool call** with the
agent proceeding accordingly, **see tool results** (so you know what happened), and
**survive a reconnect** — on the one account the owner actually uses.

Note this does **not** simplify below a throwaway; it slightly raises the bar. Still
justified: "rough usable" is ~20% of "built properly" (auth, multi-account,
persistence-hardening, rich rendering, cross-agent all cut), and the permission
round-trip — the one non-negotiable cost — would be paid in the real build anyway, so
it is not wasted. It is a cheap decision-gate, not a throwaway.

The permission round-trip stays the core, but for a sharper reason than "it's the
risk": an agent chat that cannot approve/deny tool calls is **useless for real work**
(Claude/Codex ask constantly), so it is what makes the tryout usable at all.

## Broad boundaries (scope to the RISK, not to "a chat UI")

- **The risk is NOT text-over-web** (known-good — every LLM chat UI does it). It is
  the **structured event stream + the tool-permission approve/deny round-trip**.
  Spend the one shot there.
- **Path:** Claude Agent SDK (best structured output + permission hooks) *or*
  `claude --output-format stream-json` as the event source; minimal server + minimal
  phone web page + a websocket. Pick the fastest route to the round-trip.
- **Account switching is STUBBED, not built.** Holding multiple account tokens in an
  app you own is known-solvable; it is not the technical risk, so it must not consume
  the PoC.
- **Explicit non-goals:** no auth, no real multi-account, no rich diff rendering, no
  hardened persistence, no polish, no cross-agent. Nothing ships to users from this.
- **Anti-scaffolding guard:** a "rough thing I keep using" tends to ossify into the
  permanent architecture. Set an explicit trigger — *if still in daily use after ~2
  weeks, stop and rebuild properly* — so the PoC does not silently become the product.

## Pass / fail

From a phone browser: assistant messages stream in live, and a tool call surfaces as
**approve/deny buttons** whose response routes back so the agent continues (or halts)
correctly. Binary yes/no.

## Open decisions for backlog-refine

- **Which agent to try it against — the decision that sets the target.** A rough chat
  to **Claude** teaches little about whether the owner would *use* it (remote control
  already covers Claude on the phone); the thing worth *trying* is the gap. So: if the
  question is "do I like text-chat-to-agent as a pattern?" → Claude via the SDK is the
  fastest pleasant build; if it is "is the Codex/unified gap worth filling?" → it must
  be **Codex CLI**. Decide which question the tryout answers up front.
- Agent SDK vs `stream-json` as the event source (follows from the agent choice).
- If it earns real investment, lean the follow-on on the durable justification
  (unification + own account layer), not the expiring Codex-on-Windows gap.

## Source

In-session discussion 2026-07-21 (owner proposed the one-shot PoC framing; agent
agreed and sharpened it to the permission round-trip). Research receipt:
`.horus/research/2026-07-21-mobile-agent-session-access.md` (suggested idea #2,
target #1, conclusion 4).
