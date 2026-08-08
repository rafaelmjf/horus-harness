---
status: open
priority: high
created: 2026-08-07
created_by: owner
readiness: shaping
readiness_reason: "Primary questions, pilot tasks, run topology and tool-use posture are pinned (2026-08-08). Two items remain before runs begin: the per-task answer key must be established and pinned on the shared SHA, and the owner must set the session/token ceiling for the nine runs."
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

## The three questions this must answer (owner, 2026-08-08)

These are the decision, in priority order. Speed and tokens are supporting evidence, not
the verdict.

1. **Does it help the agent understand the project?** Accuracy first — does the agent
   reach a *correct* understanding, localize the right surface, and avoid confident wrong
   claims? Time and tokens are secondary to whether the answer was right.
2. **Does it help the human understand the project?** Tested separately, on the same
   questions, measuring time and confidence. Graphify earns no agent credit for
   visualization, and no human credit was found in the removed visualizer.
3. **Is the maintenance cost of the integration worth adopting?** Generation and update
   cost, artifact bytes, diff noise, dependency burden, and integration surface — weighed
   against any measured benefit.

## Intended outcome

An evidence-backed retain, narrow, or drop verdict for each tool, separated by audience:
OpenWiki as human orientation/documentation and Graphify as agent code intelligence.
The result should also say whether any benefit begins only after a project crosses a
meaningful complexity threshold, rather than claiming that raw repository size alone is
the cause.

## Resolved — run design (2026-08-08)

**One SHA, three worktrees per task.** All conditions run from one pinned pushed SHA via
`horus run --worktree BRANCH --account <fixed> --model <fixed>`. Worktrees are used
whether or not runs overlap, because they are what makes each condition's context
*provably* only its own artifact — sequential runs in one checkout would require adding
and removing `graphify-out/` and `openwiki/` between runs, risking exactly the leakage
that would invalidate the comparison.

**Three prepared branches from that SHA**, differing only in artifact plus its instruction
layer. Confirmed branch-local, not user-global: there is no `~/.claude/skills/`, so a
baseline worktree cannot silently inherit the graphify skill.

**Batched by task, not by condition.** The three conditions of task 1 run together, then
task 2, then task 3 — never all nine at once. This bounds contention at three sessions and
buys a control sequential runs cannot: the three cells actually being compared face
identical API conditions, same hour, same model build. Spreading nine runs across a day
risks a model update or load shift landing *between* conditions, a worse confound than the
one concurrency introduces.

**Accounts do not vary.** Only `claude-work` and `claude-personal` are Claude accounts
(`codex-personal` is a different agent); three conditions cannot each get their own, and
the card fixes account as a controlled variable. So concurrency shares a rate limit and
contaminates wall-clock **by design**.

**Therefore: correctness is the gate, tokens are the efficiency proxy, time is
observational.** At n=1 per cell a sub-20% time difference is noise whether or not runs
overlap, so paying 3× wall clock to protect it is a bad trade. Stated assumption, to be
written into the verdict: this design will under-detect a tool whose only benefit is
*speed at equal tokens*. That is judged unlikely — context artifacts save tokens by
replacing exploratory search, and time follows tokens — but it is an assumption, not a
finding.

## Resolved — tool-use posture and its known confound (2026-08-08)

**Test as-shipped.** The conditions are asymmetric in *two* variables, not one, and the
asymmetry is a file-level fact the prompt cannot neutralize:

| Condition | Artifact | Agent-facing instruction layer |
|---|---|---|
| Baseline | none | none |
| OpenWiki | 22 files / ~61 KB | 6 lines in `CLAUDE.md`/`AGENTS.md`, explicitly deflationary: "optional just-in-time context, not required startup reading… treat source code and tests as authoritative" |
| Graphify | ~9.4 MB graph | 710-line `SKILL.md` + 8 reference files, projected to **both** `.agents/skills/` and `.claude/skills/`, plus a `## Graphify experiment` directive block preferring `graphify explain` |

Graphify's skill description routes on nearly every code question: *"Use for any question
about a codebase… especially when `graphify-out/` exists, where the question should be
treated as a graphify query first."* OpenWiki ships no consumption skill at all — its two
bundled skills (`mermaid-diagrams`, `write-connector`) generate wiki content and extend
OpenWiki itself.

As-shipped is the right posture because the question is whether to *adopt* these tools,
and the instruction layer is product, not noise — a tool that ships a good skill genuinely
is more useful to an agent. **But the verdict must not overclaim:** a Graphify win is a win
for *Graphify-plus-its-skill*, not evidence about code graphs. A follow-up with a
normalized pointer would isolate which did the work, and is worth running only if it wins.

Consequence worth stating: because OpenWiki's own block instructs behavior close to the
baseline, **OpenWiki-vs-baseline is the clean A/B on the artifact, and Graphify-vs-baseline
is the confounded one.** The OpenWiki result is the more scientifically solid of the two.

