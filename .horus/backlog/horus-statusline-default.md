---
status: open
priority: medium
created: 2026-07-17
vision_facet: "Accounts & isolation"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: new horus/statusline.py (portable renderer) + `horus statusline` CLI; account provisioning writes settings.json statusLine pointer; overlaps account-settings-sync
---

# horus-statusline-default — ship the status line, don't hand-configure it per machine

**Why (owner, 2026-07-17):** the owner asked "can we make this default ship with
horus, so if I install on other machines I get the same display by default — or do
I always need to configure individually, for windows, linux and mac?"

Today the display lives in `~/.claude/statusline.sh`, hand-written on one machine.
It cannot be the shipped default, because it is **Linux-only**:

- `date -d "@$ts"` is GNU-specific (macOS needs `date -r`);
- `jq` is an undeclared dependency, installed by default nowhere;
- `/tmp`, `hostname -s`, and bash itself are not native on Windows.

Committing it would break the repo's own three-OS portability bar on two of three
targets. `~/.horus/` is machine-local and gitignored, so settings never travel
either — a new machine starts from nothing.

## Idea

Make the renderer a **Horus command**, which the Rules already name as the only
portable spelling: *"the `horus` console script is the only guaranteed spelling."*

```jsonc
// each account's settings.json — a tiny, portable pointer
"statusLine": { "type": "command", "command": "horus statusline" }
```

- **`horus/statusline.py`** — renders the rows from the statusline JSON in Python:
  no jq, no GNU date, no bash. Current layout (see `~/.claude/statusline.sh` on the
  owner's Linux box, 2026-07-17) is the reference:
  1. `user@host:cwd` (with `~` for `$HOME`) │ model
  2. `ctx` / `5h` / `7d` meters — bar + percent + `↻ reset` (5h as `%H:%M`, weekly as
     `%b %-d`)
  3. `⎇ branch` │ `PR #<n> <review_state>`
- **`horus statusline`** reads stdin, **records the usage reading in-process**, and
  prints the rows. This collapses the whole capture apparatus the bash script needs:
  no background job, no per-account throttle stamp, no `find -mmin` (see the bfs trap
  below). `horus usage record` stays for owners who keep their own script.
- **Provisioning writes the pointer.** `horus account --isolate` (or the
  `account-settings-sync` verb) puts `statusLine` into
  `~/.horus/accounts/<agent>-<alias>/settings.json`. Nothing writes account-level
  settings today — `native_hooks.py` only writes *project*-level `.claude/settings.json`.

## Acceptance

- A fresh install on any of the three OSes, plus account provisioning, yields the same
  status line with no hand-editing.
- `horus statusline` renders correctly given the documented payload, and degrades
  cleanly: no `rate_limits` (non-Pro/Max, or before a session's first API response)
  drops row 2; no git repo drops the branch; no PR drops that segment.
- It never corrupts the status line: any bad/absent input prints nothing and exits 0.
- The reading it records is served to `horus usage check` from cache, with
  `source=statusline`.
- Rendering is verified on all three OSes (per the release rule), including ANSI colour.

## Non-goals

- **Not a configurable widget.** Ship one good default. Add knobs (bar width, segment
  order) only if real use demands them — Horus owns the memory/planning plane, and a
  display surface invites customization requests forever. The owner's words when this
  work started: *"we don't need a fancy widget."*
- Not a Codex equivalent: Codex's status line is declarative (`status_line = [...]`
  built-in segments in `config.toml`), takes no stdin payload, and cannot be scripted —
  so there is nothing to render or capture there. Its rollout JSONL stays the source.
- Not ambient inheritance: per-account isolated dirs stay the invariant.

## Notes

- **Depends on / overlaps `account-settings-sync`**, which owns "one canonical settings
  block across isolated account dirs" and was born from the same 2026-07-17 incident (a
  statusLine in `~/.claude` never applied because sessions run under `claude-personal`).
  Decide whether provisioning writes the pointer directly, or whether that card's sync
  verb owns it — do not build two writers of account settings.
- Traps already paid for on the bash version, worth not re-learning:
  - the owner's `find` is **bfs**, which rejects `-newermt '-60 seconds'` and leaks part
    of its error into the substitution, so a throttle built on it fires at random
    (`-mmin -1` is the portable spelling). An in-process recorder needs no throttle at all.
  - `permission_mode` is **not** in the statusline payload (hooks only) — it is one of
    Claude Code's own footer badges, which render below the status line and cannot be
    relocated. Do not try to add it.
  - `rate_limits.*.resets_at` is **unix epoch seconds** here, while the OAuth `/usage`
    endpoint returns ISO strings.
- Reference: `horus usage record --help` and `usage_snapshot.snapshot_from_claude_statusline`
  already parse this payload; the renderer should reuse that, not re-parse.
