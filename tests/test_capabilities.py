"""Tests for the experimental `horus capabilities` fleet capability catalog.

Covers: Shipped-ledger extraction from imperfect PRD markdown (bullet, numbered,
bold-paragraph shapes, qualified headings),
the argparse CLI-surface walker on a small fixture parser, cheap cross-reference
matching, and the read-only/idempotence invariants against an on-disk fixture
fleet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from horus import capabilities
from horus.cli import main

# A PRD whose Shipped uses the bold-paragraph shape (this repo's own live PRD
# style) and mentions a CLI command inline.
ALPHA_PRD = """---
status: active
current_focus: "wire alpha to beta"
---

# alpha — PRD

## Backlog

- **First item** with a wrapped
  continuation line that has no marker.
1. Second item as a numbered entry.

## Shipped

One line per capability; details in git history.
**Fleet dispatch view**: `horus fleet` prints one line per registered project.
**Bridge v2** hardened the alpha-beta bridge.

## Rules

- Not extracted by this module.
"""

# A PRD whose Shipped uses plain bullets instead of bold paragraphs.
BETA_PRD = """---
status: active
---

# beta-svc — PRD

## Shipped

- **Only** a plain bullet.
- Another plain bullet.
"""

DELTA_PRD = """---
status: active
---

# delta — PRD

## Vision

A tabletop RPG engine that runs entirely inside **Claude Code as the runtime** — no
app to deploy, no API keys. The rulebook is grown: rules are proposed by the AI and
ratified by the table.

## Shipped

- **Map canvas** renders tokens and fog of war.
"""

# A PRD with wrapped bullets in Shipped — regression test for truncation bug.
GAMMA_PRD_WRAPPED_BULLETS = """---
status: active
---

# gamma — PRD

## Shipped

- **Release → hosted auto-deploy + pinned-install switch (2026-07-09).** Closes item 5
  of the roadmap; pinned-install switch flips hosts to the released wheel.
- Simpler single-line bullet for contrast.
- Top-level with nested sub-detail
  - Indented sub-item under the parent.
  - Another sub-item.
