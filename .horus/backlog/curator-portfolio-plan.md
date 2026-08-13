---
status: open
priority: medium
readiness: shaping
readiness_reason: "Strategic decisions remain owner/LLM work, not screening: the trigger-vs-seamless question (owner explicitly unsure) and whether the proposal-into-project flow is needed at all. Both are [session] work. The buildable ledger foundation was split out to `curator-ledger-foundation` (Ready) on 2026-08-13."
created: 2026-08-12
created_by: owner
last_refined: 2026-08-13
refine_passes: 1
type: feature
topic: curator-portfolio
parallel: safe
tier: large
surface: "strategy anchor only — no direct surface; the buildable surface lives on `curator-ledger-foundation`"
---

# curator-portfolio — cross-surface session curator + harness-neutral portfolio (strategy anchor)

**Open-ended anchor card.** Captures the direction validated in the 2026-08-12 exploration + PoC
and the strategic decisions still open. The buildable ledger foundation (extraction, attribution,
deterministic capture, batched LLM curation, git-of-record portfolio) was **split out to
`curator-ledger-foundation` (Ready/attended) on 2026-08-13** and does not gate this card. What
remains here is genuinely unresolved and needs a working session, not a screening exchange.

## Thesis

Horus's durable value is **harness-neutral project info** — backlog, next step, decisions —
that outlives any agent, account, app/CLI, or machine. The gap surfaced in the ceremony/scope
reflection: *maintaining* that info is a per-session ritual coupled to one harness, so it drifts
and feels like overhead. The move: an **out-of-session curator** that reads the exhaust every
surface already drops locally and distills it into a neutral, cross-project **portfolio** any
agent can read — maintenance becomes asynchronous and evidence-driven instead of an in-session tax.

## What the PoC proved (2026-08-12; sample under an ephemeral temp dir)

- Works across **23 projects / 80 sessions**, not just the self-referential case — output is
  specific and actionable, not generic.
- The session **ledger** (date/account/surface/agent/branch/turns + rich segmented summaries +
  raw drill-down) is the **high-value, low-risk foundation** — build it first. The card/topic
  **proposal engine is the lossy layer** on top.
- **Attribution is product-critical.** Git remote is the join key; Codex early-cwd
  misattribution, merged checkouts, and moved clones all appeared — and were self-flagged, not
  silently wrong. This is hardening target #1.
- Summaries must **scale with the session** (segment by branch/topic); flat one-liners aren't
  representative of long multi-branch sessions.
- Two independent axes: **surface** (App/CLI/SDK, from `entrypoint`) and **account** — the app
  is 57 of 80 sessions, so any surface-blind or hook-based design misses most of the work.
- Independent action item: a **leaked Notion credential in `pm-for-agents`** — rotate it.
- The view was rebuilt to the **rafaelfigueiredo.com sumi-e** design (warm paper, ink, one seal).

## Settled this session

- **Integrate into horus**; `horus-harness → horus-builder` eventually (rides the existing
  `product-naming` rename card — low priority, do it when convenient).
- **v1 storage = git-of-record** (a private portfolio repo). **No local server in v1.** Each
  project's own `.horus/` stays authoritative; the portfolio is derived and regenerable
  (delete-tomorrow test must always pass).
- **Raw transcripts stay LOCAL** — never pushed. Secrets live in raw (see the credential above).
- **Ledger-first.** Proposals landing into a project's own `.horus/` come later, by acceptance.
- **Capture/curate split:** a cheap deterministic CLI capture (factual metadata skeleton, no
  LLM) + a batched LLM curation pass (the interpretation).

## Draft phased plan

Phases 1-3 (extraction + attribution, the ledger, the portfolio repo) — the settled,
buildable half — moved to **`curator-ledger-foundation` (Ready/attended)** on 2026-08-13.
This anchor now carries only the phases that are still genuinely open:

4. **Trigger / sync.** — OPEN, decision #1 below.
5. **(Later) Proposals into projects.** Cards/topics land into a project's own `.horus/` by
   acceptance; two-tier onboarding (universal portfolio + opt-in in-repo); rejection ledger.
   — OPEN, decision #2 below (needed at all?).
6. **(Conditional door) Local tailnet server** as a derived read/render layer over the git
   store — real-time state, search at scale, write-back, phone access. Only when a concrete need
   lands; never the source of truth. Deferred until a concrete need appears.

## Open decisions (still live — [session] work)

1. **Trigger vs "seamless" — the big one, UNRESOLVED.** The ledger card ships with a manual
   `horus curate` CLI, so this no longer blocks any build — it's now about how to make refresh
   *feel* automatic. Options weighed: scheduled reconciler + on-login catch-up + manual CLI (no
   daemon); session-end hooks (rejected — miss the app, per-harness, add exit latency);
   file-watcher daemon (= a service, deferred). Owner is not convinced any *feels* seamless
   enough. Best resolved after the manual ledger exists and the real friction is felt.
2. **Proposal lifecycle — needed at all?** Is the read-only unified **ledger** the actual
   product, with the accept-into-project proposal flow a maybe? The ledger tested as the stronger,
   safer half. Decide after the ledger is in daily use.

### Resolved / delegated by the 2026-08-13 split

- **Capture push scope** → decided on the ledger card: skeleton-only, raw stays local, no
  cross-machine curation in v1.
- **Where curation runs** → each machine curates its own (ledger card, phase 3).
- **Portfolio granularity / confidentiality** → deferred; current use is clean, no client data.
- **Rename timing** → rides `product-naming`, not this topic.

## PoC artifact note

The sample output + sumi-e view live under a temp dir (`horus-builder-poc/`) and will be cleaned
up. If worth keeping as a reference, move it somewhere durable first.

## Source

2026-08-12 exploration: ceremony/scope reflection → curator/portfolio design → a PoC over 80 local
sessions across both agents and all accounts → the sumi-e view. This card is the durable anchor
for that direction.

## Reviews

### 2026-08-13 — split, owner-approved (backlog-refine)

The anchor bundled an owner-settled, low-risk buildable foundation (the ledger — phases 1-3) with
two genuinely-open strategic decisions. During refinement the owner approved splitting: the ledger
foundation became `curator-ledger-foundation` (Ready/attended) with a manual `horus curate` CLI as
its v1 trigger, so it no longer waits on the seamless-trigger question. This card stays Shaping and
carries only decisions #1 (seamless trigger) and #2 (proposal lifecycle) — both [session] work best
resolved once the ledger is in daily use. Also cleaned the two lint warnings: added `readiness_reason`
and dropped the stray `autonomy` field (autonomy belongs only on Ready cards).
