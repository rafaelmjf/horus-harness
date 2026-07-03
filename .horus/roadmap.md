---
status: active
current_focus: "Round 3 done, supervisor-only hub proven: ttrpg Phase 4 + horus run --watch (v0.0.18) + gym UI regression root-caused (unversioned dist from unmerged worker branch) — all gates supervisor-reproduced, all pushed. Structure-test data sufficient."
next_action: "1) Run the workflow analysis (pre-registered acceptance test, PRD backlog item 1): closure/resume tool-call counts + Codex cold-reader quiz, v3 repo vs six-lane controls (each control gained 2 worker sessions today). 2) [bug] claude adapter failed/rc=0 mapping. 3) Awaiting Rafa: GM feel-review Phases 3+4; keiko phone re-check."
next_prompt: "Resume Horus. FIRST git fetch --all --prune; main clean, v0.0.18 on PyPI. THEN read .horus/PRD.md (single continuity file; ignore six-lane routing from older tooling). Primary task: the workflow analysis per the pre-registered acceptance test in PRD backlog item 1 — measure closure+resume costs and rerun the Codex cold-reader quiz on this repo (v3) vs agentic-gym-coach and agentic-ttrpg (six-lane controls). Worker spawns: horus run --agent codex|claude --posture auto-edit|full-auto --watch — codex workers cannot commit/bind sockets (supervisor owns gates+git); claude workers use branch+PR on the hub repo."<brief>\"` — remember the worker sandbox cannot commit or bind sockets; supervisor reproduces gates, commits, pushes. At closure: update PRD backlog/shipped + the two shim frontmatters + a session note; one consolidate pass max."
execution_recommendation: "continue-as-is for Horus-side backlog items (small, single-agent); delegate the next bounded cross-project phase to a codex worker as proven — supervisor owns gates and git."
last_updated: 2026-07-03
---

# Roadmap

**Content moved to `PRD.md` — the backlog lives there** (structure prototype,
2026-07-03). This file remains as a frontmatter shim for the dashboard NEXT box,
`horus resume`, and the merge freshness gate until the tooling reads PRD.md directly.
