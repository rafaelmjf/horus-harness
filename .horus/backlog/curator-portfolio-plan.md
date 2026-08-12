---
status: open
priority: medium
readiness: shaping
autonomy: attended
created: 2026-08-12
created_by: owner
type: feature
topic: curator-portfolio
parallel: safe
tier: large
surface: "new subsystem (eventual horus-builder): reads ~/.claude & ~/.codex session stores + isolated-account dirs; writes a private portfolio git repo; regeneratable static view"
---

# curator-portfolio — cross-surface session curator + harness-neutral portfolio (draft plan)

**Open-ended anchor card.** Captures the direction validated in the 2026-08-12 exploration + PoC,
a draft phased plan, and the decisions still open. NOT ready to build — several mechanism
decisions remain, above all the trigger-vs-"seamless" question the owner is still unsure about.

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

1. **Extraction + attribution foundation.** Read `~/.claude/projects`, `~/.codex/sessions`, and
   isolated-account dirs; parse both record schemas; attribute by git remote (handle early-cwd,
   merged checkouts, moved clones, non-project sessions). Emit the deterministic metadata
   skeleton. Secret redaction + scan. Watermark per session on **content change** (sessions
   resume across days — one file spanned ten).
2. **The ledger.** Per-session rich summary: `context` + `segments` (proportional to length,
   segmented by branch/topic) + Discussed/Decided/Shipped/Open. Per-project unified history
   (merged checkouts) + global timeline. Summarize on a cheaper model tier (plugs into horus's
   model routing).
3. **The portfolio repo.** Private git remote; per-project + cross-project index; regeneratable
   static view (sumi-e). Push the interpreted portfolio + skeletons; raw stays local. Each
   machine pushes only its own sessions (partition by session-id → conflict-free merges).
4. **Trigger / sync.** — OPEN, see below.
5. **(Later) Proposals into projects.** Cards/topics land into a project's own `.horus/` by
   acceptance; two-tier onboarding (universal portfolio + opt-in in-repo); rejection ledger.
6. **(Conditional door) Local tailnet server** as a derived read/render layer over the git
   store — real-time state, search at scale, write-back, phone access. Only when a concrete need
   lands; never the source of truth.

## Open decisions (to discuss)

1. **Trigger vs "seamless" — the big one, UNRESOLVED.** Options weighed: scheduled reconciler +
   on-login catch-up + manual CLI (recommended, no daemon); session-end hooks (rejected — miss
   the app, per-harness, add exit latency); file-watcher daemon (= a service, deferred). Owner is
   not convinced any of these *feels* seamless enough. What makes it feel automatic without
   standing up a daemon? Does the capture/curate split reduce friction or add it?
2. **Capture push scope.** Skeleton-only (recommended; raw stays local) vs pushing
   redacted-filtered transcripts — the latter only needed if curation runs on a *different*
   machine than capture. Do we need cross-machine curation in v1?
3. **Where curation runs.** Each machine curates its own (simplest; raw never travels) vs
   offloading to one machine or a scheduled agent task. The app *can* schedule agent tasks
   (Claude/Codex) — is that the natural home for the curate half?
4. **Portfolio granularity / confidentiality.** One portfolio per GitHub identity; work/personal
   sharding as a trust boundary. Deferred — current use is clean, no client data.
5. **Proposal lifecycle — needed at all?** Is the read-only unified **ledger** the actual
   product, with the accept-into-project proposal flow a maybe? The ledger tested as the stronger,
   safer half.
6. **Rename timing.** `horus-harness → horus-builder` — when to pull the trigger.

## PoC artifact note

The sample output + sumi-e view live under a temp dir (`horus-builder-poc/`) and will be cleaned
up. If worth keeping as a reference, move it somewhere durable first.

## Source

2026-08-12 exploration: ceremony/scope reflection → curator/portfolio design → a PoC over 80 local
sessions across both agents and all accounts → the sumi-e view. This card is the durable anchor
for that direction.
