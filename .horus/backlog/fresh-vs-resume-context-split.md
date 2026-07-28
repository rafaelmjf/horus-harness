---
status: open
priority: low
readiness: deferred
readiness_reason: "Owner hold continues (2026-07-26). The 2026-07-21→2026-07-26 observation window yielded NO evidence: #386 swallowed the seeded prompt, so resume sessions received no handoff either and both modes were indistinguishable. The window genuinely starts 2026-07-26, now that #403 makes the resume path deliver."
created: 2026-07-19
last_refined: 2026-07-28
refine_passes: 2
vision_facet: "Continuity core"
phase: explore
tier: medium
type: bug
parallel: safe
created_by: owner
surface: horus/routines.py (resume_prompt / resume_context), horus/terminal_tui.py (launch-mode branch ~2573), horus/templates.py (PRD template + managed block), CLAUDE.md + AGENTS.md managed block, .horus/PRD.md frontmatter layout
---

# fresh-vs-resume-context-split — the resume directive should reach resume sessions only

**Why (owner, 2026-07-19):** the TUI already offers **fresh** vs **resume** as distinct
launch options, and the design intent is that resume loads the next action while fresh
does not. That intent is not supposed to be probabilistic — it is a plain IF/ELSE
enforced by the launch options. Today it is enforced at launch and then defeated
downstream, so a fresh session still ends up executing the previous session's directive.

**Observed (this repo, 2026-07-19, fresh inline-batch launch):** the owner opened a fresh
session intending something else and already knowing the pinned next action was blocked.
The agent nonetheless spent its opening tool calls running the stored `next_prompt`
checklist verbatim (fetch, verify PyPI version, curl `/health`, expect `/` 403) and framed
its entire opening read-out around the stale pinned next action.

## What is actually broken

The launch branch is correct and did the right thing:

- `horus/terminal_tui.py:2573` — `prompt = routines.resume_prompt(result.project) if
  result.mode == "resume" else ""`. A fresh launch receives an empty prompt; the
  directive was never injected.
- `routines.resume_prompt()` is what embeds `current_focus` / `next_action` /
  `next_prompt` (`horus/routines.py:180-191`).

The leak is one layer down, in storage layout rather than control flow:

- The Horus-managed block in `CLAUDE.md` / `AGENTS.md` instructs **every** session,
  unconditionally, to read `.horus/PRD.md` before substantial work — correctly, since
  Vision / Backlog / Shipped / Rules are the orientation a fresh session genuinely needs.
- But `next_prompt` and `next_action` live in that same file's frontmatter. So the fresh
  path declines the directive at launch and then reads it anyway, because directive and
  orientation are colocated in the one file both modes are told to read.

**Not a context-budget problem.** Measured on this repo at the time of the report:
PRD.md is 58,138 chars; the entire frontmatter is 3,503 (6%); the four directive/
orientation fields together are 3,391; `next_prompt` alone is roughly 1.4KB. Suppressing
it saves ~2% of one file. The cost is misdirection, not tokens — do not scope this as a
size reduction.

## Design question (open — decide in-card)

The constraint is fixed: **deterministic, enforced by the launch options, no reliance on
the model choosing to skip a section.** How to get there is open. Sketches, not a
decision:

- Separate directive from orientation at the storage level, so the always-read file
  carries only orientation and the directive lives where `resume_prompt` reads it and a
  fresh reader never encounters it.
- Or keep one file and split the *instruction*: the managed block scopes which parts of
  PRD.md each launch mode reads. Cheaper, but re-introduces a model-compliance step —
  weigh that against the constraint above before choosing it.
- Or have the fresh path receive an explicit non-empty prompt that orients without
  directing, rather than the empty string it gets today.

Whatever is chosen must keep working for **non-TUI entry points** — a bare `claude` /
`codex` in the project dir, a dispatched worker, a scheduled run — which never pass
through the TUI branch at all. That is the harder half of the problem and is the reason
the launch-mode IF/ELSE alone was not sufficient.

## Adjacent: the directive is a proposal, not an instruction

