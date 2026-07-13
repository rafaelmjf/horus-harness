"""Launch a tracked brainstorm session — shared by the CLI and the dashboard.

A brainstorm is an ordinary tracked interactive session (the same launch/registry
plumbing as ``horus open``) seeded with a *scoped-context* prompt: the project's
PRD vision/backlog/rules plus a topic, and an output contract that writes an
implementation-plan draft to ``.horus/temp/brainstorm-<slug>.md`` and never edits
PRD.md. ``horus brainstorm`` and the dashboard's Ideas/Brainstorm card both call
:func:`start_brainstorm`, so the CLI and the web share exactly one code path.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from horus import frontmatter, launch, registry, templates

_MAX_SLUG = 60
_TEMP_DIRNAME = "temp"


def slugify(topic: str) -> str:
    """Filesystem-safe slug for a brainstorm topic (bounded length)."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    slug = slug[:_MAX_SLUG].strip("-")
    return slug or "session"


def note_relpath(topic: str) -> str:
    """Repo-relative path of the brainstorm output note for ``topic``."""
    return f".horus/{_TEMP_DIRNAME}/brainstorm-{slugify(topic)}.md"


def _section(body: str, heading: str) -> str:
    """Body of a top-level (``## ``) markdown section, until the next ``## `` heading.

    Heading match is prefix-tolerant so ``## Rules (load-bearing)`` matches
    ``Rules`` — the PRD template annotates a couple of its section titles.
    """
    lines = body.splitlines()
    target = heading.strip().lower()
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("## "):
            continue
        title = stripped[3:].strip().lower()
        if title == target or title.startswith(target + " "):
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def build_prompt(project_dir: Path | str, topic: str) -> str:
    """Seed prompt: minimal PRD context (vision/backlog/rules) + topic + contract.

    Reads only ``.horus/PRD.md`` — never sessions or the archive. On a project with
    no PRD (six-lane / uninitialized), the sections degrade to explicit "(not
    recorded)" markers rather than pulling in other lanes.
    """
    root = Path(project_dir).resolve()
    doc = frontmatter.parse_file(frontmatter.prd_path(root))
    body = doc.body if doc is not None else ""
    return templates.brainstorm_prompt(
        project=root.name,
        topic=topic.strip(),
        vision=_section(body, "Vision"),
        backlog=_section(body, "Backlog"),
        rules=_section(body, "Rules"),
        note_path=note_relpath(topic),
    )


def _prepare(project_dir: Path | str, topic: str) -> tuple[Path, str]:
    """Validate the topic, build the scoped prompt, and ensure the note's parent
    dir exists so the session can drop the draft. Returns (root, prompt)."""
    topic = topic.strip()
    if not topic:
        raise ValueError("a brainstorm needs a non-empty topic")
    root = Path(project_dir).resolve()
    prompt = build_prompt(root, topic)
    (root / ".horus" / _TEMP_DIRNAME).mkdir(parents=True, exist_ok=True)
    return root, prompt


def start_brainstorm_app(
    *,
    project_dir: Path | str,
    topic: str,
    agent: str = "claude",
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    host=None,
) -> tuple[str, str]:
    """Start the brainstorm as an in-app PTY terminal (headless-safe); return
    ``(term_id, note_path)``.

    Same scoped prompt and output contract as :func:`start_brainstorm`, but the
    session runs in the dashboard's session-host instead of a native OS window —
    the only launch shape that works on a hosted/headless dashboard.
    """
    root, prompt = _prepare(project_dir, topic)
    if host is None:  # late import: brainstorm is also used by the windowless CLI
        from horus import pty_host

        host = pty_host.host
    term_id = host.start(
        agent=agent, project_dir=root, account=account, posture=posture,
        model=model, prompt=prompt, title=f"{root.name} · brainstorm", managed=True,
    )
    return term_id, note_relpath(topic)


@dataclass
class BrainstormResult:
    """Outcome of starting a brainstorm: the launch result plus where the draft lands."""

    launch: launch.LaunchResult
    topic: str
    slug: str
    note_path: str  # repo-relative

    @property
    def ok(self) -> bool:
        return self.launch.ok


def start_brainstorm(
    *,
    project_dir: Path | str,
    topic: str,
    agent: str = "claude",
    account: str | None = None,
    posture: str = "default",
    model: str | None = None,
    reg: registry.Registry | None = None,
    launch_fn: Callable[..., launch.LaunchResult] = launch.launch_interactive,
) -> BrainstormResult:
    """Launch a tracked brainstorm session seeded with the scoped-context prompt.

    Raises ``ValueError`` on an empty topic. Otherwise returns a
    :class:`BrainstormResult` wrapping the (possibly failed) launch — the same
    return-don't-raise posture as :func:`launch.launch_interactive`.
    """
    root, prompt = _prepare(project_dir, topic)
    topic = topic.strip()

    result = launch_fn(
        agent=agent,
        project_dir=root,
        account=account,
        posture=posture,
        model=model,
        prompt=prompt,
        reg=reg,
    )
    return BrainstormResult(
        launch=result,
        topic=topic,
        slug=slugify(topic),
        note_path=note_relpath(topic),
    )


__all__ = [
    "BrainstormResult",
    "build_prompt",
    "note_relpath",
    "slugify",
    "start_brainstorm",
    "start_brainstorm_app",
]
