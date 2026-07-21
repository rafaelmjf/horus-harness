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
    activity,
    adapters,
    backlog,
    backlog_migrate,
    backlog_tree,
    capabilities,
    claude_usage,
    closure,
    codex_usage,
    config,
    datums,
    envelope,
    fleet_review,
    frontmatter,
    github_catalog,
    launch,
    machine_requirements,
    notify,
    notify_listen,
    projection_sync,
    proxy,
    registry,
    remote_start,
    routines,
    schedule,
    skills,
    statusline,
    terminal_sessions,
    usage_snapshot,
    warmup,
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
    prompt_override: str | None = None
    model: str | None = None
    effort: str | None = None
    posture: str | None = None


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


@dataclass(frozen=True)
class _RemoteStart:
    project: "github_catalog.RemoteProject"


@dataclass(frozen=True)
class _Campaign:
    pass


_Action = _Launch | _Attach | _Stop | _EditCard | _RemoteStart | _Campaign | str

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

# Just the explanation half of _POSTURE_LABELS, for the launch form's expanded row
# (which prints the posture name itself as the choice label).
_POSTURE_HELP: dict[str, str] = {
    key: label.split(" — ", 1)[1] for key, label in _POSTURE_LABELS.items()
}

# How a TUI-launched session opens (`config.LAUNCH_WINDOW_CHOICES`). `new-window`
# is desktop-only and falls back to takeover on mobile/SSH.
_WINDOW_LABELS: dict[str, str] = {
    "takeover": "Take over this terminal — Ctrl-b d back to the TUI (default; phone-friendly)",
    "new-window": "New window on desktop — opens beside the TUI; takeover on mobile/SSH",
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
        self.project_trees = {project: _project_tree(project) for project in self.projects}
        self.project_receipts = {project: _receipts(project) for project in self.projects}
        # Group-by lens for the backlog list, and per-(project, lens, group) collapse
        # state. Sections default to EXPANDED; a key present here is collapsed.
        self.backlog_group_by = config.load_backlog_group_by()
        self.collapsed_groups: set[tuple[Path, str, str]] = set()
        self.priority_card: backlog.Card | None = None  # card whose priority the picker edits
        self.receipt: backlog_tree.Receipt | None = None
        self.receipt_scroll = 0
        self.project_pending = {
            project: len(closure.pending_delivery_commits(project)) for project in self.projects
        }
        self.remote_projects, self.remote_ignored, self.remote_errors = _remote_projects()
        self.running = [record for record in registry.Registry.default().all() if record.status == "running"]
        self.screen = "projects"
        self.project: Path | None = None
        self.project_filter: Path | None = None
        self.pending_mode: str | None = None
        self.pending_card: backlog.Card | None = None
        self.pending_prompt: str | None = None
        self.pending_origin: str | None = None
        self.pending_account: LaunchAccount | None = None
        self.pending_model: str | None = None
        self.pending_effort: str | None = None
        self.pending_posture: str | None = None
        # Which row of the consolidated launch form is expanded to show its
        # alternatives, or None while the form is in its compact review state.
        self.launch_expanded: str | None = None
        self.card: backlog.Card | None = None
        self.card_scroll = 0
        self.backlog_fields = config.load_backlog_fields()
        self.project_focus: dict[str, str] = {}
        self.project_requirements: machine_requirements.Report | None = None
        self.capabilities_record: dict | None = None
        self.capabilities_error = ""
        self.project_skill_states: list[skills.SkillState] = []
        self.fleet_review_record: fleet_review.FleetReview | None = None
        self.fleet_review_error = ""
        self.projection_records: list[tuple[Path, dict]] = []
        self._load_projection_sync()
        # Mission Control (`m`) + Settings (`t`) panes — shared cached machine state,
        # refreshed on show/after an action so systemctl/loginctl reads never run inside
        # the per-render body paint.
        self.control_sched_ok = False
        self.control_listener_active = False
        self.control_listener_installed = False
        self.control_keepwarm: dict[str, bool] = {}
        self.control_linger: bool | None = None
        self.control_sink = "none"
        self.control_envelopes: list[tuple[str, str, str]] = []  # (name, expires, state)
        self.control_activity: activity.Activity | None = None
        self.control_proxy: proxy.ProxyStatus | None = None
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
            self._nav("up")

        @keys.add("j")
        def _down(event) -> None:
            self._nav("down")

        @keys.add("up")
        def _terminal_up(event) -> None:
            self._nav("down" if self.invert_mobile_scroll else "up")

        @keys.add("down")
        def _terminal_down(event) -> None:
            self._nav("up" if self.invert_mobile_scroll else "down")

        @keys.add("right")
        def _terminal_right(event) -> None:
            self._nav("right")

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
        @keys.add("b")
        def _back(event) -> None:
            self.back()

        @keys.add("left")
        def _left(event) -> None:
            # On the wide projects grid, left moves a column; with no column to its
            # left (single list, tail, or narrow) it falls through to Back.
            self._nav("left")

        @keys.add("s")
        def _sessions(event) -> None:
            self.project_filter = None
            self._show("sessions")

        @keys.add("d")
        def _defaults(event) -> None:
            self._show("settings")

        @keys.add("m")
        def _mission(event) -> None:
            self._show("mission")

        @keys.add("t")
        def _machine_settings(event) -> None:
            self._show("toggles")

        @keys.add("u")
        def _refresh_usage(event) -> None:
            if self.screen == "projection_sync":
                self.refresh_projection_sync()
            else:
                self.refresh_account_usage()

        @keys.add("f")
        def _fleet_review(event) -> None:
            if self.screen == "projects":
                self._load_fleet_review()
                self._show("fleet_review")
            elif self.screen == "backlog":
                self._show("backlog_fields")

        on_card = Condition(lambda: self.screen == "card" and self.card is not None)

        @keys.add("e", filter=on_card)
        def _edit_card(event) -> None:
            self._exit_edit(review=False)

        @keys.add("r", filter=on_card)
        def _review_card(event) -> None:
            self._exit_edit(review=True)

        @keys.add("p")
        def _priority(event) -> None:
            # Quick reprioritize from the backlog without opening the editor — open
            # the priority picker for the selected card.
            if self.screen == "backlog" and self.items:
                kind, value = self.items[self.selected]
                if kind == "card":
                    self.priority_card = value  # type: ignore[assignment]
                    self._show("card_priority")

        @keys.add("g")
        def _cycle_group_by(event) -> None:
            # Cycle the backlog group-by lens for THIS session (the persisted
            # default lives in the Settings pane). Wraps None→Readiness→…→Priority.
            if self.screen != "backlog":
                return
            lenses = backlog_tree.GROUP_BY_LENSES
            self.backlog_group_by = lenses[(lenses.index(self.backlog_group_by) + 1) % len(lenses)]
            self.selected = 0
            self._refresh_items()
            self.status = f"Grouped by: {backlog_tree.GROUP_BY_LABELS[self.backlog_group_by]}"
            self.application.invalidate()

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

    def refresh_projection_sync(self) -> None:
        """Re-run the canonical read-only projection comparison."""
        selected = self.selected
        self._load_projection_sync()
        self._refresh_items()
        self.selected = min(selected, max(0, len(self.items) - 1))
        self.status = "Projection sync refreshed against the installed CLI."
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

    def _project_columns(self, width: int | None = None) -> int:
        """Column count for the projects home grid — the single source of truth
        shared by the wide render and grid navigation. 1 (a single scrollable list)
        on a narrow/mobile width or any non-projects screen; a fluid 2–3 on the
        wide cockpit."""
        if self.screen != "projects":
            return 1
        if width is None:
            width = self.application.output.get_size().columns
        if width < 96:
            return 1
        return min(3, max(2, width // 72))

    def _nav(self, direction: str) -> None:
        """Arrow/vim navigation. Card/receipt screens scroll their text body;
        every list screen routes through the 2D-aware grid nav so on the wide
        projects grid down/up move a row and left/right move a column, while a
        single-column list keeps linear up/down with left = Back."""
        if self.screen in ("card", "receipt"):
            if direction == "up":
                self.scroll(-1)
            elif direction == "down":
                self.scroll(1)
            elif direction == "left":
                self.back()
            return
        cols = self._project_columns()
        projects = sum(1 for kind, _ in self.items if kind == "project")
        target = _grid_nav_target(self.selected, len(self.items), projects, cols, direction)
        if target is None:
            self.back()
        elif target != self.selected:
            self.move(target - self.selected)

    def _reload_project_backlog(self, project: Path) -> None:
        """Re-read one project's cards, tree, and metrics after an in-place card
        edit (e.g. a priority change) so the backlog re-renders immediately."""
        self.project_cards[project] = _open_cards(project)
        self.project_metrics[project] = _backlog_metrics(project, self.project_cards[project])
        self.project_trees[project] = _project_tree(project)

    def scroll(self, amount: int) -> None:
        if self.screen == "card":
            lines = self._card_lines()
            self.card_scroll = max(0, min(len(lines) - 1, self.card_scroll + amount))
            self.application.invalidate()
            return
        if self.screen == "receipt":
            lines = self._receipt_lines()
            self.receipt_scroll = max(0, min(len(lines) - 1, self.receipt_scroll + amount))
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
            self._load_project_requirements()
            self._load_project_capabilities()
            self._load_project_skills()
            self._show("project")
        elif self.screen == "projects" and kind == "fleet_review":
            self._load_fleet_review()
            self._show("fleet_review")
        elif self.screen == "projects" and kind == "projection_sync":
            self._show("projection_sync")
        elif self.screen == "projects" and kind == "remote_project":
            if isinstance(value, github_catalog.RemoteProject):
                self.application.exit(result=_RemoteStart(value))
        elif self.screen == "projects" and kind == "campaign":
            self.application.exit(result=_Campaign())
        elif self.screen == "project" and kind == "mode":
            self.pending_mode = str(value)
            self.pending_card = None
            self.pending_prompt = None
            self.pending_origin = "project"
            self._show("accounts")
        elif self.screen == "project" and kind == "backlog":
            self._show("backlog")
        elif self.screen == "project" and kind == "capabilities":
            self._show("capabilities")
        elif self.screen == "project" and kind == "skills":
            self._show("skills")
        elif self.screen == "project" and kind == "receipts":
            self._show("receipts")
        elif self.screen == "backlog" and kind == "group":
            section = value  # type: ignore[assignment]
            key = (self.project, self.backlog_group_by, section.key)
            if key in self.collapsed_groups:
                self.collapsed_groups.discard(key)  # expand
            else:
                self.collapsed_groups.add(key)  # collapse
            selected = self.selected
            self._refresh_items()
            self.selected = min(selected, max(0, len(self.items) - 1))
            self.application.invalidate()
        elif self.screen == "receipts" and kind == "receipt":
            self.receipt = value  # type: ignore[assignment]
            self.receipt_scroll = 0
            self._show("receipt")
        elif self.screen == "backlog_fields" and kind == "backlog_field":
            field = str(value)
            self.backlog_fields = config.toggle_backlog_field(field)
            selected = self.selected
            self._refresh_items()
            self.selected = min(selected, max(0, len(self.items) - 1))
            shown = "shown on" if field in self.backlog_fields else "hidden from"
            self.status = f"{field} {shown} every backlog card row."
            self.application.invalidate()
        elif self.screen == "backlog" and kind == "card":
            self.card = value  # type: ignore[assignment]
            self.card_scroll = 4
            self._show("card")
        elif self.screen == "card_priority" and kind == "priority_choice":
            choice = str(value)
            card = self.priority_card
            message = ""
            if card is not None:
                try:
                    backlog.set_priority(card.path, choice)
                    if self.project is not None:
                        self._reload_project_backlog(self.project)
                    message = f"{card.name}: priority set to {choice}."
                except (ValueError, OSError) as exc:
                    message = f"Could not set priority: {exc}"
            self.priority_card = None
            self._show("backlog")  # clears status, so set the outcome after
            self.status = message
        elif self.screen == "card" and kind == "card_resume":
            self.pending_mode = "resume"
            self.pending_card = self.card
            self.pending_prompt = None
            self.pending_origin = "card"
            self._show("accounts")
        elif self.screen == "sessions" and kind == "session":
            self.selected_session = value  # type: ignore[assignment]
            self._show("session")
        elif self.screen == "accounts" and kind == "account":
            if isinstance(value, LaunchAccount):
                self.pending_account = value
                # Preselect this agent's saved profile so the common case is a single
                # keypress on Launch; an unusual model stays a per-launch override.
                profile = config.load_launch_profile(value.agent)
                self.pending_model = profile.get("model")
                self.pending_effort = profile.get("effort")
                self.pending_posture = profile.get(
                    "posture", config.load_launch_defaults()["posture"]
                )
                self.launch_expanded = None
                self._show("launch_form")
        elif self.screen == "launch_form":
            self._handle_launch_form(kind, value)
        elif self.screen == "settings" and kind == "posture":
            posture = str(value)
            config.set_launch_default_posture(posture)
            self._refresh_items()
            self.status = f"Default launch posture set to {posture}."
            self.application.invalidate()
        elif self.screen == "settings" and kind == "window":
            window = str(value)
            config.set_launch_default_window(window)
            self._refresh_items()
            self.selected = (
                len(config.LAUNCH_POSTURE_CHOICES)
                + config.LAUNCH_WINDOW_CHOICES.index(window)
            )
            self.status = f"Sessions now launch: {window}."
            self.application.invalidate()
        elif self.screen == "toggles":
            self._activate_toggles(kind, value)
        elif self.screen == "fleet_review" and kind == "curator":
            if isinstance(value, Path):
                self.project = value
                self.pending_mode = "resume"
                self.pending_card = None
                self.pending_prompt = None
                self.pending_origin = "fleet_review"
                self._show("accounts")
        elif self.screen == "projection_sync" and kind == "projection_curator":
            if isinstance(value, Path):
                self.project = value
                self.pending_mode = "resume"
                self.pending_card = None
                self.pending_prompt = _projection_curator_prompt(self.projection_records)
                self.pending_origin = "projection_sync"
                self._show("accounts")
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
            self.project_requirements = None
            self._show("projects")
        elif self.screen == "accounts":
            self._show(self.pending_origin or ("card" if self.pending_card is not None else "project"))
        elif self.screen == "launch_form":
            # An expanded row collapses first, so Back never loses the whole form
            # when the owner was only peeking at a row's alternatives.
            if self.launch_expanded is not None:
                self.launch_expanded = None
                self._refresh_items()
                self.application.invalidate()
            else:
                self._show("accounts")
        elif self.screen == "backlog":
            self._show("project")
        elif self.screen == "backlog_fields":
            self._show("backlog")
        elif self.screen == "card_priority":
            self.priority_card = None
            self._show("backlog")
        elif self.screen == "capabilities":
            self._show("project")
        elif self.screen == "skills":
            self._show("project")
        elif self.screen == "receipts":
            self._show("project")
        elif self.screen == "receipt":
            self._show("receipts")
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
        elif self.screen in ("mission", "toggles"):
            self._show("projects")
        elif self.screen == "fleet_review":
            self._show("projects")
        elif self.screen == "projection_sync":
            self._show("projects")

    def _show(self, screen: str) -> None:
        self.screen = screen
        self.selected = 0
        self.status = ""
        self._refresh_items()
        if screen == "launch_form":
            # Posture always has a concrete value — unlike model/effort there is no
            # "agent default" to defer to, so an unset one resolves to the configured
            # launch default rather than rendering as absent.
            if self.pending_posture is None:
                self.pending_posture = config.load_launch_defaults()["posture"]
                self._refresh_items()
            # Launch is focused by default: the saved profile is already correct for
            # the common case, so the whole form should cost one keypress.
            self.selected = max(0, len(self.items) - 1)
        self.application.invalidate()

    def _load_control(self) -> None:
        """Read machine state once (systemctl/loginctl/config/activity) into cached
        attributes — shared by BOTH the Mission Control (`m`) and Settings (`t`) panes,
        so the body paint never re-reads it per render."""
        self.control_sched_ok = schedule.availability().ok
        if self.control_sched_ok:
            self.control_listener_installed = schedule.listen_service_installed()
            self.control_listener_active = schedule.listen_service_active()
            self.control_linger = schedule.linger_enabled()
            self.control_keepwarm = {
                alias: schedule.keepwarm_service_active(alias) for alias in warmup.claude_accounts()
            }
        else:
            self.control_listener_installed = False
            self.control_listener_active = False
            self.control_linger = None
            self.control_keepwarm = {}
        try:
            self.control_sink = notify.load_notify_config().sink
        except Exception:  # noqa: BLE001 - a bad config degrades to 'none', never a crash
            self.control_sink = "none"
        self.control_remote_control = config.load_remote_control_default()
        self.control_backlog_group_by = config.load_backlog_group_by()
        today = datetime.now().date()
        self.control_envelopes = []
        for env in envelope.load_all():
            if env.revoked:
                state = "revoked"
            elif env.is_expired(today=today):
                state = "expired"
            else:
                state = "live"
            self.control_envelopes.append((env.name, env.expires, state))
        self.control_activity = activity.collect(limit=8)
        try:
            self.control_proxy = proxy.status()
        except Exception:  # noqa: BLE001 - a proxy probe failure never breaks the pane
            self.control_proxy = None

    def _activate_toggles(self, kind: str, value: object) -> None:
        """Enter on a Settings-pane (`t`) item: toggle a machine feature / fire a quick
        action via the existing CLI primitives (never a reimplemented systemd/notify path)."""
        if not self.control_sched_ok and kind in {"ctl_listener", "ctl_listener_restart", "ctl_keepwarm"}:
            self.status = "Scheduling unavailable here — systemd --user timers are needed."
        elif kind == "ctl_listener":
            try:
                if self.control_listener_active:
                    schedule.remove_listen_service()
                    self.status = "Steering listener stopped."
                else:
                    invalid = notify_listen.validate_config()
                    if invalid is not None:
                        self.status = invalid[1]
                    else:
                        schedule.install_listen_service(
                            command=("horus", "notify", "listen"), cwd=Path.cwd())
                        self.status = "Steering listener started (persistent service)."
            except schedule.ScheduleError as exc:
                self.status = f"Listener: {exc}"
        elif kind == "ctl_listener_restart":
            try:
                schedule.restart_listen_service()
                self.status = "Steering listener restarted (adopts the current CLI)."
            except schedule.ScheduleError as exc:
                self.status = f"Listener restart: {exc}"
        elif kind == "ctl_keepwarm" and isinstance(value, str):
            try:
                if self.control_keepwarm.get(value):
                    schedule.remove_keepwarm_service(value)
                    self.status = f"Keep-warm off for {value}."
                else:
                    schedule.install_keepwarm_service(
                        account=value,
                        command=("horus", "warmup", "--keep", "--account", value),
                        cwd=Path.cwd(),
                    )
                    self.status = f"Keep-warm on for {value} (re-warms after each 5h reset)."
            except schedule.ScheduleError as exc:
                self.status = f"Keep-warm: {exc}"
        elif kind == "ctl_notify_test":
            esc = notify.Escalation(
                event=notify.SUPERVISE_GATE,
                project="horus",
                summary="test escalation from the TUI Settings pane",
                inspect="this is a test; no action needed",
            )
            self.status = notify.escalate(esc, force=True).describe()
        elif kind == "ctl_proxy":
            st = self.control_proxy
            if st is not None and st.enabled:
                _, self.status = proxy.disable()
            elif st is not None and st.ready_to_enable:
                self.status = "Enabling proxy (starting service + verifying)…"
                self.application.invalidate()
                _, self.status = proxy.enable()
            else:
                self.status = ("Proxy not set up — run `horus proxy login codex` (and `claude`) "
                               "in a terminal, then toggle here.")
        elif kind == "ctl_remote_control":
            new = config.set_remote_control_default(not self.control_remote_control)
            self.control_remote_control = new
            self.status = (
                "Remote Control on by default — new Horus-launched Claude sessions are "
                "phone-attachable at spawn." if new else
                "Remote Control off by default — enable per launch with `open --remote-control`."
            )
        elif kind == "ctl_backlog_group_by":
            lenses = backlog_tree.GROUP_BY_LENSES
            nxt = lenses[(lenses.index(self.control_backlog_group_by) + 1) % len(lenses)]
            config.set_backlog_group_by(nxt)
            self.control_backlog_group_by = nxt
            self.backlog_group_by = nxt  # apply to the live session too
            self.status = f"Backlog opens grouped by: {backlog_tree.GROUP_BY_LABELS[nxt]}"
        self._refresh_items()
        self.selected = min(self.selected, max(0, len(self.items) - 1))
        self.application.invalidate()

    def _refresh_items(self) -> None:
        if self.screen == "mission":
            # Mission Control is read-mostly observability (armed + recent + readiness);
            # no toggles live here, so it carries no selectable items.
            self._load_control()
            self.items = []
            return
        if self.screen == "toggles":
            self._load_control()
            items: list[tuple[str, object]] = [("ctl_listener", None)]
            if self.control_listener_active:
                items.append(("ctl_listener_restart", None))
            items.extend(("ctl_keepwarm", alias) for alias in sorted(self.control_keepwarm))
            items.append(("ctl_notify_test", None))
            items.append(("ctl_proxy", None))
            items.append(("ctl_remote_control", None))
            items.append(("ctl_backlog_group_by", None))
            self.items = items
            return
        if self.screen == "projects":
            self.items = [("project", project) for project in self.projects]
            self.items.extend(("remote_project", project) for project in self.remote_projects)
            self.items.append(("projection_sync", None))
            self.items.append(("fleet_review", None))
            if _cockpit_project(self.projects) is not None:
                self.items.append(("campaign", None))
        elif self.screen == "project":
            self.items = [
                ("mode", "resume"),
                ("mode", "fresh"),
                ("backlog", None),
                ("capabilities", None),
                ("skills", None),
                ("receipts", None),
            ]
        elif self.screen == "accounts":
            self.items = [("account", account) for account in self.accounts]
        elif self.screen == "launch_form":
            self.items = self._launch_form_items()
        elif self.screen == "receipts":
            self.items = [("receipt", receipt) for receipt in self.project_receipts.get(self.project, [])]
        elif self.screen == "receipt":
            self.items = []
        elif self.screen == "backlog":
            cards = self.project_cards.get(self.project, [])
            tree = self.project_trees.get(self.project) or backlog_tree.Tree()
            sections = backlog_tree.sections_for(cards, self.backlog_group_by, tree)
            if len(sections) <= 1:
                # `none`, or a lens with no real structure (a new project, or one
                # that does not use facets/branches): the flat list is the fallback,
                # identical to the pre-grouping view.
                self.items = [("card", card) for card in cards]
            else:
                items: list[tuple[str, object]] = []
                for section in sections:
                    items.append(("group", section))
                    if (self.project, self.backlog_group_by, section.key) not in self.collapsed_groups:
                        items.extend(("card", card) for card in section.children)
                self.items = items
        elif self.screen == "card_priority":
            self.items = [("priority_choice", p) for p in backlog.PRIORITY_CHOICES]
            current = self.priority_card.priority if self.priority_card else ""
            if current in backlog.PRIORITY_CHOICES:
                self.selected = backlog.PRIORITY_CHOICES.index(current)
        elif self.screen == "backlog_fields":
            choices = _card_field_choices(self.project_cards.get(self.project, []), self.backlog_fields)
            self.items = [("backlog_field", key) for key in choices]
        elif self.screen == "capabilities":
            project = (self.capabilities_record or {}).get("project", {})
            records = project.get("capabilities", []) if isinstance(project, dict) else []
            self.items = [
                ("capability", record)
                for record in records
                if isinstance(record, dict) and isinstance(record.get("text"), str)
            ]
        elif self.screen == "skills":
            self.items = [("skill", state) for state in self.project_skill_states]
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
            posture = config.load_launch_defaults()["posture"]
            self.items = [("posture", choice) for choice in config.LAUNCH_POSTURE_CHOICES]
            self.items.extend(("window", choice) for choice in config.LAUNCH_WINDOW_CHOICES)
            self.selected = config.LAUNCH_POSTURE_CHOICES.index(posture)
        elif self.screen == "fleet_review":
            self.items = []
            if self.fleet_review_record is not None:
                curator = Path(self.fleet_review_record.manifest).parent
                if curator in self.projects:
                    self.items.append(("curator", curator))
                self.items.extend(
                    ("review_project", project)
                    for project in self.fleet_review_record.projects
                )
        elif self.screen == "projection_sync":
            self.items = []
            curator = _cockpit_project(self.projects)
            if curator is not None:
                self.items.append(("projection_curator", curator))
            self.items.extend(("projection_project", record) for record in self.projection_records)

    def _exit_edit(self, *, review: bool) -> None:
        if self.project is None or self.card is None:
            return
        self.application.exit(result=_EditCard(self.project, self.card, review))

    def _launch_model_choices(self) -> list[str]:
        agent = self.pending_account.agent if self.pending_account else ""
        models = list(_agent_models(agent))
        # Toggle on → a Claude launch is proxied, so offer the proxy's GPT models
        # next to the native Claude aliases (both are served through the one proxy).
        # load_state() is a cheap file read (no network), reliable whether or not the
        # Control pane has been visited this session.
        if agent == "claude" and proxy.load_state().get("enabled"):
            models += proxy.gpt_launch_models()
        return models

    def _launch_form_items(self) -> list[tuple[str, object]]:
        """Rows of the consolidated launch form, with the expanded row's choices
        spliced in beneath it. Launch is last so it stays the resting position."""
        rows: list[tuple[str, object]] = []
        for row, choices in (
            ("model", [None] + self._launch_model_choices()),
            ("effort", [None] + list(adapters.EFFORT_LEVELS)),
            ("posture", list(config.LAUNCH_POSTURE_CHOICES)),
        ):
            rows.append(("launch_row", row))
            if self.launch_expanded == row:
                rows.extend((row, choice) for choice in choices)
        rows.append(("save_defaults", None))
        rows.append(("launch", None))
        return rows

    def _handle_launch_form(self, kind: str, value: object) -> None:
        """One consolidated review form: model / effort / posture, then Launch.

        Compact by default — each row shows only its selected value. Entering a row
        expands its alternatives; picking one collapses back. `Save as defaults`
        persists the current selection as this agent's profile, so an occasional
        override never rewrites it.
        """
        if kind == "launch_row":
            # Enter on a compact row expands it; entering the open row collapses it.
            row = str(value)
            self.launch_expanded = None if self.launch_expanded == row else row
            self._refresh_items()
            return
        if kind in ("model", "effort", "posture"):
            selected = value if value is None else str(value)
            if kind == "model":
                self.pending_model = selected
            elif kind == "effort":
                self.pending_effort = selected
            else:
                self.pending_posture = selected
            self.launch_expanded = None
            self._refresh_items()
            return
        if kind == "save_defaults":
            if self.pending_account is not None:
                profile = {
                    key: val
                    for key, val in (
                        ("model", self.pending_model),
                        ("effort", self.pending_effort),
                        ("posture", self.pending_posture),
                    )
                    if val
                }
                try:
                    config.save_launch_profile(self.pending_account.agent, profile)
                    self.status = f"Saved as {self.pending_account.agent} launch defaults."
                except (ValueError, OSError) as exc:
                    self.status = f"Could not save defaults: {exc}"
                self.application.invalidate()
            return
        if kind == "launch" and self.pending_account is not None:
            self._exit_launch(self.pending_account)

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
                self.pending_prompt,
                self.pending_model,
                self.pending_effort,
                self.pending_posture,
            )
        )

    def _launch_tier(self) -> str:
        """The `tier:` a resume/card-launch resolves a recommendation from.

        A backlog-card launch reads the card's own tier; a plain resume reads
        the project's top open card (its sorted-by-priority "next action") as
        a proxy for the project's current focus. A fresh launch never
        recommends — it has no continuity context to recommend from.
        """
        if self.pending_mode != "resume":
            return ""
        if self.pending_card is not None:
            return self.pending_card.tier
        cards = self.project_cards.get(self.project) if self.project is not None else None
        return cards[0].tier if cards else ""

    def _recommended_model_for_launch(self) -> str | None:
        tier = self._launch_tier()
        if not tier or self.pending_account is None:
            return None
        return _resolve_recommended_model(tier, _agent_models(self.pending_account.agent))

    def _header_text(self) -> StyleAndTextTuples:
        title = {
            "projects": "HORUS · Projects",
            "project": f"HORUS · {self.project.name if self.project else 'Project'}",
            "accounts": f"HORUS · {self.pending_mode.title() if self.pending_mode else 'Choose'} account",
            "launch_form": (
                f"HORUS · Launch {self.pending_account.agent.title()}"
                if self.pending_account
                else "HORUS · Launch"
            ),
            "backlog": f"HORUS · {self.project.name if self.project else 'Project'} backlog",
            "backlog_fields": "HORUS · Backlog card fields",
            "card_priority": f"HORUS · Priority: {self.priority_card.name if self.priority_card else 'card'}",
            "capabilities": f"HORUS · {self.project.name if self.project else 'Project'} capabilities",
            "skills": f"HORUS · {self.project.name if self.project else 'Project'} skills",
            "card": "HORUS · Backlog card",
            "receipts": f"HORUS · {self.project.name if self.project else 'Project'} receipts",
            "receipt": "HORUS · Receipt",
            "sessions": "HORUS · Running sessions",
            "session": "HORUS · Session",
            "confirm": "HORUS · Close session?",
            "settings": "HORUS · Defaults",
            "mission": "HORUS · Mission Control",
            "toggles": "HORUS · Settings",
            "fleet_review": "HORUS · Fleet Review",
            "projection_sync": "HORUS · Projection Sync",
        }[self.screen]
        live = len(self.running)
        return [("class:header", f" {title}"), ("class:meta", f"   {live} live" if live else "")]

    def _body_text(self) -> StyleAndTextTuples:
        if self.screen == "card":
            return self._card_body_text()
        if self.screen == "receipt":
            return self._receipt_body_text()
        if self.screen == "mission":
            return self._mission_body_text()
        if self.screen == "toggles":
            return self._settings_body_text()
        if self.screen == "capabilities":
            return self._capabilities_body_text()
        if self.screen == "skills":
            return self._skills_body_text()
        if self.screen == "fleet_review":
            return self._fleet_review_body_text()
        if self.screen == "projection_sync":
            return self._projection_sync_body_text()
        if not self.items:
            if self.screen == "projects":
                message = "No tracked projects. Run `horus init` first."
            elif self.screen == "backlog":
                message = "No open backlog cards."
            elif self.screen == "receipts":
                message = "No research receipts yet."
            elif self.screen == "backlog_fields":
                message = "No frontmatter fields on these cards."
            elif self.screen == "accounts":
                message = "No agent accounts detected."
            else:
                message = "No running sessions."
            return [("class:muted", f"\n  {message}\n")]
        if self.screen == "projects" and self.application.output.get_size().columns >= 96:
            return self._wide_home_text(self.application.output.get_size().columns)
        lines: StyleAndTextTuples = []
        if self.screen == "backlog":
            counts = backlog.readiness_counts(self.project_cards.get(self.project, []))
            lines.extend([
                ("class:section", "\n  Readiness\n"),
                (
                    "class:muted",
                    f"  Ready—Autonomous eligible {counts[backlog.QUEUE_READY_ELIGIBLE]} · "
                    f"Ready—Attended {counts[backlog.QUEUE_READY_ATTENDED]}\n",
                ),
                (
                    "class:muted",
                    f"  Shaping {counts[backlog.QUEUE_SHAPING]} · "
                    f"Gated {counts[backlog.QUEUE_GATED]} · "
                    f"Deferred {counts[backlog.QUEUE_DEFERRED]} · "
                    f"Unclassified {counts[backlog.QUEUE_UNCLASSIFIED]}\n",
                ),
            ])
        if self.screen == "projects":
            lines.extend(self._account_summary_text())
            lines.extend(self._remote_catalog_notes_text())
        elif self.screen == "project":
            pending = self.project_pending.get(self.project, 0)
            if pending:
                lines.append((
                    "class:warning",
                    f"\n  Continuity checkpoint pending · {pending} delivery commit"
                    f"{'s' if pending != 1 else ''}\n",
                ))
            warning = (
                machine_requirements.warning_text(self.project_requirements)
                if self.project_requirements is not None
                else ""
            )
            if warning:
                lines.append(("class:warning", f"\n  {warning}\n"))
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
        recommended_model = (
            self._recommended_model_for_launch() if self.screen == "launch_form" else None
        )
        under_group = False  # backlog: are we rendering cards under a group header?
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if kind == "group":
                under_group = True
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
                pending = self.project_pending.get(root, 0)
                continuity = f" · continuity {pending} pending" if pending else ""
                lines.append(("class:muted", f"     backlog {card_count} · bugs {bug_count}{continuity}\n"))
            elif kind == "remote_project":
                project = value
                badge = "cloned, not registered" if project.is_local else "remote only"
                lines.append((style, f"\n {marker} {project.name} · {badge}\n"))
                detail = project.current_focus or project.full_name
                lines.append(("class:muted", f"     {detail}\n"))
            elif kind == "fleet_review":
                lines.append((style, f"\n {marker} Fleet Review\n"))
                lines.append(
                    ("class:muted", "     Compare remote shipped truth with local working state\n")
                )
            elif kind == "campaign":
                lines.append((style, f"\n {marker} Campaign\n"))
                lines.append(
                    (
                        "class:muted",
                        "     Optional cross-project supervision — asks for outcome + targets\n",
                    )
                )
            elif kind == "projection_sync":
                stale, unknown = _projection_counts(self.projection_records)
                detail = f"{stale} stale"
                if unknown:
                    detail += f" · {unknown} unknown"
                if not stale and not unknown:
                    detail = "all tracked projects in sync"
                lines.append((style, f"\n {marker} Projection Sync\n"))
                lines.append(("class:muted", f"     {detail} · Claude/Codex vs installed CLI\n"))
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
                cards = self.project_cards.get(self.project, [])
                counts = backlog.readiness_counts(cards)
                ready = counts[backlog.QUEUE_READY_ELIGIBLE] + counts[backlog.QUEUE_READY_ATTENDED]
                lines.append((
                    "class:muted",
                    f"     {card_count} cards · {bug_count} bugs · {ready} ready · "
                    f"{counts[backlog.QUEUE_SHAPING]} shaping · "
                    f"{counts[backlog.QUEUE_GATED]} gated · "
                    f"{counts[backlog.QUEUE_DEFERRED]} deferred\n",
                ))
            elif kind == "capabilities":
                project = (self.capabilities_record or {}).get("project", {})
                records = project.get("capabilities", []) if isinstance(project, dict) else []
                count = len(records) if isinstance(records, list) else 0
                lines.append((style, f"\n {marker} Capabilities\n"))
                detail = self.capabilities_error or f"{count} shipped capabilities"
                lines.append(("class:muted", f"     {detail}\n"))
            elif kind == "skills":
                lines.append((style, f"\n {marker} Skills\n"))
                lines.append(("class:muted", f"     {_skill_summary(self.project_skill_states)}\n"))
            elif kind == "receipts":
                count = len(self.project_receipts.get(self.project, []))
                lines.append((style, f"\n {marker} Receipts\n"))
                lines.append(("class:muted", f"     {count} research receipt{'s' if count != 1 else ''}\n"))
            elif kind == "account":
                account = value
                lines.append((style, f"\n {marker} {account.agent.title()} {account.alias}\n"))
                for meter_style, meter_text in _usage_meter_lines(self.account_usage.get((account.agent, account.alias))):
                    lines.append((meter_style, f"     {meter_text}\n"))
            elif kind == "launch_row":
                row = str(value)
                current = {
                    "model": self.pending_model,
                    "effort": self.pending_effort,
                    "posture": self.pending_posture,
                }[row]
                label = {"model": "Model", "effort": "Effort", "posture": "Permission"}[row]
                shown = str(current) if current else "agent default"
                caret = "v" if self.launch_expanded == row else ">"
                lines.append((style, f"\n {marker} {label:<11}{shown}  {caret}\n"))
            elif kind in ("model", "effort", "posture") and self.screen == "launch_form":
                # An expanded row's alternatives: indented, radio-marked, with the
                # one-line help that stays hidden while the form is compact. Scoped to
                # the form so it never shadows Settings' own `posture` rows below.
                current = {
                    "model": self.pending_model,
                    "effort": self.pending_effort,
                    "posture": self.pending_posture,
                }[kind]
                radio = "(o)" if value == current else "( )"
                if value is None:
                    label = "Default"
                    detail = f"Agent's default {'model' if kind == 'model' else 'reasoning effort'}"
                else:
                    label = str(value)
                    detail = _POSTURE_HELP.get(label, "") if kind == "posture" else ""
                    if kind == "model" and value == recommended_model:
                        label += " (recommended)"
                lines.append((style, f"\n   {marker} {radio} {label}\n"))
                if detail:
                    lines.append(("class:muted", f"        {detail}\n"))
            elif kind == "save_defaults":
                agent = self.pending_account.agent if self.pending_account else "this agent"
                lines.append((style, f"\n {marker} Save as defaults\n"))
                lines.append((
                    "class:muted",
                    f"     Remember this selection for every {agent} launch\n",
                ))
            elif kind == "launch":
                lines.append((style, f"\n {marker} Launch\n"))
            elif kind == "card":
                card = value
                status = " · claimed" if card.status == "claimed" else ""
                suffix = _card_field_suffix(card, self.backlog_fields)
                # A card under a group header gets a tree connector + indent so
                # its membership is visible; the last child closes with └─.
                if under_group:
                    last = index + 1 >= len(self.items) or self.items[index + 1][0] != "card"
                    connector = "   └─ " if last else "   ├─ "
                else:
                    connector = " "
                lines.append((style, f"\n{connector}{marker} "))
                lines.append(_priority_dot(card.priority))
                lines.append((style, f"[{card.type}{status}] {card.title}{suffix}\n"))
                indent = "        " if under_group else "     "
                lines.append(("class:muted", f"{indent}{backlog.readiness_label(card)}\n"))
                if card.readiness_reason:
                    lines.append(("class:muted", f"{indent}{card.readiness_reason}\n"))
                # The classic priority sub-line, unless priority was picked as an
                # inline field — then it's already on the row above.
                if card.priority and "priority" not in self.backlog_fields:
                    lines.append(("class:muted", f"{indent}priority {card.priority}\n"))
            elif kind == "group":
                section = value
                collapsed = (self.project, self.backlog_group_by, section.key) in self.collapsed_groups
                caret = "▸" if collapsed else "▾"
                header_style = "class:selected" if selected else "class:branch"
                lines.append((header_style, f"\n {marker} {caret} {section.label} ({len(section.children)})\n"))
                if section.subtitle:
                    lines.append(("class:muted", f"     {section.subtitle}\n"))
            elif kind == "receipt":
                receipt = value
                lines.append((style, f"\n {marker} {receipt.title}\n"))
                lines.append(("class:muted", f"     {receipt.date or 'undated'} · {receipt.path.name}\n"))
            elif kind == "priority_choice":
                if index == 0:
                    title = self.priority_card.title if self.priority_card else ""
                    lines.append(("class:section", f"\n  Set priority — {title}\n"))
                choice = str(value)
                current = self.priority_card.priority if self.priority_card else ""
                active = "current" if choice == current else "      "
                lines.append((style, f"\n {marker} "))
                lines.append(_priority_dot(choice))
                lines.append((style, f"[{active}] {choice}\n"))
            elif kind == "backlog_field":
                if index == 0:
                    lines.append(("class:section", "\n  Shown inline after each card title\n"))
                field = str(value)
                cards = self.project_cards.get(self.project, [])
                shown = field in self.backlog_fields
                box = "x" if shown else " "
                lines.append((style, f"\n {marker} [{box}] {field}\n"))
                lines.append(("class:muted", f"     {_card_field_detail(field, cards)}\n"))
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
                if index == 0:
                    lines.append(("class:section", "\n  Launch posture\n"))
                posture = str(value)
                current = config.load_launch_defaults()["posture"]
                active = "current" if posture == current else "      "
                lines.append((style, f"\n {marker} [{active}] {posture}\n"))
                lines.append(("class:muted", f"     {_POSTURE_LABELS.get(posture, '')}\n"))
            elif kind == "window":
                if index == len(config.LAUNCH_POSTURE_CHOICES):
                    lines.append(("class:section", "\n  Session window\n"))
                window = str(value)
                current = config.load_launch_defaults()["window"]
                active = "current" if window == current else "      "
                lines.append((style, f"\n {marker} [{active}] {window}\n"))
                lines.append(("class:muted", f"     {_WINDOW_LABELS.get(window, '')}\n"))
        return lines

    def _wide_home_text(self, width: int) -> StyleAndTextTuples:
        """Render the home cockpit as responsive columns on wide terminals."""
        fragments: StyleAndTextTuples = [("class:section", "\n Accounts\n")]
        account_blocks = []
        for account in self.accounts:
            usage = _usage_meter_lines(self.account_usage.get((account.agent, account.alias)))
            account_blocks.append(
                [("class:account", f" {account.agent.title()} {account.alias}")]
                + [(meter_style, f" {meter_text}") for meter_style, meter_text in usage]
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
        project_columns = self._project_columns(width)
        project_width = max(1, (width - 2 * (project_columns - 1)) // project_columns)
        project_items = [
            (index, root)
            for index, (kind, root) in enumerate(self.items)
            if kind == "project"
        ]
        for start in range(0, len(project_items), project_columns):
            blocks: list[tuple[int, list[tuple[str, str]]]] = []
            for index, root in project_items[start : start + project_columns]:
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
                            (
                                "class:muted",
                                f"   backlog {card_count} · bugs {bug_count}"
                                + (
                                    f" · continuity {self.project_pending.get(root, 0)} pending"
                                    if self.project_pending.get(root, 0)
                                    else ""
                                ),
                            ),
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
        fragments.extend(self._remote_catalog_notes_text())
        remote_items = [
            (index, project)
            for index, (kind, project) in enumerate(self.items)
            if kind == "remote_project"
        ]
        if remote_items:
            fragments.append(("class:section", " Remote projects\n"))
            for index, project in remote_items:
                marker = ">" if index == self.selected else " "
                style = "class:selected" if index == self.selected else "class:item"
                badge = "cloned, not registered" if project.is_local else "remote only"
                if index == self.selected:
                    fragments.append(("[SetCursorPosition]", ""))
                fragments.append((style, f" {marker} {project.name} · {badge}\n"))
                detail = project.current_focus or project.full_name
                fragments.append(("class:muted", f"   {detail}\n"))
            fragments.append(("", "\n"))
        utility_rows = [
            (index, kind)
            for index, (kind, _value) in enumerate(self.items)
            if kind in {"projection_sync", "fleet_review", "campaign"}
        ]
        for utility_index, kind in utility_rows:
            selected = utility_index == self.selected
            if selected:
                fragments.append(("[SetCursorPosition]", ""))
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if kind == "projection_sync":
                stale, unknown = _projection_counts(self.projection_records)
                summary = f"{stale} stale"
                if unknown:
                    summary += f" · {unknown} unknown"
                if not stale and not unknown:
                    summary = "all tracked projects in sync"
                fragments.append((style, f" {marker} Projection Sync\n"))
                fragments.append(("class:muted", f"   {summary} · Claude/Codex vs installed CLI\n"))
            elif kind == "fleet_review":
                fragments.append((style, f" {marker} Fleet Review\n"))
                fragments.append(
                    ("class:muted", "   Compare remote shipped truth with local working state\n")
                )
            else:
                fragments.append((style, f" {marker} Campaign\n"))
                fragments.append(
                    ("class:muted", "   Optional cross-project supervision — asks for outcome + targets\n")
                )
        return fragments

    def _account_summary_text(self) -> StyleAndTextTuples:
        if not self.accounts:
            return []
        lines: StyleAndTextTuples = [("class:section", "\n Accounts\n")]
        for account in self.accounts:
            usage = self.account_usage.get((account.agent, account.alias))
            lines.append(("class:account", f"  {account.agent.title()} {account.alias}\n"))
            for meter_style, meter_text in _usage_meter_lines(usage):
                lines.append((meter_style, f"    {meter_text}\n"))
        lines.append(("", "\n Projects\n"))
        return lines

    def _remote_catalog_notes_text(self) -> StyleAndTextTuples:
        """Surface the 'unavailable' and 'ignored' remote-catalog states as text,
        distinct from the selectable ``remote_project`` items themselves."""
        lines: StyleAndTextTuples = []
        for error in self.remote_errors:
            lines.append(("class:warning", f"\n  Remote catalog unavailable: {error}\n"))
        if self.remote_ignored:
            count = len(self.remote_ignored)
            lines.append((
                "class:muted",
                f"\n  {count} remote repo{'s' if count != 1 else ''} hidden via `horus ignore`\n",
            ))
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

    def _receipt_lines(self) -> list[str]:
        if self.receipt is None:
            return ["", "Receipt unavailable."]
        try:
            body = self.receipt.path.read_text(encoding="utf-8")
        except OSError:
            body = "Receipt could not be read."
        description = body.splitlines()
        for index, line in enumerate(description):
            if line.strip():
                if line.lstrip().startswith("# "):
                    description.pop(index)
                break
        return [
            "",
            f"[{self.receipt.date or 'undated'}]",
            self.receipt.title,
            "",
            *description,
            "",
        ]

    def _receipt_body_text(self) -> StyleAndTextTuples:
        fragments: StyleAndTextTuples = []
        for index, line in enumerate(self._receipt_lines()):
            if index == self.receipt_scroll:
                fragments.append(("[SetCursorPosition]", ""))
            if index == 1:
                style = "class:meta"
            elif index == 2:
                style = "class:card-title"
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

    def _load_project_skills(self) -> None:
        """Retain the canonical per-agent skill install states for the project frame.

        Read-only projection of ``skills.skill_states`` (the same detection behind
        ``skill_findings`` / the nudge) for both agents — no new scanning here.
        """
        self.project_skill_states = []
        if self.project is None:
            return
        try:
            self.project_skill_states = skills.skill_states(
                self.project, targets=("claude", "codex")
            )
        except OSError:
            return

    def _load_project_focus(self) -> None:
        """Retain the canonical PRD-first focus record for the project frame."""
        self.project_focus = {}
        if self.project is None:
            return
        try:
            self.project_focus = frontmatter.resolve_focus(self.project)
        except OSError:
            return

    def _load_project_requirements(self) -> None:
        """Retain the canonical read-only readiness result for the project frame."""
        self.project_requirements = None
        if self.project is None:
            return
        self.project_requirements = machine_requirements.inspect(self.project)

    def _load_fleet_review(self) -> None:
        """Build the canonical CLI review once; this screen only renders it."""
        self.fleet_review_record = None
        self.fleet_review_error = ""
        try:
            self.fleet_review_record = fleet_review.build(
                [project.as_posix() for project in self.projects]
            )
        except ValueError as exc:
            self.fleet_review_error = str(exc)

    def _load_projection_sync(self) -> None:
        """Retain the canonical per-project surface comparison for this frame."""
        self.projection_records = [
            (project, projection_sync.sync_state(project)) for project in self.projects
        ]

    def _projection_sync_body_text(self) -> StyleAndTextTuples:
        stale, unknown = _projection_counts(self.projection_records)
        fragments: StyleAndTextTuples = [
            (
                "class:muted",
                "\n  Read-only comparison of each Claude and Codex projection with "
                "the installed Horus CLI.\n",
            ),
            ("class:section", f"  {stale} stale · {unknown} unknown\n"),
        ]
        if not self.items:
            fragments.append(("class:muted", "\n  No tracked projects.\n"))
            return fragments
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                fragments.append(("[SetCursorPosition]", ""))
            if kind == "projection_curator":
                fragments.append((style, f"\n {marker} Start projection curator\n"))
                fragments.append(
                    (
                        "class:muted",
                        f"     Launch {Path(value).name} with a bounded, dirty-worktree-safe sync prompt\n",
                    )
                )
                continue
            if kind != "projection_project":
                continue
            project, state = value
            verdict = str(state.get("verdict", "unknown"))
            row_style = style if selected or verdict == "in_sync" else "class:warning"
            fragments.append((row_style, f"\n {marker} {project.name} · {verdict.replace('_', ' ')}\n"))
            fragments.append(
                (
                    "class:muted",
                    "     "
                    f"Claude {_projection_surface_text(state.get('claude'))} · "
                    f"Codex {_projection_surface_text(state.get('codex'))}\n",
                )
            )
        return fragments

    def _fleet_review_body_text(self) -> StyleAndTextTuples:
        if self.fleet_review_error:
            return [("class:muted", f"\n  Fleet review unavailable: {self.fleet_review_error}\n")]
        record = self.fleet_review_record
        if record is None:
            return [("class:muted", "\n  Fleet review unavailable.\n")]
        fragments: StyleAndTextTuples = [
            ("class:muted", f"\n  manifest: {record.manifest}\n"),
            (
                "class:muted",
                "  Remote shipped truth is never blended with local working state.\n",
            ),
        ]
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                fragments.append(("[SetCursorPosition]", ""))
            if kind == "curator":
                fragments.append((style, f"\n {marker} Start curator session\n"))
                fragments.append(
                    ("class:muted", f"     Resume {Path(value).name} as an ordinary project\n")
                )
                continue
            if kind != "review_project":
                continue
            project = value
            remote = project.remote
            fragments.append(
                (style, f"\n {marker} {project.id} [{project.manifest_status}]\n")
            )
            if remote.available:
                ref = f"{remote.ref}@{remote.sha[:8]}" if remote.sha else remote.ref
                fragments.append(
                    ("class:section", f"     REMOTE SHIPPED TRUTH · {remote.source} {ref}\n")
                )
                fragments.append(
                    ("class:muted", f"     focus: {' '.join(remote.current_focus.split()) or '-'}\n")
                )
                fragments.append(
                    (
                        "class:muted",
                        f"     capabilities {len(remote.capabilities)} · backlog "
                        f"{len(remote.backlog) if remote.backlog_mode == 'cards' else remote.backlog_mode}\n",
                    )
                )
                if remote.source_commits_since_continuity:
                    fragments.append(
                        (
                            "class:status",
                            "     WARNING: "
                            f"{remote.source_commits_since_continuity} newer source commit(s)\n",
                        )
                    )
            else:
                fragments.append(
                    ("class:muted", f"     REMOTE SHIPPED TRUTH unavailable: {remote.note}\n")
                )
            fragments.append(("class:section", "     LOCAL WORKING STATE\n"))
            fragments.append(("class:muted", f"     {project.local.summary}\n"))
        return fragments

    def _mission_body_text(self) -> StyleAndTextTuples:
        """Mission Control (`m`): read-mostly observability of the autonomous loop —
        execution readiness + what will run (armed) + what ran (recent, with glyphs).
        Renders from cached `_load_control` state; no toggles live here."""
        frags: StyleAndTextTuples = [("class:section", "\n  Execution readiness\n")]
        if not self.control_sched_ok:
            frags.append(("class:warning",
                          "     scheduler: unavailable here (needs systemd --user timers)\n"))
        else:
            frags.append(("class:muted", "     scheduler: available\n"))
        if self.control_linger is True:
            frags.append(("class:muted", "     linger: on — services survive logout\n"))
        elif self.control_linger is False:
            frags.append(("class:warning",
                          "     linger: OFF — away services die at logout · `loginctl enable-linger`\n"))
        else:
            frags.append(("class:muted", "     linger: unknown\n"))
        live_envelopes = [e for e in self.control_envelopes if e[2] == "live"]
        if live_envelopes:
            for name, expires, _state in live_envelopes:
                frags.append(("class:muted",
                              f"     envelope {name} · expires {expires} · revoke: `horus envelope revoke {name}`\n"))
        else:
            frags.append(("class:muted", "     no live dispatch envelope\n"))
        # Revoked/expired envelopes are NOT authorizations — mark them so the pane
        # never reads a dead envelope as standing readiness.
        for name, expires, state in self.control_envelopes:
            if state != "live":
                tag = "REVOKED" if state == "revoked" else f"EXPIRED {expires}"
                frags.append(("class:warning", f"     envelope {name} · {tag} — not a live authorization\n"))

        act = self.control_activity
        frags.append(("class:section", "\n  Armed dispatches\n"))
        if act is not None and act.armed:
            for item in act.armed:
                state = "halted" if item.halted else ("fired" if item.fired else "pending")
                frags.append(("class:muted",
                              f"     {activity.ARMED} {item.id}  {state}  {item.when}  {item.description}\n"))
                # A fired timer shows what the worker DID, not just that it ran.
                outcome = act.outcomes.get(item.id)
                if outcome is not None:
                    frags.append(("class:muted",
                                  f"        └─ {outcome.glyph} {activity.outcome_summary(outcome)}\n"))
        else:
            frags.append(("class:muted", "     (none)\n"))
        frags.append(("class:section", "\n  Recent runs\n"))
        if act is not None and act.ran:
            for r in act.ran:
                frags.append(("class:muted", f"     {r.glyph} {r.card or '(card?)'}  {r.account}  {r.status}\n"))
        else:
            frags.append(("class:muted", "     (none dispatched under an envelope yet)\n"))
        return frags

    def _settings_body_text(self) -> StyleAndTextTuples:
        """Settings (`t`): machine feature toggles — on/off switches the pane triggers via
        existing primitives. Every on/off feature (keep-warm, listener, notify sink, and
        future hermes/proxy integrations) lives here; the items carry the selection markers."""
        frags: StyleAndTextTuples = []
        if not self.control_sched_ok:
            frags.append(("class:warning",
                          "\n  Scheduling unavailable here (needs systemd --user timers) — "
                          "service toggles are inert.\n"))
        frags.append(("class:section", "\n  Machine feature toggles\n"))
        for index, (kind, value) in enumerate(self.items):
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                frags.append(("[SetCursorPosition]", ""))
            if kind == "ctl_listener":
                box = "x" if self.control_listener_active else " "
                frags.append((style, f"\n {marker} [{box}] Steering listener\n"))
                state = ("active" if self.control_listener_active
                         else ("installed (not running)" if self.control_listener_installed else "off"))
                frags.append(("class:muted", f"       inbound Telegram steering · {state}\n"))
            elif kind == "ctl_listener_restart":
                frags.append((style, f"\n {marker}     ↻ restart listener (adopt an upgraded CLI)\n"))
            elif kind == "ctl_keepwarm" and isinstance(value, str):
                box = "x" if self.control_keepwarm.get(value) else " "
                frags.append((style, f"\n {marker} [{box}] Keep-warm · {value}  (Tokenmaxxing)\n"))
                frags.append(("class:muted", "       re-warms the 5h window after each reset\n"))
            elif kind == "ctl_notify_test":
                frags.append((style, f"\n {marker}     ⇢ send a test escalation (sink: {self.control_sink})\n"))
            elif kind == "ctl_proxy":
                st = self.control_proxy
                box = "x" if (st and st.enabled) else " "
                frags.append((style, f"\n {marker} [{box}] GPT via proxy (CLIProxyAPI)\n"))
                if st is None:
                    detail = "status unavailable"
                elif st.enabled:
                    detail = f"ON — proxied launches get Claude + GPT ({st.model_count} models)"
                elif st.ready_to_enable:
                    detail = f"ready ({', '.join(st.providers)} logged in) — Enter to enable"
                elif not st.docker:
                    detail = "needs Docker installed"
                else:
                    detail = "run `horus proxy login codex` (and `claude`) first"
                frags.append(("class:muted", f"       {detail}\n"))
            elif kind == "ctl_remote_control":
                box = "x" if self.control_remote_control else " "
                frags.append((style, f"\n {marker} [{box}] Remote Control on launch (Claude)\n"))
                detail = ("new Claude sessions are phone-attachable at spawn"
                          if self.control_remote_control
                          else "off — enable per launch with `open --remote-control`")
                frags.append(("class:muted", f"       {detail}\n"))
            elif kind == "ctl_backlog_group_by":
                label = backlog_tree.GROUP_BY_LABELS.get(self.control_backlog_group_by, self.control_backlog_group_by)
                frags.append((style, f"\n {marker}     ⇢ Backlog default group-by: {label}  (Enter cycles)\n"))
                frags.append(("class:muted", "       what the backlog list opens to; g cycles it live\n"))
        return frags

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

    def _skills_body_text(self) -> StyleAndTextTuples:
        fragments: StyleAndTextTuples = [
            (
                "class:muted",
                "\n  Bundled skills per agent — read-only projection of "
                "skills.skill_findings; never auto-written.\n",
            ),
        ]
        if not self.items:
            fragments.append(("class:muted", "\n  No bundled skills detected.\n"))
            return fragments
        current_target: str | None = None
        for index, (_kind, state) in enumerate(self.items):
            if state.target != current_target:
                current_target = state.target
                fragments.append(("class:section", f"\n  {current_target.title()}\n"))
            selected = index == self.selected
            marker = ">" if selected else " "
            style = "class:selected" if selected else "class:item"
            if selected:
                fragments.append(("[SetCursorPosition]", ""))
            label, detail = _skill_state_label(state)
            fragments.append((style, f"\n {marker} {state.name}  —  {label}\n"))
            if detail:
                fragments.append(("class:muted", f"     {detail}\n"))
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
        if self.screen == "toggles":
            text = (
                " ↑↓ · Enter toggle · Esc back"
                if narrow
                else " ↑↓ select   Enter toggle feature / run action   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "mission":
            text = " ↑↓ read · Esc back" if narrow else " ↑↓/swipe read   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen == "backlog":
            text = (
                " ↑↓ · Enter open/expand · g group · p priority · f fields · Esc"
                if narrow
                else " ↑↓/swipe scroll   Enter open / expand   g group-by   p priority   f fields   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "card_priority":
            text = (
                " ↑↓ · Enter set · Esc back"
                if narrow
                else " ↑↓ select   Enter set priority   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "receipts":
            text = " ↑↓ · Enter open · Esc back" if narrow else " ↑↓/swipe scroll   Enter open (read-only)   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen == "receipt":
            text = " ↑↓ read · Esc back" if narrow else " ↑↓/swipe read   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen == "backlog_fields":
            text = (
                " ↑↓ · Enter toggle · Esc back"
                if narrow
                else " ↑↓/swipe select   Enter toggle (saved for every project)   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "capabilities":
            text = " ↑↓ scroll · Esc back" if narrow else " ↑↓/swipe scroll   Esc back   q quit"
            return [("class:footer", text)]
        if self.screen == "skills":
            text = (
                " ↑↓ scroll · Esc back"
                if narrow
                else " ↑↓/swipe scroll   read-only   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "fleet_review":
            text = (
                " ↑↓ · Enter curator · Esc back"
                if narrow
                else " ↑↓/swipe review   Enter start curator   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen == "projection_sync":
            text = (
                " ↑↓ · Enter curator · u refresh · Esc"
                if narrow
                else " ↑↓/swipe review   Enter start curator   u refresh   Esc back   q quit"
            )
            return [("class:footer", text)]
        if self.screen in {"projects", "accounts"}:
            text = (
                " ↑↓ · f fleet · u refresh · m mission · t settings · q"
                if narrow
                else " ↑↓/swipe · Enter · f fleet · u refresh · Esc · s sessions · d defaults · m mission · t settings · q quit"
            )
            return [("class:footer", text)]
        text = (
            " ↑↓ scroll · s sessions · m mission · t settings · q"
            if narrow
            else " ↑↓/swipe scroll   Enter open   Esc back   s sessions   d defaults   m mission   t settings   q quit"
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
        "warning": "bold #e3b341",
        "section": "bold #b8c7d1",
        "account": "#d7dce2",
        "session": "#9fc4d7",
        "card-title": "bold #ffffff",
        "status": "#9fc4d7 bg:#17202a",
        "footer": "#aeb8c2 bg:#20242b",
        # Usage meters — same green/yellow/red capacity bands as the status bar.
        "usage-ok": "#3fb950",
        "usage-warn": "#e3b341",
        "usage-high": "#f85149",
        # Backlog visual guidance: branch umbrellas + priority dots.
        "branch": "bold #6cb6ff",
        "prio-high": "#f85149",
        "prio-medium": "#e3b341",
        "prio-low": "#8c98a5",
    }
)


def run() -> int:
    """Run frames until quit, suspending the alternate screen for agent commands."""
    status = ""
    pending_campaign: tuple[Path, str] | None = None
    while True:
        ui = TerminalUI(status=status)
        if pending_campaign is not None:
            project, prompt_text = pending_campaign
            pending_campaign = None
            if project in ui.projects:
                ui.project = project
                ui.pending_mode = "resume"
                ui.pending_card = None
                ui.pending_prompt = prompt_text
                ui.pending_origin = "projects"
                ui._show("accounts")
        result = ui.application.run()
        if result == "quit":
            return 0
        if result == "interrupt":
            return 130
        if isinstance(result, _Launch):
            defaults = config.load_launch_defaults()
            prompt = _launch_prompt(result)
            # Toggle on → every TUI Claude launch runs through the proxy (any
            # account); per-launch env injection, never a settings.json rewrite.
            proxied = result.agent == "claude" and proxy.load_state().get("enabled", False)
            # `new-window` opens the session beside the TUI on a real desktop;
            # it resolves to takeover on mobile/SSH so a phone never gets a
            # broken window (terminal_sessions.resolve_window_launch).
            new_window = terminal_sessions.resolve_window_launch(defaults["window"])
            if new_window:
                launched = terminal_sessions.launch_window(
                    agent=result.agent,
                    project_dir=result.project,
                    account=result.account,
                    prompt=prompt,
                    posture=defaults["posture"],
                    model=result.model,
                    effort=result.effort,
                    proxied=proxied,
                )
            else:
                launched = _launch(
                    target=terminal_sessions.default_target(),
                    agent=result.agent,
                    root=result.project,
                    account=result.account,
                    prompt=prompt,
                    posture=defaults["posture"],
                    model=result.model,
                    effort=result.effort,
                    proxied=proxied,
                )
            if not launched.ok:
                status = f"Launch failed: {launched.error}"
            elif new_window:
                status = f"Session {launched.session_id[:8]} opened in a new window."
            else:
                status = f"Session {launched.session_id[:8]} returned to Horus."
        elif isinstance(result, _EditCard):
            status = _edit_card(result.project, result.card, review=result.review)
        elif isinstance(result, _Attach):
            error = terminal_sessions.attach_session(result.session_id)
            status = error or f"Detached from {result.session_id[:8]}."
        elif isinstance(result, _Stop):
            error = terminal_sessions.stop_session(result.session_id)
            status = error or f"Closed {result.session_id[:8]}."
        elif isinstance(result, _RemoteStart):
            status = _start_remote(result)
        elif isinstance(result, _Campaign):
            outcome = _run_campaign_prompt(_projects())
            pending_campaign = outcome
            status = (
                "Campaign brief ready — choose an agent/account for the cockpit."
                if outcome is not None
                else "Campaign cancelled — no outcome provided."
            )


def _cockpit_project(projects: list[Path]) -> Path | None:
    """The registered `horus-agent` workspace, if any — the compatible cockpit
    that the optional Campaign entry point supervises other projects from."""
    return next((project for project in projects if project.name == "horus-agent"), None)


def _projects() -> list[Path]:
    return [
        root
        for raw in config.load_projects()
        if (root := Path(raw).resolve()).is_dir() and (root / ".horus").is_dir()
    ]


def _remote_projects() -> tuple[
    list["github_catalog.RemoteProject"], list["github_catalog.RemoteProject"], list[str]
]:
    """Cache-only remote Horus project listing: (visible, ignored, error notes).

    Reads only the on-disk cache that ``horus start`` / the dashboard's background
    refresh already populate — never calls ``gh`` — so the TUI's first paint never
    blocks on a network round trip. Already-registered projects are dropped since
    they already appear as ``project`` items.
    """
    local = config.load_projects()
    all_projects: list[github_catalog.RemoteProject] = []
    errors: list[str] = []
    for owner in config.load_github_owners():
        cached = github_catalog.load_cache(owner, local_projects=local)
        if cached is None:
            continue
        all_projects.extend(cached.projects)
        if cached.error:
            when = f" at {cached.error_at}" if cached.error_at else ""
            errors.append(f"{owner}: last refresh failed{when}: {cached.error}")
    unregistered = github_catalog.drop_registered(all_projects, registered=local)
    visible, hidden = github_catalog.filter_ignored(unregistered)
    return visible, hidden, errors


def _projection_counts(records: list[tuple[Path, dict]]) -> tuple[int, int]:
    """Return stale and unknown counts without treating unknown as actionable drift."""
    unknown = sum(state.get("verdict") == "unknown" for _project, state in records)
    stale = sum(
        state.get("verdict") not in {"in_sync", "unknown"}
        for _project, state in records
    )
    return stale, unknown


def _skill_state_label(state: skills.SkillState) -> tuple[str, str]:
    """Presentation label + optional detail for one skill state (no detection here).

    Maps the canonical ``skills.SKILL_*`` status to the card's four rows:
    installed (vX) / outdated (vX→vY) / available, not installed / unversioned.
    """
    if state.status == skills.SKILL_INSTALLED:
        return f"installed (v{state.installed_version})", ""
    if state.status == skills.SKILL_OUTDATED:
        return (
            f"outdated (v{state.installed_version} → v{state.bundled_version})",
            f"refresh: {state.refresh_command}",
        )
    if state.status == skills.SKILL_MISSING:
        return "available, not installed", f"install: {state.refresh_command}"
    # SKILL_UNVERSIONED — customized/unmarked; shown as such, never flagged to overwrite.
    return "unversioned / customized", "left as-is — never auto-flagged for overwrite"


def _skill_summary(states: list[skills.SkillState]) -> str:
    """One-line roll-up of skill states for the project menu row."""
    if not states:
        return "no bundled skills detected"
    outdated = sum(s.status == skills.SKILL_OUTDATED for s in states)
    missing = sum(s.status == skills.SKILL_MISSING for s in states)
    unversioned = sum(s.status == skills.SKILL_UNVERSIONED for s in states)
    parts: list[str] = []
    if outdated:
        parts.append(f"{outdated} outdated")
    if missing:
        parts.append(f"{missing} not installed")
    if unversioned:
        parts.append(f"{unversioned} unversioned")
    if not parts:
        return "all bundled skills installed · claude/codex"
    return " · ".join(parts) + " · claude/codex"


def _projection_surface_text(value: object) -> str:
    if not isinstance(value, dict):
        return "unknown"
    status = str(value.get("status", "unknown"))
    pending = value.get("pending", 0)
    return f"{status} ({pending} pending)" if pending else status


def _projection_curator_prompt(records: list[tuple[Path, dict]]) -> str:
    """Build a bounded handoff for the optional fleet curator workspace."""
    drift = [
        (project, state)
        for project, state in records
        if state.get("verdict") != "in_sync"
    ]
    rows = "\n".join(
        f"- {project.name}: {state.get('verdict', 'unknown')} "
        f"(Claude {_projection_surface_text(state.get('claude'))}; "
        f"Codex {_projection_surface_text(state.get('codex'))})"
        for project, state in drift
    ) or "- none: all tracked projects currently report in_sync"
    return (
        "Resume Horus as the fleet projection curator. The installed CLI's read-only "
        "projection report is:\n"
        f"{rows}\n\n"
        "For each actionable target separately: fetch --all --prune; verify its default "
        "branch against origin; read its instructions and canonical Horus continuity; "
        "confirm the local Horus version floor; and refresh only Horus-owned Claude/Codex "
        "projection artifacts through that project's supported upgrade workflow. Preserve "
        "all user work, use an isolated worktree when the registered checkout is dirty, and "
        "land each project through its own branch and PR with required checks observed. Never "
        "combine repositories, overwrite user-owned prose, or treat unknown/cli_outdated as "
        "permission to write. Re-run the read-only projection report and stop when every "
        "reachable actionable target is in_sync."
    )


_PRIORITY_STYLE = {
    "now": "class:prio-high", "high": "class:prio-high", "urgent": "class:prio-high",
    "medium": "class:prio-medium", "med": "class:prio-medium",
    "low": "class:prio-low", "later": "class:prio-low", "deferred": "class:prio-low",
}


def _priority_dot(priority: str | None) -> tuple[str, str]:
    """A colored ``●`` for a card's priority so the backlog scans at a glance —
    red high, yellow medium, dim low. A card with no priority gets no dot, keeping
    unprioritized rows clean and closest to the classic view."""
    if not priority:
        return ("", "")
    return (_PRIORITY_STYLE.get(priority.strip().lower(), "class:muted"), "● ")


def _card_field_suffix(card: backlog.Card, fields: list[str]) -> str:
    """The ` · <key> <value>` run appended to a backlog row for the picked fields.

    A field the card doesn't carry (or carries empty) is skipped entirely, so a card
    missing one reads as a shorter row rather than showing a blank or "None" slot.
    With no fields picked this is "" and the row is byte-for-byte the classic one.
    """
    parts = [f" · {key} {card.field_value(key)}" for key in fields if card.field_value(key)]
    return "".join(parts)


def _card_field_choices(cards: list[backlog.Card], configured: list[str]) -> list[str]:
    """Pickable frontmatter keys: whatever these cards actually carry, plus any
    already-picked key — a field picked elsewhere stays visible (and removable) in a
    project whose cards happen not to use it."""
    keys = {key for card in cards for key, value in card.fields if value}
    keys.update(configured)
    return sorted(keys)


def _card_field_detail(field: str, cards: list[backlog.Card]) -> str:
    """One muted line under a picker row: how many cards carry the field, and a
    sample value, so the choice is concrete before it's made."""
    values = [card.field_value(field) for card in cards if card.field_value(field)]
    if not values:
        return "on no card here"
    sample = values[0]
    return f"on {len(values)} of {len(cards)} cards · e.g. {sample}"


def _open_cards(root: Path) -> list[backlog.Card]:
    try:
        cards = [card for card in backlog.load_cards(root) if card.status not in {"done", "shipped"}]
    except (OSError, ValueError):
        return []
    return sorted(cards, key=backlog.readiness_sort_key)


def _project_tree(root: Path) -> backlog_tree.Tree:
    try:
        return backlog_tree.build_tree(root)
    except (OSError, ValueError):
        return backlog_tree.Tree()


def _receipts(root: Path) -> list[backlog_tree.Receipt]:
    try:
        return backlog_tree.list_receipts(root)
    except OSError:
        return []


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


def _agent_models(agent: str) -> list[str]:
    """The `--model` selectors valid for `agent`, straight from its adapter —
    never a list hardcoded here, so a new adapter model shows up automatically."""
    try:
        return list(adapters.get_adapter(agent).KNOWN_MODELS)
    except KeyError:
        return []


def _resolve_recommended_model(tier: str, models: list[str]) -> str | None:
    """Resolve a card's `tier:` to one of `models`, via the SAME tier->model
    normalization `horus capabilities` uses (`datums.canonical_model_name`),
    so this stays correct once vendor-neutral tiers make the mapping
    per-provider. A bare Claude family alias (today's tier vocabulary) matches
    a Claude account's own model list directly; a generic alias like
    `gpt-5.6` resolves to its canonical variant (`gpt-5.6-sol`) for Codex."""
    if not tier:
        return None
    if tier in models:
        return tier
    canonical = datums.canonical_model_name(tier)
    if canonical and canonical in models:
        return canonical
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


def _int_pct(value: float | None) -> int | None:
    """Floor a numeric percent to an int; None for missing/non-numeric."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _usage_meter_lines(snapshot: usage_snapshot.UsageSnapshot | None) -> StyleAndTextTuples:
    """Home-view usage as colored ``label ██░░ NN% ↻ reset`` meter lines, reusing
    the status bar's own bar + capacity level (`statusline.usage_bar`/`usage_level`)
    so the cockpit and the status line read the same. An unknown window is a dim
    dash — never a misleading zero bar."""
    def meter(label: str, percent: float | None, resets_at: str | None) -> tuple[str, str]:
        pct = _int_pct(percent)
        if pct is None:
            return ("class:muted", f"{label:<6} --")
        reset = f" ↻ {resets_at}" if resets_at else ""
        # Pad the label so the 5h and weekly bars start at the same column.
        return (f"class:usage-{statusline.usage_level(pct)}", f"{label:<6} {statusline.usage_bar(pct)} {pct:3d}%{reset}")

    if snapshot is None:
        return [("class:muted", "5h --"), ("class:muted", "weekly --")]
    return [
        meter("5h", snapshot.percent, snapshot.resets_at),
        meter("weekly", snapshot.weekly_percent, snapshot.weekly_resets_at),
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


def _grid_nav_target(selected: int, count: int, projects: int, cols: int, direction: str) -> int | None:
    """Next selection index for arrow navigation over the projects home.

    Layout mirrored from the wide render: items ``[0, projects)`` are a ``cols``-wide
    row-major grid; items ``[projects, count)`` are a single-column tail stacked
    below it (remote projects, Projection Sync, Fleet Review, Campaign). ``down``/
    ``up`` move a visual row, ``left``/``right`` move a column. Returns the new index,
    the same index for a no-op, or ``None`` for ``left`` with no column to its left
    (the caller then performs Back — preserving left-as-Back on a single list).

    With ``cols == 1`` (narrow/mobile, or any non-projects list) this reduces to the
    old linear behavior: down/up = ±1, right = no-op, left = Back.
    """
    if count == 0:
        return None if direction == "left" else selected
    i = max(0, min(count - 1, selected))
    in_grid = cols > 1 and i < projects
    if direction == "right":
        if in_grid and i % cols < cols - 1 and i + 1 < projects:
            return i + 1
        return i
    if direction == "left":
        if in_grid and i % cols > 0:
            return i - 1
        return None  # no left column → Back
    if direction == "down":
        if in_grid:
            if i + cols < projects:
                return i + cols
            if projects < count:            # off the last project row → into the tail
                return projects
            return i
        return min(count - 1, i + 1)         # tail or single list: linear
    if direction == "up":
        if cols > 1 and i == projects:       # first tail item → back up into the grid
            return projects - 1
        if in_grid:
            return i - cols if i - cols >= 0 else i
        return max(0, i - 1)
    return i


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


def _start_remote(action: "_RemoteStart") -> str:
    """Clone (if needed) + register + refresh projections for a selected remote
    project, reusing ``remote_start.start_github_project`` — the same primitive
    the CLI's ``horus start github:owner/repo`` uses. No second clone/register
    path is introduced here."""
    try:
        result = remote_start.start_github_project(f"github:{action.project.full_name}")
    except RuntimeError as exc:
        return f"Remote start failed: {exc}"
    verb = "Cloned and registered" if result.cloned else "Registered"
    return f"{verb} {result.project.name} at {result.path}. Select it to resume."


def _run_campaign_prompt(projects: list[Path]) -> tuple[Path, str] | None:
    """Between-frames flow for the optional Campaign entry point: ask the owner
    for the outcome and target set in plain text — never inventing either. The
    cockpit's own account/agent is still chosen normally on the accounts screen
    that follows, so this never auto-selects a model or account."""
    cockpit = _cockpit_project(projects)
    if cockpit is None:
        return None
    outcome = input("\nCampaign outcome - what should be true when this campaign is done? ").strip()
    if not outcome:
        return None
    raw_targets = input(
        "Target projects (comma-separated registered names, blank = cockpit only): "
    ).strip()
    names = [name.strip() for name in raw_targets.split(",") if name.strip()]
    known = {project.name: project for project in projects}
    targets = [known[name] for name in names if name in known]
    unknown = [name for name in names if name not in known]
    if unknown:
        print(f"Ignoring unrecognized project name(s): {', '.join(unknown)}")
    prompt = routines.campaign_prompt(
        outcome=outcome,
        cockpit=cockpit.name,
        targets=[project.name for project in targets],
    )
    return cockpit, prompt


def _card_prompt(root: Path, card: backlog.Card) -> str:
    return (
        f"{routines.resume_prompt(root)}\n\n"
        f"Work on this backlog card first: {card.title}. Read the full card at "
        f"`.horus/backlog/{card.path.name}` before changing code, and treat it as the "
        "first item for this session."
    )


def _launch_prompt(result: _Launch) -> str:
    """The initial prompt for a launched session — purely a question of WHAT CONTEXT
    the launch loads.

    A card launch loads that card's scope; a resume loads the authored handoff; a
    fresh launch loads NOTHING and returns "" so the owner types into an empty
    session. Nothing is prepended: there is no mode preamble to spend a turn on.
    Kept module-level and pure so the wiring is testable without driving the app."""
    if result.prompt_override is not None:
        return result.prompt_override
    if result.card is not None:
        return _card_prompt(result.project, result.card)
    return routines.resume_prompt(result.project) if result.mode == "resume" else ""


def _launch(
    *,
    target: str,
    agent: str,
    root: Path,
    account: str | None,
    prompt: str,
    posture: str = "default",
    model: str | None = None,
    effort: str | None = None,
    proxied: bool = False,
):
    kwargs = {
        "agent": agent,
        "project_dir": root,
        "account": account,
        "prompt": prompt,
        "posture": posture,
        "model": model,
        "effort": effort,
        "proxied": proxied,
    }
    if target == terminal_sessions.TMUX:
        return terminal_sessions.launch_tmux(**kwargs)
    return terminal_sessions.run_attached(**kwargs)