Even a correctly-routed resume prompt is a *previous session's hypothesis* about what
this session wants. The owner may open a resume session and still want something else.
This rule already exists in the repo but is scoped to a single step —
`.claude/skills/pathfinder/SKILL.md:76`:

> An intent carried in args, a stored `next_prompt`, or a scheduled brief is a PROPOSAL,
> not a confirmation.

with the calibration note that the 2026-07-17 convergence-test run treated a pre-pinned
intent as settled and skipped the ask. Same class, different surface, three days apart.
Consider whether generalizing that line into the managed block belongs in this card or a
separate one — it is a guidance rung, cheaper and broader than the routing fix, and the
two are independent.

## Deliberately not actioned yet — observe first (owner, 2026-07-19)

**This may be a feature, not a bug.** A fresh session that reads the pinned directive
arrives oriented and immediately useful; the failure mode is only visible when the owner
opens with a *different* intent than the one pinned. It is not yet known which case is
more common in real use, so acting now risks removing something that mostly helps in
order to fix something that occasionally misdirects.

The owner is holding this card and **observing across several more session launches**
before deciding anything. What to watch for, over that window:

- How often a fresh launch's opening moves actually match what the owner wanted, versus
  chasing a stale pinned action.
- Whether the context cost is ever load-bearing — the measurement above says ~2% of one
  file, so the prior is that it is not, and a bloat argument needs new evidence to stand.
- Whether the misdirection is self-correcting cheaply (one exchange, as on 2026-07-19) or
  compounds into wasted work before the owner notices.

Do not action this card on the strength of the single 2026-07-19 observation. If the
observation window shows the fresh-path directive is usually *right*, the correct outcome
is closing this as working-as-intended and keeping only the proposal-not-instruction
framing below.

## Acceptance (draft — refine before actioning)

- A fresh launch does not act on the stored `next_prompt` / `next_action`, while still
  getting Vision / Backlog / Shipped / Rules.
- A resume launch still gets the full pinned directive, unchanged.
- The distinction holds for entry points that bypass the TUI, or the card states
  explicitly which ones are out of scope and why.
- `horus resume`, the dashboard, `resume_preflight`, and scheduled/dispatched briefs
  continue to read the directive fields.

## Non-goals

- Not a context-size optimization (see the measurement above).
- Not a change to what continuity records — only to who is handed the directive.
- Not removing `next_prompt`; it earns its keep on the resume path.

## Notes

Raised by the owner after a fresh session executed a stale pinned checklist against a
different opening intent. The owner's framing: "resume loads the next action, fresh
doesn't — it doesn't need to be non-deterministic, it's a simple IF/ELSE condition to be
enforced via our launch options."

## Reviews

- 2026-07-26 — **Hold continues, but the evidence window restarts today.** The 07-19 hold
  said to observe several more launches before deciding. That observation never happened,
  for a structural reason nobody knew at the time: `session-remote-control-default` (#386,
  shipped v0.0.74 on 2026-07-21) put a bare `--remote-control` ahead of the positional
  prompt, and because that flag takes an *optional value* it consumed the seeded prompt as
  its session name. So from 07-21 until #403 landed on 07-26, **resume launches received no
  handoff via the prompt either** — every interactive session, fresh or resume, got the
  pinned directive by exactly one route: reading `PRD.md`. The two modes were
  indistinguishable, so no differential evidence could accumulate.

  Net: five days later there is still exactly **one** observation (2026-07-19), and the
  card's own guidance forbids acting on it alone. Deferred stands, for a sound reason
  rather than an assumed one, and the window starts now.

  What to watch, unchanged from the 07-19 list but now actually measurable: how often a
  fresh launch's opening moves match the owner's intent versus chasing a stale pinned
  action; whether misdirection self-corrects in one exchange or compounds; and whether the
  context cost is ever load-bearing (prior: no — measured at ~2% of one file).

  Not extracted this pass, still available: the card's own "Adjacent" suggestion to
  generalise *"a stored `next_prompt` is a PROPOSAL, not a confirmation"* from
  `pathfinder/SKILL.md:76` into the managed block. It is cheap, broad, and independent of
  the routing design; it was left unsplit deliberately to avoid a second concurrent
  managed-block change alongside `process-fixes-live-in-process-not-memory`.
