"""Responsive full-screen terminal UI for tracked Horus projects."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    FormattedTextControl,
    HSplit,
    Layout,
    ScrollOffsets,
    Window,
)
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.output import Output
from prompt_toolkit.styles import Style

from horus import (
    backlog,
    backlog_migrate,
    capabilities,
    claude_usage,
    closure,
    codex_usage,
    config,
    frontmatter,
    registry,
    routines,
    terminal_sessions,
    usage_snapshot,
)


@dataclass(frozen=True)
class LaunchAccount:
    agent: str
    alias: str
    account: str | None


@dataclass(frozen=True)
class _Launch:
    project: Path
    agent: str
    mode: str
    account: str | None
    card: backlog.Card | None = None


@dataclass(frozen=True)
class _Attach:
    session_id: str


@dataclass(frozen=True)
class _Stop:
    session_id: str


@dataclass(frozen=True)
class _EditCard:
    project: Path
    card: backlog.Card
    review: bool = False


_Action = _Launch | _Attach | _Stop | _EditCard | str

# Labels for the home-level Defaults screen's one setting: the permission
# posture new TUI launches (fresh/resume/card-resume) start with, until changed
# here. `config.LAUNCH_POSTURE_CHOICES` is the source of truth for the values.
_POSTURE_LABELS: dict[str, str] = {
    "plan": "Plan — think/plan only, no edits or commands",
    "read-only": "Read-only — may inspect, never write or run side-effecting tools",
    "default": "Default — prompt for sensitive actions",
    "auto-edit": "Auto-edit — auto-accept file edits, still gate other actions",
    "full-auto": "Full-auto — bypass permissions (dangerous; unattended)",
}


class _BodyControl(FormattedTextControl):
    def __init__(self, text, on_scroll, *, invert_mouse_scroll: bool) -> None:
        super().__init__(text, focusable=True)
        self._on_scroll = on_scroll
        self._invert_mouse_scroll = invert_mouse_scroll

    def mouse_handler(self, event: MouseEvent):
        if event.event_type == MouseEventType.SCROLL_UP:
            self._on_scroll(1 if self._invert_mouse_scroll else -1)
            return None
        if event.event_type == MouseEventType.SCROLL_DOWN:
            self._on_scroll(-1 if self._invert_mouse_scroll else 1)
            return None
        return super().mouse_handler(event)


class TerminalUI:
    """One application frame. Blocking agent actions run between frames."""

    def __init__(
        self,
        *,
        status: str = "",
        input: Input | None = None,
        output: Output | None = None,
        invert_mouse_scroll: bool | None = None,
    ) -> None:
        self.projects = _projects()
        self.accounts = _launch_accounts()
        self.account_usage = _account_usage(self.accounts)
        self.project_cards = {project: _open_cards(project) for project in self.projects}
        self.project_metrics = {
            project: _backlog_metrics(project, self.project_cards[project]) for project in self.projects
        }
        self.running = [record for record in registry.Registry.default().all() if record.status == "running"]
        self.screen = "projects"
        self.project: Path | None = None
        self.project_filter: Path | None = None
        self.pending_mode: str | None = None
        self.pending_card: backlog.Card | None = None
        self.card: backlog.Card | None = None
        self.card_scroll = 0
        self.project_focus: dict[str, str] = {}
        self.capabilities_record: dict | None = None
        self.capabilities_error = ""
        self.selected_session: registry.SessionRecord | None = None
        self.items: list[tuple[str, object]] = []
        self.selected = 0
        self.status = status
        if invert_mouse_scroll is None:
            invert_mouse_scroll = _invert_mobile_scroll()
        self.invert_mobile_scroll = invert_mouse_scroll
        self.body = _BodyControl(self._body_text, self.scroll, invert_mouse_scroll=invert_mouse_scroll)
        self.keys = self._key_bindings()
        self.body_window = Window(
            self.body,
            scroll_offsets=ScrollOffsets(top=2, bottom=2),
            allow_scroll_beyond_bottom=False,
            wrap_lines=True,
        )
        container = HSplit(
            [
                Window(FormattedTextControl(self._header_text), height=1, style="class:header"),
                Window(height=1, char="─", style="class:rule"),
                self.body_window,
                ConditionalContainer(
                    Window(FormattedTextControl(self._status_text), height=1, style="class:status"),
                    filter=Condition(lambda: bool(self.status)),
                ),
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

        @keys.add("k")
        def _up(event) -> None:
            self.scroll(-1)

        @keys.add("j")
        def _down(event) -> None:
            self.scroll(1)

        @keys.add("up")
        def _terminal_up(event) -> None:
            self.scroll(1 if self.invert_mobile_scroll else -1)

        @keys.add("down")
        def _terminal_down(event) -> None:
            self.scroll(-1 if self.invert_mobile_scroll else 1)

        @keys.add("pageup")
        def _page_up(event) -> None:
            self.scroll(-self._page_size())

        @keys.add("pagedown")
        def _page_down(event) -> None:
            self.scroll(self._page_size())

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

        @keys.add("d")
        def _defaults(event) -> None:
            self._show("settings")

        @keys.add("u")
        def _refresh_usage(event) -> None:
            self.refresh_account_usage()

        on_card = Condition(lambda: self.screen == "card" and self.card is not None)

        @keys.add("e", filter=on_card)
        def _edit_card(event) -> None:
            self._exit_edit(review=False)

        @keys.add("r", filter=on_card)
        def _review_card(event) -> None:
            self._exit_edit(review=True)

        @keys.add("q")
        def _quit(event) -> None:
            event.app.exit(result="quit")

        @keys.add("c-c")
        def _interrupt(event) -> None:
            event.app.exit(result="interrupt")

        return keys

    def refresh_account_usage(self) -> None:
        """Re-read account aliases and their cache-only usage in the current frame."""
        selected = self.selected
        self.accounts = _launch_accounts()
        self.account_usage = _account_usage(self.accounts)
        if self.screen == "accounts":
            self._refresh_items()
            self.selected = min(selected, max(0, len(self.items) - 1))
        self.status = "Account usage refreshed from cache."
        self.application.invalidate()

    def _page_size(self) -> int:
        rows = self.application.output.get_size().rows
        fixed_rows = 4 if self.status else 3
        return max(1, rows - fixed_rows)

    def move(self, amount: int) -> None:
        if not self.items:
            return
        self.selected = max(0, min(len(self.items) - 1, self.selected + amount))
        if self.screen == "projects" and self.selected == 0:
            # The account KPI rail sits above the first selectable project. Once
            # prompt_toolkit has scrolled down, merely returning the cursor to the
            # first project keeps that rail outside the viewport. Explicitly return
            # home to the top so wheel/arrow navigation is reversible.
            self.body_window.vertical_scroll = 0
        self.application.invalidate()

    def scroll(self, amount: int) -> None:
        if self.screen == "card":
            lines = self._card_lines()
            self.card_scroll = max(0, min(len(lines) - 1, self.card_scroll + amount))
            self.application.invalidate()
            return
        self.move(amount)

    def activate(self) -> None:
        if not self.items:
            return
        kind, value = self.items[self.selected]
        if self.screen == "projects" and kind == "project":
            self.project = value  # type: ignore[assignment]
            self._load_project_focus()
            self._load_project_capabilities()
            self._show("project")
        elif self.screen == "project" and kind == "mode":
            self.pending_mode = str(value)
            self.pending_card = None
            self._show("accounts")
        elif self.screen == "project" and kind == "backlog":
            self._show("backlog")
        elif self.screen == "project" and kind == "capabilities":
            self._show("capabilities")
        elif self.screen == "backlog" and kind == "card":
            self.card = value  # type: ignore[assignment]
            self.card_scroll = 4
            self._show("card")
        elif self.screen == "card" and kind == "card_resume":
            self.pending_mode = "resume"
            self.pending_card = self.card
            self._show("accounts")
        elif self.screen == "sessions" and kind == "session":
            self.selected_session = value  # type: ignore[assignment]
            self._show("session")
        elif self.screen == "accounts" and kind == "account":
            if isinstance(value, LaunchAccount):
                self._exit_launch(value)
        elif self.screen == "settings" and kind == "posture":
            posture = str(value)
            config.set_launch_default_posture(posture)
            self._refresh_items()
            self.status = f"Default launch posture set to {posture}."
            self.application.invalidate()
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
            self.project_focus = {}
            self._show("projects")
        elif self.screen == "accounts":
            self._show("card" if self.pending_card is not None else "project")
        elif self.screen == "backlog":
            self._show("project")
        elif self.screen == "capabilities":
            self._show("project")
        elif self.screen == "card":
            self._show("backlog")
        elif self.screen == "sessions":
            self._show("project" if self.project_filter else "projects")
        elif self.screen == "session":
            self._show("sessions")
        elif self.screen == "confirm":
            self._show("session")
        elif self.screen == "settings":
            self._show("projects")

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
                ("mode", "resume"),
                ("mode", "fresh"),
                ("backlog", None),
                ("capabilities", None),
            ]
        elif self.screen == "accounts":
            self.items = [("account", account) for account in self.accounts]
        elif self.screen == "backlog":
            self.items = [("card", card) for card in self.project_cards.get(self.project, [])]
        elif self.screen == "capabilities":
            project = (self.capabilities_record or {}).get("project", {})
            records = project.get("capabilities", []) if isinstance(project, dict) else []
            self.items = [
                ("capability", record)
                for record in records
                if isinstance(record, dict) and isinstance(record.get("text"), str)
            ]
        elif self.screen == "card":
            self.items = [("card_resume", self.card)] if self.card is not None else []
        elif self.screen == "sessions":
            records = list(self.running)
            if self.project_filter is not None:
                records = [
                    record
                    for record in records
                    if Path(record.project).resolve() == self.project_filter.resolve()
                ]
            records.sort(key=lambda record: record.updated_at, reverse=True)
            self.items = [("session", record) for record in records]
        elif self.screen == "session":
            if self.selected_session is not None and terminal_sessions.is_attachable(self.selected_session):
                self.items = [("attach", None), ("close", None), ("back", None)]
            else:
                self.items = [("unavailable", None), ("back", None)]
        elif self.screen == "confirm":
            self.items = [("no", None), ("yes", None)]
        elif self.screen == "settings":
            current = config.load_launch_defaults()["posture"]
            self.items = [("posture", choice) for choice in config.LAUNCH_POSTURE_CHOICES]
            self.selected = config.LAUNCH_POSTURE_CHOICES.index(current)

    def _exit_edit(self, *, review: bool) -> None:
        if self.project is None or self.card is None:
            return
        self.application.exit(result=_EditCard(self.project, self.card, review))

    def _exit_launch(self, account: LaunchAccount) -> None:
        if self.project is None or self.pending_mode is None:
            return
        self.application.exit(
            result=_Launch(
                self.project,
                account.agent,
                self.pending_mode,
                account.account,
                self.pending_card,
            )
        )

    def _header_text(self) -> StyleAndTextTuples:
        title = {
            "projects": "HORUS · Projects",
            "project": f"HORUS · {self.project.name if self.project else 'Project'}",
            "accounts": f"HORUS · {self.pending_mode.title() if self.pending_mode else 'Choose'} account",
            "backlog": f"HORUS · {self.project.name if self.project else 'Project'} backlog",
            "capabilities": f"HORUS · {self.project.name if self.project else 'Project'} capabilities",
            "card": "HORUS · Backlog card",
            "sessions": "HORUS · Running sessions",
            "session": "HORUS · Session",
            "confirm": "HORUS · Close session?",
            "settings": "HORUS · Defaults",
        }[self.screen]
        live = len(self.running)
        return [("class:header", f" {title}"), ("class:meta", f"   {live} live" if live else "")]

    def _body_text(self) -> StyleAndTextTuples:
        if self.screen == "card":
            return self._card_body_text()
        if self.screen == "capabilities":
            return self._capabilities_body_text()
        if not self.items:
            if self.screen == "projects":
                message = "No tracked projects. Run `horus init` first."
            elif self.screen == "backlog":
                message = "No open backlog cards."
            elif self.screen == "accounts":
                message = "No agent accounts detected."
            else:
                message = "No running sessions."
            return [("class:muted", f"\n  {message}\n")]
        if self.screen == "projects" and self.application.output.get_size().columns >= 96:
            return self._wide_home_text(self.application.output.get_size().columns)
        lines: StyleAndTextTuples = []
        if self.screen == "projects":
            lines.extend(self._account_summary_text())
        elif self.screen == "project":
            current_focus = self.project_focus.get("current_focus", "")
            next_action = self.project_focus.get("next_action", "")
            if current_focus:
                lines.append(("class:section", "\n  Current focus\n"))
                lines.append(("class:muted", f"    {current_focus}\n"))
            if next_action:
                lines.append(("class:section", "\n  Next action\n"))
                lines.append(("class:muted", f"    {next_action}\n"))
            project = (self.capabilities_record or {}).get("project", {})
            vision = project.get("vision") if isinstance(project, dict) else None
            if isinstance(vision, str) and vision:
                lines.append(("class:muted", f"\n  {vision}\n"))
            elif self.capabilities_error:
                lines.append(("class:muted", f"\n  Capabilities unavailable: {self.capabilities_error}\n"))
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                lines.append(("[SetCursorPosition]", ""))
            if kind == "project":
                root = value
                sessions = self._project_sessions(root)
                suffix = f" · {len(sessions)} open session{'s' if len(sessions) != 1 else ''}" if sessions else ""
                lines.append((style, f"\n {marker} {root.name}{suffix}\n"))
                if sessions:
                    session_labels = ", ".join(_session_label(record) for record in sessions)
                    lines.append(("class:session", f"     {session_labels}\n"))
                card_count, bug_count = self.project_metrics.get(root, (0, 0))
                lines.append(("class:muted", f"     backlog {card_count} · bugs {bug_count}\n"))
            elif kind == "mode":
                label = str(value).title()
                detail = (
                    "Continue from project continuity"
                    if value == "resume"
                    else "Start without a continuity prompt"
                )
                lines.append((style, f"\n {marker} {label}\n"))
                lines.append(("class:muted", f"     {detail}\n"))
            elif kind == "backlog":
                card_count, bug_count = self.project_metrics.get(self.project, (0, 0))
                lines.append((style, f"\n {marker} Backlog\n"))
                lines.append(("class:muted", f"     {card_count} cards · {bug_count} bugs\n"))
            elif kind == "capabilities":
                project = (self.capabilities_record or {}).get("project", {})
                records = project.get("capabilities", []) if isinstance(project, dict) else []
                count = len(records) if isinstance(records, list) else 0
                lines.append((style, f"\n {marker} Capabilities\n"))
                detail = self.capabilities_error or f"{count} shipped capabilities"
                lines.append(("class:muted", f"     {detail}\n"))
            elif kind == "account":
                account = value
                lines.append((style, f"\n {marker} {account.agent.title()} {account.alias}\n"))
                for usage_line in _usage_lines(self.account_usage.get((account.agent, account.alias))):
                    lines.append(("class:muted", f"     {usage_line}\n"))
            elif kind == "card":
                card = value
                status = " · claimed" if card.status == "claimed" else ""
                lines.append((style, f"\n {marker} [{card.type}{status}] {card.title}\n"))
                if card.priority:
                    lines.append(("class:muted", f"     priority {card.priority}\n"))
            elif kind == "session":
                record = value
                lines.append(
                    (
                        style,
                        f"\n {marker} {record.agent} · {_session_account_alias(record)} · "
                        f"{Path(record.project).name}\n",
                    )
                )
                lines.append(
                    (
                        "class:muted",
                        f"     {terminal_sessions.access_label(record)} · "
                        f"{record.launch_target} · {record.session_id[:8]}\n",
                    )
                )
            elif kind in {"attach", "close", "back"}:
                lines.append((style, f"\n {marker} {kind.title()}\n"))
            elif kind == "unavailable":
                lines.append(("class:muted", "\n   This live session remains in its original terminal.\n"))
            elif kind in {"yes", "no"}:
                lines.append((style, f"\n {marker} {'Close session' if kind == 'yes' else 'Keep session'}\n"))
            elif kind == "posture":
                posture = str(value)
                current = config.load_launch_defaults()["posture"]
                active = "current" if posture == current else "      "
                lines.append((style, f"\n {marker} [{active}] {posture}\n"))
                lines.append(("class:muted", f"     {_POSTURE_LABELS.get(posture, '')}\n"))
        return lines

    def _wide_home_text(self, width: int) -> StyleAndTextTuples:
        """Render the home cockpit as responsive columns on wide terminals."""
        fragments: StyleAndTextTuples = [("class:section", "\n Accounts\n")]
        account_blocks = []
        for account in self.accounts:
            usage = _usage_lines(self.account_usage.get((account.agent, account.alias)))
            account_blocks.append(
                [("class:account", f" {account.agent.title()} {account.alias}")]
                + [("class:muted", f" {line}") for line in usage]
            )
        if account_blocks:
            account_columns = min(3, max(1, width // 40), len(account_blocks))
            account_width = max(1, (width - (account_columns - 1) * 2) // account_columns)
            for start in range(0, len(account_blocks), account_columns):
                blocks = account_blocks[start : start + account_columns]
                for line_index in range(max(len(block) for block in blocks)):
                    for column, block in enumerate(blocks):
                        style, text = block[line_index] if line_index < len(block) else ("", "")
                        fragments.append((style, _fit_cell(text, account_width)))
                        if column < len(blocks) - 1:
                            fragments.append(("class:muted", "  "))
                    fragments.append(("", "\n"))
                fragments.append(("", "\n"))
        else:
            fragments.append(("class:muted", " No agent accounts detected.\n\n"))

        fragments.append(("class:section", " Projects\n"))
        project_columns = 2
        project_width = max(1, (width - 2) // project_columns)
        for start in range(0, len(self.items), project_columns):
            blocks: list[tuple[int, list[tuple[str, str]]]] = []
            for index in range(start, min(start + project_columns, len(self.items))):
                _, root = self.items[index]
                sessions = self._project_sessions(root)  # type: ignore[arg-type]
                suffix = (
                    f" · {len(sessions)} open session{'s' if len(sessions) != 1 else ''}"
                    if sessions
                    else ""
                )
                marker = ">" if index == self.selected else " "
                session_labels = ", ".join(_session_label(record) for record in sessions)
                card_count, bug_count = self.project_metrics.get(root, (0, 0))  # type: ignore[arg-type]
                blocks.append(
                    (
                        index,
                        [
                            ("class:selected" if index == self.selected else "class:item", f" {marker} {root.name}{suffix}"),
                            ("class:session", f"   {session_labels}" if session_labels else ""),
                            ("class:muted", f"   backlog {card_count} · bugs {bug_count}"),
                        ],
                    )
                )
            for line_index in range(3):
                for column, (index, block) in enumerate(blocks):
                    if line_index == 0 and index == self.selected:
                        fragments.append(("[SetCursorPosition]", ""))
                    style, text = block[line_index]
                    fragments.append((style, _fit_cell(text, project_width)))
                    if column < len(blocks) - 1:
                        fragments.append(("class:muted", "  "))
                fragments.append(("", "\n"))
            fragments.append(("", "\n"))
        return fragments

    def _account_summary_text(self) -> StyleAndTextTuples:
        if not self.accounts:
            return []
        lines: StyleAndTextTuples = [("class:section", "\n Accounts\n")]
        for account in self.accounts:
            usage = self.account_usage.get((account.agent, account.alias))
            summary = _usage_lines(usage)
            lines.append(("class:account", f"  {account.agent.title()} {account.alias}\n"))
            for detail in summary:
                lines.append(("class:muted", f"    {detail}\n"))
        lines.append(("", "\n Projects\n"))
        return lines

    def _project_sessions(self, root: Path) -> list[registry.SessionRecord]:
        return [record for record in self.running if Path(record.project).resolve() == root.resolve()]

    def _card_lines(self) -> list[str]:
        if self.card is None:
            return ["", "Backlog card unavailable."]
        try:
            body = frontmatter.parse(self.card.path.read_text(encoding="utf-8")).body
        except (OSError, ValueError):
            body = "Card description could not be read."
        description = body.splitlines()
        for index, line in enumerate(description):
            if line.strip():
                if line.lstrip().startswith("# "):
                    description.pop(index)
                break
        return [
            "",
            f"[{self.card.type} · priority {self.card.priority or '-'}]",
            self.card.title,
            "",
            "> Resume this card",
            "",
            *description,
            "",
        ]

    def _card_body_text(self) -> StyleAndTextTuples:
        fragments: StyleAndTextTuples = []
        for index, line in enumerate(self._card_lines()):
            if index == self.card_scroll:
                fragments.append(("[SetCursorPosition]", ""))
            if index == 1:
                style = "class:meta"
            elif index == 2:
                style = "class:card-title"
            elif index == 4:
                style = "class:selected"
            else:
                style = "class:item"
            fragments.append((style, f" {line}\n"))
        return fragments

    def _load_project_capabilities(self) -> None:
        """Regenerate and retain the one canonical per-project capability record."""
        self.capabilities_record = None
        self.capabilities_error = ""
        if self.project is None:
            return
        try:
            record = json.loads(capabilities.generate_project(self.project.as_posix()))
            if not isinstance(record, dict) or not isinstance(record.get("project"), dict):
                raise ValueError("invalid generated record")
            self.capabilities_record = record
        except (OSError, ValueError) as exc:
            self.capabilities_error = str(exc)

    def _load_project_focus(self) -> None:
        """Retain the canonical PRD-first focus record for the project frame."""
        self.project_focus = {}
        if self.project is None:
            return
        try:
            self.project_focus = frontmatter.resolve_focus(self.project)
        except OSError:
            return

    def _capabilities_body_text(self) -> StyleAndTextTuples:
        if self.capabilities_error:
            return [("class:muted", f"\n  Capabilities unavailable: {self.capabilities_error}\n")]
        record = self.capabilities_record or {}
        generated_at = record.get("generated_at")
        freshness = _capability_freshness(self.project, generated_at)
        fragments: StyleAndTextTuples = [
            ("class:muted", f"\n  {freshness}\n"),
            ("class:section", "\n  Shipped capabilities\n"),
        ]
        if not self.items:
            fragments.append(("class:muted", "\n  No shipped capabilities recorded.\n"))
            return fragments
        for index, (_kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                fragments.append(("[SetCursorPosition]", ""))
            text = str(value.get("text", ""))
            fragments.append((style, f"\n {marker} {text}\n"))
            commands = value.get("related_commands", [])
            if isinstance(commands, list) and commands:
                fragments.append(("class:muted", f"     commands: {', '.join(map(str, commands))}\n"))
        return fragments

    def _status_text(self) -> StyleAndTextTuples:
        if self.status:
            return [("class:status", f" {self.status}")]
        return [("class:status", "")]

    def _footer_text(self) -> StyleAndTextTuples:
        narrow = self.application.output.get_size().columns < 64
        if self.screen == "card":
            text = (
                " ↑↓ read · Enter resume · e/r edit · Esc back"
                if narrow
                else " ↑↓/swipe read   Enter resume   e edit   r review   Esc back"
            )
            return [("class:footer", text)]
        if self.screen == "sessions":
            text = (
                " Enter attach · Esc back · q quit"
                if narrow
                else " Enter attach   Ctrl-b d returns   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "session" and (
            self.selected_session is None or not terminal_sessions.is_attachable(self.selected_session)
        ):
            text = " Esc back · q quit" if narrow else " Original terminal only   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen == "settings":
            text = (
                " ↑↓ select · Enter save · Esc back"
                if narrow
                else " ↑↓ select   Enter save   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "capabilities":
            text = " ↑↓ scroll · Esc back" if narrow else " ↑↓/swipe scroll   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen in {"projects", "accounts"}:
            text = (
                " ↑↓ · Enter · u refresh · q"
                if narrow
                else " ↑↓/swipe · Enter · u refresh · Esc · s sessions · d defaults · q quit"
            )
            return [("class:footer", text)]
        text = (
            " ↑↓ scroll · Enter · s sessions · d defaults · q"
            if narrow
            else " ↑↓/swipe scroll   Enter open   Esc back   s sessions   d defaults   q quit"
        )
        return [("class:footer", text)]


_STYLE = Style.from_dict(
    {
        "header": "bold #f2f2f2 bg:#20242b",
        "meta": "#8ea4b8 bg:#20242b",
        "rule": "#4b5563",
        "item": "#d7dce2",
        "selected": "bold #ffffff bg:#245a73",
        "muted": "#8c98a5",
        "section": "bold #b8c7d1",
        "account": "#d7dce2",
        "session": "#9fc4d7",
        "card-title": "bold #ffffff",
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
            if result.card is not None:
                prompt = _card_prompt(result.project, result.card)
            else:
                prompt = routines.resume_prompt(result.project) if result.mode == "resume" else ""
            launched = _launch(
                target=target,
                agent=result.agent,
                root=result.project,
                account=result.account,
                prompt=prompt,
                posture=config.load_launch_defaults()["posture"],
            )
            status = (
                f"Session {launched.session_id[:8]} returned to Horus."
                if launched.ok
                else f"Launch failed: {launched.error}"
            )
        elif isinstance(result, _EditCard):
            status = _edit_card(result.project, result.card, review=result.review)
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


_PRIORITY_RANK = {"now": 0, "next": 1, "high": 2, "medium": 3, "low": 4, "later": 5, "deferred": 6}


def _open_cards(root: Path) -> list[backlog.Card]:
    try:
        cards = [card for card in backlog.load_cards(root) if card.status not in {"done", "shipped"}]
    except (OSError, ValueError):
        return []
    return sorted(cards, key=lambda card: (_PRIORITY_RANK.get(card.priority, 99), card.title.casefold()))


def _backlog_metrics(root: Path, cards: list[backlog.Card]) -> tuple[int, int]:
    if backlog.backlog_dir(root).is_dir():
        return len(cards), sum(card.type == "bug" for card in cards)
    inline_count = backlog_migrate.inline_backlog_item_count(root)
    return (inline_count or 0, 0)


def _ambient_alias(agent: str) -> str | None:
    if agent == "claude":
        return config.alias_for(claude_usage.current_account())
    if agent == "codex":
        return config.alias_for(codex_usage.current_account())
    return None


def _launch_accounts() -> list[LaunchAccount]:
    result: list[LaunchAccount] = []
    for agent, mapped in (
        ("claude", config.load_account_config_dirs()),
        ("codex", config.load_account_codex_homes()),
    ):
        ambient = _ambient_alias(agent)
        if ambient and ambient not in mapped:
            result.append(LaunchAccount(agent, ambient, None))
        result.extend(LaunchAccount(agent, alias, alias) for alias in sorted(mapped))
    return result


def _account_usage(accounts: list[LaunchAccount]) -> dict[tuple[str, str], usage_snapshot.UsageSnapshot | None]:
    return {
        (account.agent, account.alias): (
            snapshot.without_expired_windows() if (snapshot := usage_snapshot.read_cache_only(
                account.agent, account.alias
            )) else None
        )
        for account in accounts
    }


def _percent(value: float | None) -> str:
    return "--" if value is None else f"{value:.0f}%"


def _usage_lines(snapshot: usage_snapshot.UsageSnapshot | None) -> list[str]:
    if snapshot is None:
        return ["5h --", "weekly --"]

    def window(label: str, percent: float | None, resets_at: str | None) -> str:
        text = f"{label} {_percent(percent)}"
        return f"{text}, resets {resets_at}" if resets_at else text

    return [
        window("5h", snapshot.percent, snapshot.resets_at),
        window("weekly", snapshot.weekly_percent, snapshot.weekly_resets_at),
    ]


def _session_account_alias(record: registry.SessionRecord) -> str:
    return record.account or _ambient_alias(record.agent) or "ambient"


def _session_label(record: registry.SessionRecord) -> str:
    return (
        f"{record.agent} {_session_account_alias(record)} · "
        f"{terminal_sessions.access_label(record)}"
    )


def _fit_cell(text: str, width: int) -> str:
    if len(text) > width:
        text = f"{text[: max(0, width - 1)]}…"
    return text.ljust(width)


def _capability_freshness(
    root: Path | None,
    generated_at: object,
    *,
    now: datetime | None = None,
) -> str:
    """Human provenance hint for a generated capability record.

    The capability payload still comes only from ``generate_project``. Git is
    consulted solely to say how much local work followed that payload's stamp.
    """
    if not isinstance(generated_at, str):
        return "generated time unknown · commits since unknown"
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
    except ValueError:
        return "generated time unknown · commits since unknown"

    age_seconds = max(0, int(((now or datetime.now(timezone.utc)) - generated).total_seconds()))
    if age_seconds < 60:
        age = "just now"
    elif age_seconds < 3600:
        age = f"{age_seconds // 60}m ago"
    elif age_seconds < 86400:
        age = f"{age_seconds // 3600}h ago"
    else:
        age = f"{age_seconds // 86400}d ago"

    commits = None
    if root is not None:
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "rev-list",
                    "--count",
                    f"--since={generated.isoformat()}",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                commits = int(result.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    commit_text = "commits since unknown" if commits is None else f"{commits} commits since"
    return f"generated {age} · {commit_text}"


def _invert_mobile_scroll() -> bool:
    override = (
        os.environ.get("HORUS_TUI_INVERT_SCROLL")
        or os.environ.get("HORUS_TUI_INVERT_MOUSE_SCROLL")
        or ""
    ).strip().lower()
    return bool(override) and override not in {"0", "false", "no", "off"}


_REVIEW_PLACEHOLDER = "(replace this line with your review)"


def _editor_command() -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return shlex.split(editor)
    if os.name == "nt":
        return ["notepad"]
    # The TUI is also a phone-facing surface.  Prefer a modeless editor when the
    # user has not chosen one: silently dropping a non-vi user into vi makes
    # ordinary letters look broken and gives them no discoverable way back.
    return ["nano"] if shutil.which("nano") else ["vi"]


def _editor_notice(command: list[str]) -> str:
    """Short hand-off guidance while the full-screen TUI is suspended."""
    name = Path(command[0]).name.lower()
    if name in {"nano", "pico"}:
        return f"Opening {name} (external editor). Save: Ctrl+O, Enter; return: Ctrl+X."
    if name in {"vi", "vim", "nvim"}:
        return (
            f"Opening {name} (external editor). Edit: i; save + return: Esc, :wq, Enter; "
            "quit unchanged: Esc, :q!, Enter."
        )
    return f"Opening {name} (external editor). Close it to return to Horus."


def _run_editor(path: Path) -> str | None:
    """Open the user's editor on `path`; returns an error message or None."""
    command = _editor_command()
    print(f"\n{_editor_notice(command)}", flush=True)
    try:
        subprocess.run([*command, str(path)], check=False)
    except OSError as exc:
        return f"Could not open editor ({exc}); set $EDITOR and retry."
    return None


