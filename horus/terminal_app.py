"""Dependency-light terminal control surface for tracked Horus projects."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from horus import config, frontmatter, registry, routines, terminal_sessions

InputFn = Callable[[str], str]


def run(*, input_fn: InputFn = input, output: TextIO | None = None) -> int:
    """Run the terminal application until the user quits or input closes."""
    if input_fn is input and output is None and sys.stdin.isatty() and sys.stdout.isatty():
        from horus import terminal_tui

        return terminal_tui.run()

    out = output or sys.stdout
    try:
        while True:
            projects = _projects()
            _home(projects, out)
            choice = _ask(input_fn, "Select project, [s] sessions, [q] quit: ")
            if choice is None or choice.lower() == "q":
                return 0
            if choice.lower() == "s":
                _sessions(input_fn, out)
                continue
            selected = _numbered(choice, len(projects))
            if selected is None:
                _line(out, "Invalid selection.")
                continue
            _project(projects[selected], input_fn, out)
    except KeyboardInterrupt:
        _line(out, "\nLeaving Horus.")
        return 130


def _projects() -> list[Path]:
    projects: list[Path] = []
    for raw in config.load_projects():
        root = Path(raw).resolve()
        if root.is_dir() and (root / ".horus").is_dir():
            projects.append(root)
    return projects


def _home(projects: list[Path], out: TextIO) -> None:
    running = [record for record in registry.Registry.default().all() if record.status == "running"]
    _line(out, "\nHORUS — terminal")
    _line(out, "=" * 48)
    if not projects:
        _line(out, "No tracked projects. Run `horus init` inside a project first.")
        return
    for index, root in enumerate(projects, 1):
        focus = _focus(root)
        next_action = _compact(focus.get("next_action") or focus.get("current_focus") or "No next action")
        count = sum(1 for record in running if Path(record.project).resolve() == root)
        session_label = f" · {count} live" if count else ""
        _line(out, f"{index:>2}. {root.name}{session_label}")
        _line(out, f"    {next_action}")


def _project(root: Path, input_fn: InputFn, out: TextIO) -> None:
    while True:
        focus = _focus(root)
        target = terminal_sessions.default_target()
        _line(out, f"\n{root.name}")
        _line(out, f"Next: {_compact(focus.get('next_action') or '(not set)', limit=100)}")
        _line(out, f"Launch target: {target} (automatic)")
        _line(out, "  1. Resume with Claude")
        _line(out, "  2. Fresh Claude session")
        _line(out, "  3. Resume with Codex")
        _line(out, "  4. Fresh Codex session")
        _line(out, "  5. Running sessions")
        choice = _ask(input_fn, "Select action, [b] back: ")
        if choice is None or choice.lower() == "b":
            return
        if choice == "5":
            _sessions(input_fn, out, project=root)
            continue
        action = {
            "1": ("claude", "resume"),
            "2": ("claude", "fresh"),
            "3": ("codex", "resume"),
            "4": ("codex", "fresh"),
        }.get(choice)
        if action is None:
            _line(out, "Invalid selection.")
            continue
        agent, mode = action
        account = _choose_account(agent, input_fn, out)
        if account is _CANCEL:
            continue
        prompt = routines.resume_prompt(root) if mode == "resume" else ""
        _line(out, f"Starting {agent} · {account or 'ambient'} · {mode} · {target} …")
        result = _launch(target=target, agent=agent, root=root, account=account, prompt=prompt)
        if result.ok:
            _line(out, f"Session {result.session_id[:8]} returned to Horus.")
        else:
            _line(out, f"Launch failed: {result.error}")


def _launch(*, target: str, agent: str, root: Path, account: str | None, prompt: str):
    kwargs = {"agent": agent, "project_dir": root, "account": account, "prompt": prompt}
    if target == terminal_sessions.TMUX:
        return terminal_sessions.launch_tmux(**kwargs)
    return terminal_sessions.run_attached(**kwargs)


def _sessions(input_fn: InputFn, out: TextIO, *, project: Path | None = None) -> None:
    store = registry.Registry.default()
    records = [record for record in store.all() if record.status == "running"]
    if project is not None:
        records = [record for record in records if Path(record.project).resolve() == project.resolve()]
    records.sort(key=lambda record: record.updated_at, reverse=True)
    _line(out, "\nRunning sessions")
    if not records:
        _line(out, "  None.")
        return
    for index, record in enumerate(records, 1):
        _line(
            out,
            f"{index:>2}. {record.agent} · {record.account or 'ambient'} · "
            f"{Path(record.project).name} · {terminal_sessions.access_label(record)} · "
            f"{record.launch_target} · {record.session_id[:8]}",
        )
    choice = _ask(input_fn, "Select session, [b] back: ")
    if choice is None or choice.lower() == "b":
        return
    selected = _numbered(choice, len(records))
    if selected is None:
        _line(out, "Invalid selection.")
        return
    record = records[selected]
    if not terminal_sessions.is_attachable(record):
        _line(out, "This live session remains in its original terminal and cannot be attached here.")
        return
    action = _ask(input_fn, "[a] attach, [x] close, [b] back: ")
    if action is None or action.lower() == "b":
        return
    if action.lower() == "a":
        error = terminal_sessions.attach_session(record.session_id, reg=store)
        _line(out, error or f"Detached from {record.session_id[:8]}.")
    elif action.lower() == "x":
        confirm = _ask(input_fn, f"Close {record.session_id[:8]}? [y/N]: ")
        if confirm and confirm.lower() == "y":
            error = terminal_sessions.stop_session(record.session_id, reg=store)
            _line(out, error or f"Closed {record.session_id[:8]}.")
    else:
        _line(out, "Invalid selection.")


class _Cancel:
    pass


_CANCEL = _Cancel()


def _choose_account(agent: str, input_fn: InputFn, out: TextIO) -> str | None | _Cancel:
    mapped = config.load_account_config_dirs() if agent == "claude" else config.load_account_codex_homes()
    choices: list[str | None] = [None, *sorted(mapped)]
    if len(choices) == 1:
        return None
    _line(out, "Accounts")
    for index, account in enumerate(choices, 1):
        _line(out, f"  {index}. {account or 'ambient'}")
    choice = _ask(input_fn, "Select account, [b] back: ")
    if choice is None or choice.lower() == "b":
        return _CANCEL
    selected = _numbered(choice, len(choices))
    if selected is None:
        _line(out, "Invalid account; launch cancelled.")
        return _CANCEL
    return choices[selected]


def _ask(input_fn: InputFn, prompt: str) -> str | None:
    try:
        return input_fn(prompt).strip()
    except EOFError:
        return None


def _numbered(value: str, count: int) -> int | None:
    try:
        index = int(value) - 1
    except ValueError:
        return None
    return index if 0 <= index < count else None


def _compact(value: str, *, limit: int = 76) -> str:
    one_line = " ".join(str(value).split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"


def _focus(root: Path) -> dict[str, str]:
    try:
        return frontmatter.resolve_focus(root)
    except (OSError, ValueError):
        return {"current_focus": "", "next_action": "Continuity could not be read"}


def _line(out: TextIO, value: str) -> None:
    print(value, file=out, flush=True)
