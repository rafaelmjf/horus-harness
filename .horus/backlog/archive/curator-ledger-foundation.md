---
status: shipped
priority: medium
readiness: ready
autonomy: attended
created: 2026-08-13
created_by: owner
last_refined: 2026-08-13
refine_passes: 1
topic: curator-portfolio
tier: large
type: feature
parallel: safe
surface: "new subsystem: reads ~/.claude/projects + ~/.codex/sessions + isolated-account dirs; deterministic `horus curate` capture (metadata skeleton); batched LLM curation pass; writes a private portfolio git repo (raw stays local)"
depends-on: []
shipped_pr: 510
shipped_sha: 2f4957b
---

# curator-ledger-foundation — the cross-surface session ledger (phases 1-2 of curator-portfolio)

Split out of `curator-portfolio-plan` on 2026-08-13 (owner-approved). This card is the
**buildable, owner-settled half**: read the session exhaust every surface already drops
locally, attribute it, and distill it into a neutral cross-project **ledger**. The
strategic opens (seamless trigger, proposal-into-project lifecycle) stay in the anchor
and do NOT gate this card. v1 trigger is the manual `horus curate` CLI — no daemon, no
service, no decision owed.

## Why

Horus's durable value is harness-neutral project info that outlives any agent, account,
app/CLI, or machine. The 2026-08-12 PoC proved the **ledger** (date/account/surface/agent/
branch/turns + segmented summaries + raw drill-down) is the high-value, low-risk
foundation, tested across 23 projects / 80 sessions with specific, actionable output.
The proposal engine on top is the lossy layer and is deferred. Build the ledger first.

## How

1. **Extraction + attribution.** Parse both record schemas (`~/.claude/projects`,
   `~/.codex/sessions`, isolated-account dirs). Attribute each session by **git remote**
   (the join key). Handle the failure modes the PoC surfaced and **self-flag** rather than
   silently mis-attribute: Codex early-cwd misattribution, merged checkouts, moved clones,
   non-project sessions. Attribution is hardening target #1.
2. **Deterministic capture (`horus curate`, no LLM).** Emit the factual metadata skeleton
   per session. **Secret redaction + scan on the skeleton** (the PoC found a leaked Notion
   credential in raw — raw must never travel). Watermark per session on **content change**,
   not on date — sessions resume across days (one file spanned ten).
3. **Batched LLM curation (interpretation).** Per-session rich summary: `context` +
   `segments` proportional to length, segmented by branch/topic (flat one-liners misrepresent
   long multi-branch sessions) + Discussed/Decided/Shipped/Open. Per-project unified history
   (merged checkouts) + global timeline. Summarize on a cheaper model tier via horus's
   existing model routing. Each machine curates its own sessions in v1.
4. **Portfolio repo (git-of-record).** Private remote; per-project + cross-project index;
   regeneratable static view (rafaelfigueiredo.com sumi-e). Push interpreted portfolio +
   skeletons only — **raw transcripts stay local**. Partition by session-id so each machine
   pushes only its own sessions → conflict-free merges. The delete-tomorrow test must pass:
   each project's own `.horus/` stays authoritative, the portfolio is derived.

## Acceptance

- `horus curate` produces the deterministic metadata skeleton for both Claude and Codex
  session stores with no LLM in the loop, and the secret scan flags a planted test
  credential in the skeleton output.
- Attribution self-flags (never silently wrong) on a merged-checkout and a moved-clone case.
- The LLM pass emits length-proportional segmented summaries; a long multi-branch session
  produces >1 segment.
- The portfolio repo pushes interpreted output + skeletons only; a grep for raw-transcript
  content in the pushed tree returns nothing.
- Delete-tomorrow: wipe the portfolio repo, re-run, and the same portfolio regenerates from
  local stores + each project's `.horus/`.
- Gate: full pytest suite green on the exact SHA. Probe: run `horus curate` over the real
  local stores on this machine, confirm a known multi-branch session renders correctly in the
  ledger and no secret appears in the pushed repo.

## Non-goals

- **No trigger automation** — manual CLI only in v1; the scheduled-reconciler / on-login /
  seamless question lives in the anchor.
- **No proposal-into-project flow** — the ledger is read-only; landing cards/topics into a
  project's `.horus/` by acceptance is deferred (anchor).
- **No local server** — the conditional tailnet read/render layer is deferred (anchor).
- **No cross-machine curation** — each machine curates its own; pushing redacted transcripts
  for remote curation is out of scope until a concrete need lands.
- **No rename** — `horus-harness → horus-builder` rides `product-naming`, not this card.

## Source

Split from `curator-portfolio-plan` (2026-08-13, owner). Grounded in the 2026-08-12
exploration + PoC over 80 local sessions across both agents and all accounts. The PoC
artifact lives under a temp `horus-builder-poc/` dir — move it somewhere durable if kept.

## Related

- `curator-portfolio-plan` — the anchor; carries the strategic opens this card excludes.
- `product-naming` — owns the eventual `horus-harness → horus-builder` rename.
