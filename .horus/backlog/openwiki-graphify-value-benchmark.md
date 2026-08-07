---
status: open
priority: high
created: 2026-08-07
created_by: owner
readiness: shaping
readiness_reason: "The comparison contract is pinned, but backlog-refine must still choose the three pilot tasks and their source/test ground truth, cap the fresh-session spend, and decide whether tool use is forced or merely available before any runs begin."
phase: explore
type: spike
vision_facet: "Introspection & self-improvement"
---

# openwiki-graphify-value-benchmark — test generated context against the repo-native baseline

## Why

The live OpenWiki and Graphify trials answered the visual question but not the value
question. OpenWiki produced readable human-oriented pages, while Graphify's published
6,868-symbol graph collapsed into 239 generic communities and was removed. Graphify's
focused `explain` queries did expose real callers, tests, provenance, and source lines,
so its possible agent value remains untested. Horus already has a strong repo-native
baseline — `AGENTS.md`, `.horus/`, source, tests, and direct search — and neither tool
earns maintenance merely by generating an artifact.

The current experimental branches are not a valid A/B comparison because they were
generated from different source SHAs. Their maintenance footprints also differ sharply:
the OpenWiki trial generated 22 files / about 61 KB, while Graphify's `graph.json` alone
is about 9.4 MB and the experiment added roughly 306,000 lines including its projected
instructions.

## Intended outcome

An evidence-backed retain, narrow, or drop verdict for each tool, separated by audience:
OpenWiki as human orientation/documentation and Graphify as agent code intelligence.
The result should also say whether any benefit begins only after a project crosses a
meaningful complexity threshold, rather than claiming that raw repository size alone is
the cause.

## Broad boundaries

- Regenerate baseline, OpenWiki, and Graphify conditions from one exact pushed source
  SHA. Keep model, effort, account, permission posture, and task wording fixed; every
  task starts in a fresh session with no cross-condition resume context.
- Start with a bounded Horus pilot: three representative tasks across the three
  conditions (nine sessions). Cover architecture/orientation, source-and-test location,
  and impact/debugging or one small cross-module delivery.
- Score correctness against pinned source/tests first; then time, tokens, false claims,
  files/commands consulted, successful delivery gate, and whether the extra artifact was
  actually used.
- Record generation/update time and tokens, artifact bytes, stale/noisy diffs, dependency
  burden, and incremental-update friction. A synthetic context-compression benchmark or
  visual appeal is supporting evidence only.
- Test human usefulness separately: answer the same repository questions from baseline
  docs and OpenWiki, measuring time and confidence. Do not award Graphify agent value for
  its visualization.
- Only if the Horus pilot shows a plausible signal, extend across the existing size
  ladder: agentic-travel-guide (~4.1k tracked code lines), agentic-gym-coach (~24.9k), and
  horus-harness (~86.5k). A later large, poorly documented repository is a second-order
  test, not work to pre-invent now.

Non-goals: publishing another Graphify site; merging either experiment before the
verdict; treating generated prose as canonical continuity; building a permanent
benchmark harness before the pilot proves repeated use.

## Open decisions for backlog-refine

- Which exact three Horus tasks have unambiguous source/test ground truth and comparable
  difficulty across conditions?
- Should the first pass force use of the available tool (measuring its ceiling), expose
  it without instruction (measuring discoverability), or budget one of each?
- What session/token ceiling bounds the nine-run pilot, and which Horus receipts provide
  comparable runtime and usage evidence?
- Is the provisional retention threshold accepted: equal-or-better correctness, at
  least 20% lower median time or tokens in two task categories, and update cost paid back
  within roughly ten real sessions?
- What result is strong enough to justify the portfolio ladder, and what result drops a
  tool immediately?

## Convergence / drop criterion

Retain a tool only when the controlled tasks show a repeatable benefit for its named
audience without lower correctness, and its generation/update burden plausibly amortizes
over real use. Narrow it when only one audience or task class benefits. Drop it when the
baseline matches it, false claims increase, or maintenance cost cannot pay back. If
Graphify shows no signal on Horus, do not carry it into the smaller projects merely to
complete a matrix; consider one large poorly documented repo only if the evidence points
specifically to complexity as the missing variable.

## Source

Owner decision, 2026-08-07, after the live `experiment/openwiki` (`7cda166`) and
`experiment/graphify` (`c22c79d`, visualizer `c670c7c`) trials. The Graphify publication
was removed; the OpenWiki publication remains private and Access-gated.
