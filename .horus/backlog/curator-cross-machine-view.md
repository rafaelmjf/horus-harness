---
status: open
priority: medium
readiness: shaping
readiness_reason: "Validation-first by owner request (2026-08-13): prove a unified cross-machine picture is actually useful with a cheap two-machine trial BEFORE building the merged-repo view. Needs a shared remote + a second machine, and an owner judgment call, so it is not Ready to implement."
created: 2026-08-13
created_by: owner
last_refined: 2026-08-13
refine_passes: 1
topic: curator-portfolio
tier: medium
type: feature
parallel: safe
surface: "horus/curate.py build_view_data/render_real_view (read the merged portfolio repo, not just the local manifest); ~/.horus/portfolio shared remote setup"
---

# curator-cross-machine-view — unified portfolio across machines, validate before building

Extends the curator from cross-**account** (free, all stores on one disk) to cross-**machine**
(raw lives on different disks). Owner wants to **validate usefulness before over-building**.

## The model (decided in principle)

Curation always runs **locally on each machine** — raw never travels. Machines converge
through the **shared portfolio git repo** (already built to push only each machine's own
sessions, partitioned by session-id → conflict-free merges). SSH is just how you reach a
machine to run its own `horus curate`; it is NOT a raw-transport. This respects "raw stays
local" and reuses the git-of-record as the cross-machine join.

## Cheapest validation FIRST (do this before any code)

1. Create one private portfolio repo; on machine A `git -C ~/.horus/portfolio remote add origin <url>`
   and `horus curate --interpret --portfolio --push`.
2. On machine B (SSH in or local): same, pushing to the same remote; `git pull` on A.
3. **Look at the merged repo by hand** — `index.md` + `projects/*/curation.json` from both
   machines in one tree. Judgment call: is a unified cross-machine picture actually valuable,
   or is per-machine enough? If not valuable, STOP here — do not build the view.

## Build ONLY if validated

- Teach `build_view_data` / `render_real_view` to render from the **merged portfolio repo**
  (all machines' skeleton + curation), not just the local capture.
- Raw ▾ drill-down stays available **only for sessions whose raw is on this machine**;
  remote sessions show curation + metadata, no transcript.

## Acceptance (build phase)

- With two machines' curation merged in one portfolio repo, the local view lists **both**
  machines' projects/sessions; a remote-machine session shows its curated summary and no raw
  drill-down, a local one still shows raw.

## Non-goals

- No SSH/network transport of raw transcripts, ever.
- No central server (that remains the anchor's phase-6 "conditional door").
- No live sync — convergence is git push/pull, on demand.

## Source

Owner question 2026-08-13: "cross-account curation is great — can it be cross-machine too, e.g.
over SSH?" Resolved in principle to local-curate + git-converge; carded validation-first so the
merged-view work is only built if a real two-machine trial proves it useful. The `curator-ledger-foundation`
card marked cross-machine curation out of scope "until a concrete need lands" — it has now landed.
