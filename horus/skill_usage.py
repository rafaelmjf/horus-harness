"""Machine-local record of which bundled skills actually get invoked.

`skill-audit`'s verdicts (revise / demote / retire) rested entirely on the owner
remembering a run. With 21 bundled skills there was no signal at all for which are
ever loaded, so "this skill is ceremony" and "I have not happened to use it lately"
were indistinguishable.

The signal comes from the agent CLI's own `PreToolUse` event, matched on the `Skill`
tool — verified live 2026-08-02, and it fires without a session restart. PreToolUse
rather than PostToolUse because "was it invoked" needs no result, and because Horus
already installs PreToolUse hooks and none on PostToolUse.

Deliberately minimal, per the no-transcripts rule: a name, a project and a day. No
arguments, no prompt text, no result. Machine-local and never committed, like every
other Horus telemetry sink — a count is evidence about this owner's use, not a fact
about the project, so it must not travel in `.horus/`.

Append-only and failure-tolerant: a recorder that can break a tool call is worse than
no telemetry, so every entry point swallows its own errors and the hook command
carries the standard `|| exit 0` guard.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from horus import config

LOG_NAME = "skill-invocations.jsonl"
#: Keep the log bounded without a maintenance ritual. At one line per invocation this
#: is years of real use, and the read path only ever reports counts.
MAX_LINES = 20_000


def log_path() -> Path:
    return config.config_dir() / LOG_NAME


def record(skill: str, project: str | None = None, *, today: date | None = None) -> bool:
    """Append one invocation. Returns True when written; never raises.

    Called from a hook on the agent's critical path, so any failure — unwritable
    home, full disk, a schema the reader does not understand — must degrade to
    "no telemetry", never to a broken tool call.
    """
    skill = (skill or "").strip()
    if not skill:
        return False
    entry = {
        "skill": skill,
        "project": (project or "").strip() or None,
        "day": (today or date.today()).isoformat(),
    }
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError:
        return False
    _trim(path)
    return True


def _trim(path: Path) -> None:
    """Drop the oldest lines once the log exceeds MAX_LINES. Best-effort."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= MAX_LINES:
            return
        path.write_text("\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def _entries() -> list[dict]:
    try:
        raw = log_path().read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue  # a partial write is not a reason to lose the rest
        if isinstance(item, dict) and item.get("skill"):
            out.append(item)
    return out


def counts(*, since: str | None = None, project: str | None = None) -> Counter:
    """Invocations per skill name, newest-inclusive.

    ``since`` is an ISO day compared lexicographically — ISO dates sort correctly as
    strings, so this needs no date parsing and tolerates a malformed value by simply
    not matching it.
    """
    tally: Counter = Counter()
    for e in _entries():
        if since and str(e.get("day", "")) < since:
            continue
        if project and e.get("project") != project:
            continue
        tally[e["skill"]] += 1
    return tally


def summary(known: list[str], *, since: str | None = None) -> list[tuple[str, int]]:
    """(`skill`, count) for every KNOWN skill, most-used first, zeroes included.

    The zeroes are the point — a skill absent from the log is the case `skill-audit`
    most needs to see, so this reports the full roster rather than only what fired.
    """
    tally = counts(since=since)
    return sorted(((name, tally.get(name, 0)) for name in known), key=lambda kv: (-kv[1], kv[0]))
