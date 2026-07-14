"""Project-declared, read-only machine readiness.

Projects may commit ``.horus/requirements.md`` with a narrow YAML-like front
matter shape::

    ---
    kind: machine-requirements
    tools:
      - name: Fabric CLI
        probe: fab
        install: uv tool install fab
        needed_for: Fabric workspace operations
    configs:
      - name: Power BI credentials
        probe: ~/.config/pbir/credentials.json
        install: Configure pbir credentials
        needed_for: authenticated Power BI work
    ---

The parser is intentionally dependency-free and accepts only those scalar list
fields. Most importantly, a committed probe is never executed: tool probes go
through :func:`shutil.which`, while config probes are path-existence checks.
Non-probeable requirements belong in the Markdown body as prose.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple


REQUIREMENTS_FILE = ".horus/requirements.md"
_SECTIONS = {"tools": "tool", "configs": "config"}
_ITEM_KEYS = {"name", "probe", "install", "needed_for"}
_SAFE_TOOL_PROBE = re.compile(r"^[A-Za-z0-9_.+-]+$")


@dataclass(frozen=True)
class Requirement:
    category: str
    name: str
    probe: str
    install: str
    needed_for: str
    available: bool


@dataclass(frozen=True)
class Report:
    path: Path
    declared: bool
    requirements: tuple[Requirement, ...] = ()
    issues: tuple[str, ...] = ()

    @property
    def missing(self) -> tuple[Requirement, ...]:
        return tuple(item for item in self.requirements if not item.available)

    @property
    def ready(self) -> bool:
        return self.declared and not self.issues and not self.missing


class Finding(NamedTuple):
    level: str
    message: str


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _front_matter(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], ["missing opening frontmatter fence"]
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], []
    return [], ["missing closing frontmatter fence"]


def _parse_declaration(text: str) -> tuple[list[tuple[str, dict[str, str]]], list[str]]:
    lines, issues = _front_matter(text)
    if issues:
        return [], issues

    kind = ""
    section = ""
    current: dict[str, str] | None = None
    records: list[tuple[str, dict[str, str]]] = []

    def finish() -> None:
        nonlocal current
        if current is not None:
            records.append((section, current))
            current = None

    for number, raw in enumerate(lines, start=2):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent == 0:
            finish()
            if ":" not in stripped:
                issues.append(f"line {number}: expected key: value")
                section = ""
                continue
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = _scalar(value)
            if key == "kind":
                kind = value
                section = ""
            elif key in _SECTIONS and value in {"", "[]"}:
                section = key
            else:
                issues.append(f"line {number}: unsupported top-level field {key!r}")
                section = ""
            continue

        if not section:
            issues.append(f"line {number}: list item is not under tools: or configs:")
            continue
        if stripped.startswith("- "):
            finish()
            current = {}
            stripped = stripped[2:].strip()
        if current is None:
            issues.append(f"line {number}: expected a '- name: ...' list item")
            continue
        if not stripped:
            continue
        if ":" not in stripped:
            issues.append(f"line {number}: expected key: value")
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        if key not in _ITEM_KEYS:
            issues.append(f"line {number}: unsupported requirement field {key!r}")
            continue
        current[key] = _scalar(value)

    finish()
    if kind != "machine-requirements":
        issues.append("kind must be 'machine-requirements'")
    return records, issues


def inspect(
    project_root: Path,
    *,
    which: Callable[[str], str | None] | None = None,
    path_exists: Callable[[Path], bool] | None = None,
) -> Report:
    """Parse and probe one project's declaration without executing commands."""
    path = project_root / REQUIREMENTS_FILE
    if not path.is_file():
        return Report(path=path, declared=False)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Report(path=path, declared=True, issues=(f"cannot read declaration: {exc}",))

    records, parse_issues = _parse_declaration(text)
    issues = list(parse_issues)
    tool_lookup = which or shutil.which
    exists = path_exists or Path.exists
    requirements: list[Requirement] = []

    for section, fields in records:
        category = _SECTIONS[section]
        name = fields.get("name", "").strip()
        probe = fields.get("probe", "").strip()
        if not name or not probe:
            issues.append(f"{section} item requires non-empty name and probe")
            continue
        unknown = set(fields).difference(_ITEM_KEYS)
        if unknown:
            issues.append(f"{name}: unsupported fields: {', '.join(sorted(unknown))}")
            continue

        if category == "tool":
            if not _SAFE_TOOL_PROBE.fullmatch(probe):
                issues.append(
                    f"{name}: tool probe must be one executable name (commands are never executed)"
                )
                continue
            available = tool_lookup(probe) is not None
        else:
            expanded = Path(os.path.expandvars(probe)).expanduser()
            candidate = expanded if expanded.is_absolute() else project_root / expanded
            available = exists(candidate)

        requirements.append(
            Requirement(
                category=category,
                name=name,
                probe=probe,
                install=fields.get("install", "").strip(),
                needed_for=fields.get("needed_for", "").strip(),
                available=available,
            )
        )

    return Report(
        path=path,
        declared=True,
        requirements=tuple(requirements),
        issues=tuple(issues),
    )


def _missing_detail(item: Requirement) -> str:
    detail = item.name
    if item.needed_for:
        detail += f" (needed for {item.needed_for})"
    if item.install:
        detail += f" — install: {item.install}"
    return detail


def warning_text(report: Report) -> str:
    """Canonical user-facing warning shared by resume, dashboard, and TUI."""
    parts: list[str] = []
    if report.missing:
        parts.append("⚠ this machine is missing: " + "; ".join(_missing_detail(i) for i in report.missing))
    if report.issues:
        parts.append("⚠ machine requirements could not be fully checked: " + "; ".join(report.issues))
    return "\n".join(parts)


def findings(report: Report) -> list[Finding]:
    """Doctor/dashboard findings for a previously inspected report."""
    if not report.declared:
        return []
    result = [Finding("warn", f"requirements.md: {issue}") for issue in report.issues]
    result.extend(
        Finding("warn", f"machine requirement missing: {_missing_detail(item)}")
        for item in report.missing
    )
    if not result:
        total = len(report.requirements)
        result.append(Finding("ok", f"machine requirements ready ({total}/{total} available)"))
    return result
