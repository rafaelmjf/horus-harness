---
status: shipped
priority: high
readiness: ready
autonomy: eligible
readiness_reason: "Root-caused live on 2026-07-25 from this machine's own argv, reproduced with a one-line CLI probe, and both candidate fixes were verified against the live `claude` binary. The remedy is a two-token edit in one function plus the regression test the existing suite is missing."
created: 2026-07-25
created_by: claude
vision_facet: "Continuity core"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus/adapters/claude.py:169-176 (interactive_command), tests/test_claude_adapter.py:172"
shipped_pr: 403
shipped_sha: 90e3fb1
---

# remote-control-flag-swallows-launch-prompt — `--remote-control` eats the seeded prompt, so no interactive launch is seeded and Remote Control does not come up

## Why — root-caused live, 2026-07-25

A `horus resume` of `fabric-build` opened a session that received **no resume
handoff at all**, and Remote Control was **off** until the owner typed
`/remote-control` by hand. Both symptoms are one cause.

`claude --help` (CLI 2.1.220):

```text
--remote-control [name]   Start an interactive session with Remote
                          Control enabled (optionally named)
```

`[name]` is an **optional-value** option, so Commander consumes the next
non-`-` token as the name. `interactive_command` appends the bare flag and then
appends `spec.prompt` last, so the prompt lands in exactly that slot. The live
argv of the affected session (`ps`, and `~/.horus/tmux/<sid>.json`):

```text
claude --session-id 9df1fa55-… --model opus --effort high \
       --permission-mode bypassPermissions \
       --remote-control "Resume the fabric-build project.\n\nBefore trusting local state:…"
```

The ~2 KB handoff was parsed as the Remote Control **session name**. Nothing was
left as the positional prompt.

### Proof — one-line probe against the live binary

```console
$ claude --remote-control "reply with exactly: PROBE_A_OK" -p --model haiku
Error: Input must be provided either through stdin or as a prompt argument when using --print
```

The prompt is gone. Corroborating evidence from the incident:

- Session record `~/.horus/accounts/claude-work/sessions/3303717.json` shows
  `"name": "fabric-build-e1", "nameSource": "derived"` — the value handed to the
  flag was **not** accepted as the name.
- The tmux scrollback shows the banner, then the owner's own typing; the
  authored handoff never appeared, and `bridgeSessionId` only registered after
  the manual `/remote-control`.

That an invalid multi-line name is what aborted the Remote Control start is
**inference** — Claude printed nothing. What is proven: the flag received the
prompt as its name, the prompt was never delivered, and RC was not active at
spawn.

## Blast radius

Every **seeded interactive Claude launch** since `session-remote-control-default`
(#386, v0.0.74) — resume handoffs, card scopes, dispatch briefs — on all
projects, because `[tui] remote_control_default` is on by default. Failure is
silent in both directions: the session looks healthy, just unseeded, and the
owner is left to notice the missing brief.

Not affected: the headless path. `build_command` puts the prompt immediately
after `-p` and never passes `--remote-control`, so `horus run` workers are
unharmed. Codex is unaffected (no such flag).

The pre-#386 argv had no optional-value flag ahead of the positional prompt,
which is why seeding worked before and why #386's live verification (CLI 2.1.216)
did not catch it — the flag *was* honored in that test; nobody checked that a
**prompt and the flag together** still both work.

## Fix — both candidates verified live

Preferred, the `--` separator:

```python
if spec.prompt:
    argv += ["--", spec.prompt]   # end option parsing; prompt is positional
```

It fixes this flag *and* any future optional-value flag, keeps Claude's own
derived name (`fabric-build-e1`), and additionally protects a prompt that begins
with `-`.

```console
$ claude -p --model haiku --remote-control -- "reply with exactly: PROBE_B_OK"   → PROBE_B_OK
$ claude -p --model haiku --remote-control probe-c "reply …: PROBE_C_OK"          → PROBE_C_OK
```

The explicit-name variant (`argv += ["--remote-control", name]`) also works but
guards only this one flag and requires inventing names Claude already derives.

## Acceptance

- `interactive_command` with **both** `remote_control=True` and a non-empty
  `spec.prompt` yields argv where the prompt is not the token following any
  optional-value flag — assert adjacency, not membership.
- The existing test (`tests/test_claude_adapter.py:172`) asserts only
  `"--remote-control" in argv`, and a separate test asserts the prompt is
  present; **neither exercises the combination**. Add the combined case, and
  assert the prompt is the final token preceded by `--`.
- Gate: full suite green on the exact SHA.
- Probe: `horus resume` a project with `remote_control_default = true` and
  confirm, in one session, that the handoff arrives **and** the RC banner/URL
  prints without a manual `/remote-control`.

## Related

- `session-remote-control-default` (#386, shipped v0.0.74) — introduced the flag
  that collides with the positional prompt; this card is its regression.
- `fresh-vs-resume-context-split` — depends on the seeded prompt actually being
  delivered; worth re-reading its assumptions once this is fixed.

## Source

Owner-attended diagnosis from `fabric-build`, 2026-07-25, on this machine's live
session argv (horus 0.0.74, Claude Code 2.1.220).