## Resolved — the three pilot tasks (owner, 2026-08-08)

Open work, not closed work: the owner's primary question is comprehension, which open
tasks test and recall of a merged diff does not. Each maps to one of the card's categories
and each carries an objective failure mode.

1. **herdr launch focus** — launching a session should redirect to it; today it moves to a
   tab that is already open. *Scoped to the herdr host only, not tmux.* Category:
   impact/debugging + correct localization. Surface starts at `horus/hosts/herdr.py` (516
   lines) against `horus/hosts/base.py`. **The trap:** herdr is an upstream third-party
   host, so the honest answer may be "Horus's adapter cannot fix this." Correctly
   localizing Horus-adapter vs. upstream *is* the accuracy test, and it is a proven trap —
   `herdr-server-shutdown-fragility` records a prior session getting exactly this
   distinction wrong ("initially mistaken for the cause").
2. **Session close semantics** — closing is confusing; closing a tab in herdr leaves a
   growing list of rows reading `vanished`, which should mean *crashed*. Category:
   source-and-test location. Surface: `horus/registry.py:39-67`
   (`is_deliberate_close` / `display_status`), its caller `horus/cli.py:875`, and
   `tests/test_terminal_tui.py:1494+`. Adjacent shipped work (#498) is in the PRD, so a
   condition may find it or miss it.
3. **Projectless session launch** — start a session from the TUI with no project, by
   selecting an account directly. Category: architecture/orientation. Requires
   understanding how project scoping threads through TUI → launch → accounts, and what
   breaks when it is absent.

## Scoring

- **Correctness against the pinned answer key first** (see below): right surface, right
  localization, no confident false claims. This gates the verdict.
- Then tokens; then files/commands consulted; then whether the extra artifact was actually
  used at all; then delivery gate where a change was produced.
- Wall-clock recorded but explicitly non-decisive, per the run design above.
- **False claims counted separately and weighted heavily** — a fluent wrong answer is worse
  than a slow right one, and is the specific failure mode a generated artifact can induce.

## Maintenance-cost evidence to record

- Generation and update time/tokens, artifact bytes, diff noise, dependency burden,
  incremental-update friction.
- **Integration-surface collision, specific to this repo:** graphify installs into
  `.agents/skills/` and `.claude/skills/` — the same directories `horus/skills.py` manages
  (`CLAUDE_SKILLS_SUBDIR`, `CODEX_SKILLS_SUBDIR`) and that `missing_or_stale` /
  `skill_findings` scan. Record whether a foreign skill in Horus-managed space produces
  drift findings or `horus doctor` noise. Graphify also self-installs across 19 agent
  platforms and ships an MCP server (`graphify-mcp`), which is additional surface to keep
  current.

## Human-usefulness test (question 2)

Answer the same repository questions from baseline docs and from OpenWiki, measuring time
and confidence. Do not award Graphify agent value for its visualization; the published
visualizer was already judged unhelpful and removed.

## Open decisions

- **The answer key.** Establish and pin the correct surface/localization for each of the
  three tasks, on the shared SHA, *before* any pilot run. Caveat to state when doing it:
  the key is authored with full source access and unbounded exploration — a different and
  more thorough process than a bounded pilot session — and whoever authors it is not a
  neutral party to the runs.
- **The spend ceiling** bounding the nine runs, and which Horus receipts supply comparable
  runtime and usage evidence.

## Convergence / drop criterion

Retain a tool only when it improves **accuracy** for its named audience — correct surface,
correct localization, fewer false claims — without a token regression, and its
generation/update burden plausibly amortizes over real use. Equal accuracy with lower
tokens is a *narrow* result, not a retain. Narrow it when only one audience or task class
benefits. Drop it when the baseline matches it on accuracy, when false claims increase, or
when maintenance cost cannot pay back. If Graphify shows no signal on Horus, do not carry
it into the smaller projects merely to complete a matrix; consider one large poorly
documented repo only if the evidence points specifically to complexity as the missing
variable.

Non-goals: publishing another Graphify site; merging either experiment before the
verdict; treating generated prose as canonical continuity; building a permanent
benchmark harness before the pilot proves repeated use.

Only if the Horus pilot shows a plausible signal, extend across the existing size ladder:
agentic-travel-guide (~4.1k tracked code lines), agentic-gym-coach (~24.9k), and
horus-harness (~86.5k). A later large, poorly documented repository is a second-order
test, not work to pre-invent now.

## Source

Owner decision, 2026-08-07, after the live `experiment/openwiki` (`7cda166`) and
`experiment/graphify` (`c22c79d`, visualizer `c670c7c`) trials. The Graphify publication
was removed; the OpenWiki publication remains private and Access-gated. Run design,
tool-use posture, primary questions and pilot tasks pinned by the owner 2026-08-08.