"""


def test_section_matches_qualified_heading():
    body = capabilities.frontmatter.parse(ALPHA_PRD).body
    assert capabilities._section(body, "Shipped").strip().startswith("One line per capability")
    assert capabilities._section(body, "Backlog")
    assert capabilities._section(body, "Missing") == ""


def test_top_level_items_bullets_and_numbers():
    body = capabilities.frontmatter.parse(ALPHA_PRD).body
    items = capabilities._top_level_items(capabilities._section(body, "Backlog"))
    assert items == [
        "**First item** with a wrapped continuation line that has no marker.",
        "Second item as a numbered entry.",
    ]


def test_shipped_lines_bold_paragraph_fallback():
    body = capabilities.frontmatter.parse(ALPHA_PRD).body
    items = capabilities.shipped_lines(body)
    # Non-bold preamble line is dropped; each bold entry is one item.
    assert items == [
        "**Fleet dispatch view**: `horus fleet` prints one line per registered project.",
        "**Bridge v2** hardened the alpha-beta bridge.",
    ]


def test_shipped_lines_plain_bullets():
    body = capabilities.frontmatter.parse(BETA_PRD).body
    assert capabilities.shipped_lines(body) == ["**Only** a plain bullet.", "Another plain bullet."]


def test_shipped_lines_wrapped_bullets_regression():
    """Regression: multi-line bullets must extract as full joined text, not truncated.
    Also verifies that top-level bullets with nested sub-items fold them in correctly."""
    body = capabilities.frontmatter.parse(GAMMA_PRD_WRAPPED_BULLETS).body
    items = capabilities.shipped_lines(body)
    assert len(items) == 3
    # First item: wrapped bullet with continuation line must be fully extracted.
    assert items[0] == (
        "**Release → hosted auto-deploy + pinned-install switch (2026-07-09).** "
        "Closes item 5 of the roadmap; pinned-install switch flips hosts to the released wheel."
    )
    # Second item: simple single-line bullet.
    assert items[1] == "Simpler single-line bullet for contrast."
    # Third item: top-level bullet with nested sub-items must fold sub-items in.
    assert items[2] == (
        "Top-level with nested sub-detail "
        "Indented sub-item under the parent. "
        "Another sub-item."
    )


# ---------------------------------------------------------------------------
# CLI-surface extraction
# ---------------------------------------------------------------------------


def _fixture_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="widget")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="run the widget")
    p_config = sub.add_parser("config", help="inspect widget config")
    config_sub = p_config.add_subparsers(dest="config_cmd", required=True)
    config_sub.add_parser("show", help="show the config")
    return parser


def test_walk_argparse_recovers_full_command_tree_with_help():
    commands = capabilities._walk_argparse(_fixture_parser(), ("widget",))
    by_command = {c.command: c.help for c in commands}
    assert by_command == {
        "widget run": "run the widget",
        "widget config": "inspect widget config",
        "widget config show": "show the config",
    }


def test_horus_own_cli_surface_finds_known_commands():
    commands = capabilities._horus_own_cli_surface()
    by_command = {c.command for c in commands}
    assert "horus fleet" in by_command
    assert "horus capabilities" in by_command
    assert "horus config workspace-root" in by_command


# ---------------------------------------------------------------------------
# Cross-referencing
# ---------------------------------------------------------------------------


def test_related_commands_matches_whole_phrase_only():
    commands = [
        capabilities.CliCommand(command="horus run", help=""),
        capabilities.CliCommand(command="horus fleet", help=""),
    ]
    text = "**Fleet dispatch view**: `horus fleet` prints one line per project."
    assert capabilities._related_commands(text, commands) == ["horus fleet"]

    # "horus run-something" must not match "horus run".
    text_substring_trap = "See `horus run-something-else` for details."
    assert capabilities._related_commands(text_substring_trap, commands) == []


# ---------------------------------------------------------------------------
# Aggregation + serialization
# ---------------------------------------------------------------------------


def test_build_project_catalog_prd_layer_with_cross_reference():
    catalog = capabilities.build_project_catalog("horus-harness", "/x/horus-harness", ALPHA_PRD)
    assert catalog.layer == "prd"
    assert len(catalog.capabilities) == 2
    assert catalog.capabilities[0].related_commands == ["horus fleet"]
    assert catalog.capabilities[1].related_commands == []
    assert catalog.cli_surface is not None and len(catalog.cli_surface) > 0


def test_build_project_catalog_no_ledger_found():
    catalog = capabilities.build_project_catalog("widget", "/x/widget", None)
    assert catalog.layer == "none"
    assert catalog.capabilities == []


def test_load_catalog_skips_missing_horus_dir_and_sorts_by_name(tmp_path):
    zeta = tmp_path / "zeta"
    (zeta / ".horus").mkdir(parents=True)
    (zeta / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")

    alpha = tmp_path / "alpha-proj"
    (alpha / ".horus").mkdir(parents=True)
    (alpha / ".horus" / "PRD.md").write_text(BETA_PRD, encoding="utf-8")

    gone = tmp_path / "gone"  # no .horus/ at all

    catalogs = capabilities.load_catalog([str(zeta), str(alpha), str(gone)])
    assert [c.name for c in catalogs] == ["alpha-proj", "zeta"]


def test_render_json_is_deterministic_and_carries_generated_note(tmp_path):
    catalogs = capabilities.load_catalog([])
    text = capabilities.render_json(catalogs)
    data = json.loads(text)
    assert data["note"].startswith("Generated by `horus capabilities`")
    assert data["schema_version"] == 2
    assert data["projects"] == []


def test_generate_is_idempotent_and_writes_only_the_out_path(tmp_path):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    out_path = tmp_path / "out" / "capabilities.json"

    first = capabilities.generate([str(project)], out_path)
    mtime_1 = out_path.stat().st_mtime_ns
    second = capabilities.generate([str(project)], out_path)
    mtime_2 = out_path.stat().st_mtime_ns

    assert first == second
    assert "vision" not in json.loads(first)["projects"][0]
    assert mtime_1 == mtime_2  # unchanged content -> no rewrite
    assert not (project / ".horus" / "capabilities.json").exists()  # never wrote into source .horus/


# ---------------------------------------------------------------------------
# Per-project, self-documenting mode
# ---------------------------------------------------------------------------


def test_resolve_project_path_matches_by_directory_basename():
    projects = ["/x/horus-harness", "/y/widget-svc"]
    assert capabilities.resolve_project_path("widget-svc", projects) == "/y/widget-svc"
    assert capabilities.resolve_project_path("missing", projects) is None


def test_project_path_for_cwd_matches_resolved_registered_path(tmp_path):
    project = tmp_path / "alpha-proj"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    projects = [str(project)]

    assert capabilities.project_path_for_cwd(project, projects) == str(project)
    assert capabilities.project_path_for_cwd(other, projects) is None


def test_load_project_catalog_reads_live_sources(tmp_path):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")

    catalog = capabilities.load_project_catalog(str(project))
    assert catalog.name == "alpha-proj"
    assert catalog.layer == "prd"
    assert len(catalog.capabilities) == 2


def test_load_project_catalog_no_horus_dir_yields_none_layer(tmp_path):
    project = tmp_path / "bare"
    catalog = capabilities.load_project_catalog(str(project))
    assert catalog.name == "bare"
    assert catalog.layer == "none"
    assert catalog.capabilities == []


def test_render_project_json_carries_stamp_and_payload():
    catalog = capabilities.build_project_catalog("alpha-proj", "/x/alpha-proj", ALPHA_PRD)
    text = capabilities.render_project_json(catalog)
    data = json.loads(text)
    assert data["schema_version"] == 2
    assert data["horus_version"] == capabilities.__version__
    assert data["note"].startswith("Generated by `horus capabilities`")
    assert data["generated_at"]  # ISO-8601 timestamp, present
    assert data["project"]["name"] == "alpha-proj"
    assert len(data["project"]["capabilities"]) == 2


def test_generate_project_payload_idempotent_but_stamp_refreshes(tmp_path):
    project = tmp_path / "delta"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(DELTA_PRD, encoding="utf-8")
    out_path = tmp_path / "out" / "capabilities.json"

    first = json.loads(capabilities.generate_project(str(project), out_path))
    second = json.loads(capabilities.generate_project(str(project), out_path))

    assert first["project"] == second["project"]  # payload is a pure function of the sources
    assert "vision" not in first["project"]
    assert first["schema_version"] == second["schema_version"] == 2
    assert first["horus_version"] == second["horus_version"]
    assert first["generated_at"] != second["generated_at"]  # stamp refreshes every run


def test_generate_project_default_out_path_is_under_project_horus_dir(tmp_path):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")

    capabilities.generate_project(str(project))

    written = project / ".horus" / "capabilities.json"
    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8"))["project"]["name"] == "alpha-proj"


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cmd_capabilities_writes_file_and_prints_summary(tmp_path, monkeypatch, capsys):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [str(project)])
    out_path = tmp_path / "capabilities.json"

    rc = main(["capabilities", "--out", str(out_path)])

    assert rc == 0
    assert out_path.is_file()
    out = capsys.readouterr().out
    assert "Wrote 1 project(s), 2 capability entrie(s)" in out


def test_cmd_capabilities_stdout_prints_full_json(tmp_path, monkeypatch, capsys):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [str(project)])
    out_path = tmp_path / "capabilities.json"

    rc = main(["capabilities", "--out", str(out_path), "--stdout"])

    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["projects"][0]["name"] == "alpha-proj"


def test_cmd_capabilities_no_projects_registered(monkeypatch, capsys):
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [])
    assert main(["capabilities"]) == 0
    assert "No projects registered" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CLI wiring — per-project mode
# ---------------------------------------------------------------------------


def test_cmd_capabilities_project_flag_writes_stamped_file_and_prints_it(tmp_path, monkeypatch, capsys):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [str(project)])

    rc = main(["capabilities", "--project", "alpha-proj"])

    assert rc == 0
    written = project / ".horus" / "capabilities.json"
    assert written.is_file()
    data = json.loads(capsys.readouterr().out)
    assert data["project"]["name"] == "alpha-proj"
    assert data["schema_version"] == 2
    assert data["generated_at"]
    # printed stdout matches the written file byte-for-byte
    assert json.loads(written.read_text(encoding="utf-8")) == data


def test_cmd_capabilities_project_flag_unknown_name_fails(monkeypatch, capsys):
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: ["/x/alpha-proj"])
    rc = main(["capabilities", "--project", "does-not-exist"])
    assert rc == 1
    assert "No registered project named" in capsys.readouterr().out


def test_cmd_capabilities_self_document_default_inside_registered_project(tmp_path, monkeypatch, capsys):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [str(project)])
    monkeypatch.chdir(project)

    rc = main(["capabilities"])

    assert rc == 0
    assert (project / ".horus" / "capabilities.json").is_file()
    data = json.loads(capsys.readouterr().out)
    assert data["project"]["name"] == "alpha-proj"


def test_cmd_capabilities_no_project_flag_outside_registered_project_stays_fleet_wide(
    tmp_path, monkeypatch, capsys
):
    project = tmp_path / "alpha-proj"
    (project / ".horus").mkdir(parents=True)
    (project / ".horus" / "PRD.md").write_text(ALPHA_PRD, encoding="utf-8")
    monkeypatch.setattr(capabilities.config, "load_projects", lambda: [str(project)])
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    out_path = tmp_path / "fleet-out.json"

    rc = main(["capabilities", "--out", str(out_path)])

    assert rc == 0
    assert out_path.is_file()  # fleet-wide path used, not the per-project one
    assert not (project / ".horus" / "capabilities.json").exists()
    assert "Wrote 1 project(s)" in capsys.readouterr().out


def test_per_project_capabilities_json_is_gitignored():
    repo_root = Path(__file__).resolve().parents[1]
    gitignore = (repo_root / ".horus" / ".gitignore").read_text(encoding="utf-8")
    assert "capabilities.json" in gitignore