def _edit_card(root: Path, card: backlog.Card, *, review: bool) -> str:
    """Between-frames flow for the card screen's `e`/`r` keys: optionally scaffold
    a `## Reviews` entry, open the user's editor on the card file, then OFFER to
    commit & push continuity — reusing closure's fetch-first commit primitive so
    a stale machine is refused before it can overwrite newer remote state. Always
    asks; never commits silently (hooks/UI advise and ask, never override)."""
    try:
        original = card.path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Cannot read {card.path.name}: {exc}"
    scaffolded = original
    if review:
        backlog.add_review(
            root, card.name,
            author=backlog.default_author(root),
            note=_REVIEW_PLACEHOLDER,
        )
        scaffolded = card.path.read_text(encoding="utf-8")
    if (error := _run_editor(card.path)) is not None:
        if review:
            card.path.write_text(original, encoding="utf-8")
        return error
    current = card.path.read_text(encoding="utf-8")
    if review and current == scaffolded:
        card.path.write_text(original, encoding="utf-8")
        return "Review cancelled — scaffold left untouched, card restored."
    if current == original or not closure.continuity_dirty(root):
        return f"No changes to {card.name}."
    answer = input(f"\n{card.name} changed. Commit & push continuity now? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        return f"{card.name} edited — uncommitted (sync later with `horus close --commit --push`)."
    verb = "review" if review else "edit"
    did, detail = closure.commit_continuity(
        root, f"Update backlog card {card.name} ({verb} via TUI)", push=True
    )
    return detail if did else f"Not committed: {detail}"


def _card_prompt(root: Path, card: backlog.Card) -> str:
    return (
        f"{routines.resume_prompt(root)}\n\n"
        f"Work on this backlog card first: {card.title}. Read the full card at "
        f"`.horus/backlog/{card.path.name}` before changing code, and treat it as the "
        "first item for this session."
    )


def _launch(*, target: str, agent: str, root: Path, account: str | None, prompt: str, posture: str = "default"):
    kwargs = {"agent": agent, "project_dir": root, "account": account, "prompt": prompt, "posture": posture}
    if target == terminal_sessions.TMUX:
        return terminal_sessions.launch_tmux(**kwargs)
    return terminal_sessions.run_attached(**kwargs)
