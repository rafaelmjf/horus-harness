---
state: settled
priority: medium
created: 2026-08-09
---

# generated-context-evaluation — do generated context artifacts help anyone?

## The problem

Two tools generate context artifacts for a codebase: one writes a documentation wiki using a language model, the other extracts a code graph. Both had been trialled and both produced something that looked useful. Neither had been tested for whether it actually helps an agent or a person understand the project — and **neither earns its maintenance merely by producing an artifact**.

## What was decided

**Both dropped for agent-facing use.** Six sessions across two deliberately different task shapes, all from one pinned commit: no accuracy difference in any cell, no false claims anywhere, and the plain repository was cheapest both times. The "the task was too easy" objection does not survive the second task, which required assembling an answer from four unrelated files.

The human question closed separately: the published wiki was reviewed and its **form** rejected, not its idea.

What survives is the principle, now a rule: **prefer derived over generated**. A projection over committed files cannot hallucinate, refreshes for free, carries provenance, and cannot drift silently. An authored artifact fails all four — and one of the two tools additionally injected "you MUST run me before reading source files" on every file read, which is coercion rather than context.

No work follows from this topic.
