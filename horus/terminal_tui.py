"""Responsive full-screen terminal UI for tracked Horus projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, ScrollOffsets, Window
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.output import Output
from prompt_toolkit.styles import Style

from horus import config, frontmatter, registry, routines, terminal_sessions


@dataclass(frozen=True)
class _Launch:
    project: Path
    agent: str
    mode: str
    account: str | None


@dataclass(frozen=True)
class _Attach:
    session_id: str


@dataclass(frozen=True)
class _Stop:
    session_id: str


_Action = _Launch | _Attach | _Stop | str


class _BodyControl(FormattedTextControl):
    def __init__(self, text, on_scroll) -> None:
        super().__init__(text, focusable=True)
        self._on_scroll = on_scroll

    def mouse_handler(self, event: MouseEvent):
        if event.event_type == MouseEventType.SCROLL_UP:
            self._on_scroll(-1)
            return None
        if event.event_type == MouseEventType.SCROLL_DOWN:
            self._on_scroll(1)
            return None
        return super().mouse_handler(event)


class TerminalUI:
    """One application frame. Blocking agent actions run between frames."""

    def __init__(self, *, status: str = "", input: Input | None = None, output: Output | None = None) -> None:
        self.projects = _projects()
        self.screen = "projects"
        self.project: Path | None = None
        self.project_filter: Path | None = None
        self.pending_launch: tuple[str, str] | None = None
        self.selected_session: registry.SessionRecord | None = None
        self.items: list[tuple[str, object]] = []
        self.selected = 0
        self.status = status
        self.body = _BodyControl(self._body_text, self.move)
        self.keys = self._key_bindings()
        container = HSplit(
            [
                Window(FormattedTextControl(self._header_text), height=1, style="class:header"),
                Window(height=1, char="─", style="class:rule"),
                Window(
                    self.body,
                    scroll_offsets=ScrollOffsets(top=2, bottom=2),
                    allow_scroll_beyond_bottom=False,
                    wrap_lines=False,
                ),
                Window(FormattedTextControl(self._status_text), height=1, style="class:status"),
                Window(FormattedTextControl(self._footer_text), height=1, style="class:footer"),
            ]
        )
        self.application: Application[_Action] = Application(
            layout=Layout(container, focused_element=self.body),
            key_bindings=self.keys,
            full_screen=True,
            mouse_support=True,
            style=_STYLE,
            input=input,
            output=output,
        )
        self._refresh_items()

    def _key_bindings(self) -> KeyBindings:
        keys = KeyBindings()

        @keys.add("up")
        @keys.add("k")
        def _up(event) -> None:
            self.move(-1)

        @keys.add("down")
        @keys.add("j")
        def _down(event) -> None:
            self.move(1)

        @keys.add("pageup")
        def _page_up(event) -> None:
            self.move(-self._page_size())

        @keys.add("pagedown")
        def _page_down(event) -> None:
            self.move(self._page_size())

        @keys.add("enter")
        def _enter(event) -> None:
            self.activate()

        @keys.add("escape")
        @keys.add("left")
        @keys.add("b")
        def _back(event) -> None:
            self.back()

        @keys.add("s")
        def _sessions(event) -> None:
            self.project_filter = None
            self._show("sessions")

        @keys.add("q")
        def _quit(event) -> None:
            event.app.exit(result="quit")

        @keys.add("c-c")
        def _interrupt(event) -> None:
            event.app.exit(result="interrupt")

        return keys

    def _page_size(self) -> int:
        rows = self.application.output.get_size().rows
        return max(1, rows - 6)

    def move(self, amount: int) -> None:
        if not self.items:
            return
        self.selected = max(0, min(len(self.items) - 1, self.selected + amount))
        self.application.invalidate()

    def activate(self) -> None:
        if not self.items:
            return
        kind, value = self.items[self.selected]
        if self.screen == "projects" and kind == "project":
            self.project = value  # type: ignore[assignment]
            self._show("project")
        elif self.screen == "project" and kind == "launch":
            self.pending_launch = value  # type: ignore[assignment]
            accounts = self._accounts(self.pending_launch[0])
            if len(accounts) == 1:
                self._exit_launch(accounts[0])
            else:
                self._show("accounts")
        elif self.screen == "project" and kind == "sessions":
            self.project_filter = self.project
            self._show("sessions")
        elif self.screen == "sessions" and kind == "session":
            self.selected_session = value  # type: ignore[assignment]
            self._show("session")
        elif self.screen == "accounts" and kind == "account":
            self._exit_launch(value if isinstance(value, str) else None)
        elif self.screen == "session":
            if kind == "attach" and self.selected_session is not None:
                self.application.exit(result=_Attach(self.selected_session.session_id))
            elif kind == "close":
                self._show("confirm")
            elif kind == "back":
                self.back()
        elif self.screen == "confirm" and self.selected_session is not None:
            if kind == "yes":
                self.application.exit(result=_Stop(self.selected_session.session_id))
            else:
                self._show("session")

    def back(self) -> None:
        if self.screen == "projects":
            return
        if self.screen == "project":
            self.project = None
            self._show("projects")
        elif self.screen in {"accounts", "sessions"}:
            self._show("project" if self.project_filter or self.screen == "accounts" else "projects")
        elif self.screen == "session":
            self._show("sessions")
        elif self.screen == "confirm":
            self._show("session")

    def _show(self, screen: str) -> None:
        self.screen = screen
        self.selected = 0
        self.status = ""
        self._refresh_items()
        self.application.invalidate()

    def _refresh_items(self) -> None:
        if self.screen == "projects":
            self.items = [("project", project) for project in self.projects]
        elif self.screen == "project":
            self.items = [
                ("launch", ("claude", "resume")),
                ("launch", ("claude", "fresh")),
                ("launch", ("codex", "resume")),
                ("launch", ("codex", "fresh")),
                ("sessions", None),
            ]
        elif self.screen == "accounts" and self.pending_launch:
            self.items = [("account", account) for account in self._accounts(self.pending_launch[0])]
        elif self.screen == "sessions":
            records = [record for record in registry.Registry.default().all() if record.status == "running"]
            if self.project_filter is not None:
                records = [
                    record
                    for record in records
                    if Path(record.project).resolve() == self.project_filter.resolve()
                ]
            records.sort(key=lambda record: record.updated_at, reverse=True)
            self.items = [("session", record) for record in records]
        elif self.screen == "session":
            self.items = [("attach", None), ("close", None), ("back", None)]
        elif self.screen == "confirm":
            self.items = [("no", None), ("yes", None)]

    def _accounts(self, agent: str) -> list[str | None]:
        mapped = config.load_account_config_dirs() if agent == "claude" else config.load_account_codex_homes()
        return [None, *sorted(mapped)]

    def _exit_launch(self, account: str | None) -> None:
        if self.project is None or self.pending_launch is None:
            return
        agent, mode = self.pending_launch
        self.application.exit(result=_Launch(self.project, agent, mode, account))

    def _header_text(self) -> StyleAndTextTuples:
        title = {
            "projects": "HORUS · Projects",
            "project": f"HORUS · {self.project.name if self.project else 'Project'}",
            "accounts": "HORUS · Choose account",
            "sessions": "HORUS · Running sessions",
            "session": "HORUS · Session",
            "confirm": "HORUS · Close session?",
        }[self.screen]
        live = len([record for record in registry.Registry.default().all() if record.status == "running"])
        return [("class:header", f" {title}"), ("class:meta", f"   {live} live" if live else "")]

    def _body_text(self) -> StyleAndTextTuples:
        if not self.items:
            message = "No tracked projects. Run `horus init` first." if self.screen == "projects" else "No running sessions."
            return [("class:muted", f"\n  {message}\n")]
        lines: StyleAndTextTuples = []
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                lines.append(("[SetCursorPosition]", ""))
            if kind == "project":
                root = value
                live = self._project_live_count(root)
                suffix = f" · {live} live" if live else ""
                lines.append((style, f"\n {marker} {root.name}{suffix}\n"))
                lines.append(("class:muted", f"     {_compact(_next_action(root), 72)}\n"))
            elif kind == "launch":
                agent, mode = value
                label = f"{mode.title()} with {agent.title()}"
                lines.append((style, f"\n {marker} {label}\n"))
            elif kind == "sessions":
                lines.append((style, f"\n {marker} Running sessions\n"))
            elif kind == "account":
                lines.append((style, f"\n {marker} {value or 'ambient'}\n"))
            elif kind == "session":
                record = value
                lines.append(
                    (
                        style,
                        f"\n {marker} {record.agent} · {record.account or 'ambient'} · "
                        f"{Path(record.project).name}\n",
                    )
                )
                lines.append(("class:muted", f"     {record.launch_target} · {record.session_id[:8]}\n"))
            elif kind in {"attach", "close", "back"}:
                lines.append((style, f"\n {marker} {kind.title()}\n"))
            elif kind in {"yes", "no"}:
                lines.append((style, f"\n {marker} {'Close session' if kind == 'yes' else 'Keep session'}\n"))
        return lines

    def _project_live_count(self, root: Path) -> int:
        return sum(
            1
            for record in registry.Registry.default().all()
            if record.status == "running" and Path(record.project).resolve() == root.resolve()
        )

    def _status_text(self) -> StyleAndTextTuples:
        if self.status:
            return [("class:status", f" {self.status}")]
        if self.screen == "project" and self.project is not None:
            return [("class:status", f" Next: {_compact(_next_action(self.project), 72)}")]
        return [("class:status", "")]

    def _footer_text(self) -> StyleAndTextTuples:
        return [("class:footer", " ↑↓/swipe scroll   Enter open   Esc back   s sessions   q quit")]


_STYLE = Style.from_dict(
    {
        "header": "bold #f2f2f2 bg:#20242b",
        "meta": "#8ea4b8 bg:#20242b",
        "rule": "#4b5563",
        "item": "#d7dce2",
        "selected": "bold #ffffff bg:#245a73",
        "muted": "#8c98a5",
        "status": "#9fc4d7 bg:#17202a",
        "footer": "#aeb8c2 bg:#20242b",
    }
)


def run() -> int:
    """Run frames until quit, suspending the alternate screen for agent commands."""
    status = ""
    while True:
        ui = TerminalUI(status=status)
        result = ui.application.run()
        if result == "quit":
            return 0
        if result == "interrupt":
            return 130
        if isinstance(result, _Launch):
            target = terminal_sessions.default_target()
            prompt = routines.resume_prompt(result.project) if result.mode == "resume" else ""
            launched = _launch(
                target=target,
                agent=result.agent,
                root=result.project,
                account=result.account,
                prompt=prompt,
            )
            status = (
                f"Session {launched.session_id[:8]} returned to Horus."
                if launched.ok
                else f"Launch failed: {launched.error}"
            )
        elif isinstance(result, _Attach):
            error = terminal_sessions.attach_session(result.session_id)
            status = error or f"Detached from {result.session_id[:8]}."
        elif isinstance(result, _Stop):
            error = terminal_sessions.stop_session(result.session_id)
            status = error or f"Closed {result.session_id[:8]}."


def _projects() -> list[Path]:
    return [
        root
        for raw in config.load_projects()
        if (root := Path(raw).resolve()).is_dir() and (root / ".horus").is_dir()
    ]


def _next_action(root: Path) -> str:
    try:
        focus = frontmatter.resolve_focus(root)
    except (OSError, ValueError):
        return "Continuity could not be read"
    return str(focus.get("next_action") or focus.get("current_focus") or "No next action")


def _compact(value: str, limit: int) -> str:
    one_line = " ".join(value.split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"


def _launch(*, target: str, agent: str, root: Path, account: str | None, prompt: str):
    kwargs = {"agent": agent, "project_dir": root, "account": account, "prompt": prompt}
    if target == terminal_sessions.TMUX:
        return terminal_sessions.launch_tmux(**kwargs)
    return terminal_sessions.run_attached(**kwargs)
