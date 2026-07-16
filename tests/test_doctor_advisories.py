"""Doctor advisory checks: flag non-isolated/shared accounts and outdated managed blocks.

Both follow the same shape — detect a drift from the safe default and name the fix
command — and plug into doctor's existing Finding-based advisory surface.
"""

from __future__ import annotations

import argparse

from horus import cli, config, templates


# --- account isolation (machine target) ---------------------------------------


def _accounts(monkeypatch, aliases, claude_dirs=None, codex_homes=None):
    monkeypatch.setattr(config, "load_account_aliases", lambda: aliases)
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: claude_dirs or {})
    monkeypatch.setattr(config, "load_account_codex_homes", lambda: codex_homes or {})


def test_account_findings_flag_unisolated(monkeypatch):
    _accounts(monkeypatch, {"a@b.com": "work"}, claude_dirs={})
    findings = cli._account_isolation_findings()
    assert any(f.level == "warn" and "not isolated" in f.message and "work" in f.message for f in findings)


def test_account_findings_ok_when_all_isolated(monkeypatch):
    _accounts(monkeypatch, {"a@b.com": "work"}, claude_dirs={"work": "/h/.horus/accounts/claude-work"})
    findings = cli._account_isolation_findings()
    assert findings and all(f.level == "ok" for f in findings)


def test_account_findings_flag_shared_dir(monkeypatch):
    _accounts(monkeypatch, {"a@b.com": "work", "c@d.com": "personal"},
              claude_dirs={"work": "/same/dir", "personal": "/same/dir"})
    findings = cli._account_isolation_findings()
    assert any(f.level == "warn" and "share one CLAUDE_CONFIG_DIR" in f.message for f in findings)


def test_account_findings_empty_without_accounts(monkeypatch):
    _accounts(monkeypatch, {})
    assert cli._account_isolation_findings() == []


def test_doctor_machine_surfaces_account_isolation_as_advisory(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "machine_findings", lambda root: [])
    _accounts(monkeypatch, {"a@b.com": "work"}, claude_dirs={})
    rc = cli.cmd_doctor(argparse.Namespace(path=str(tmp_path), target="machine"))
    out = capsys.readouterr().out
    assert "not isolated" in out
    assert rc == 0  # advisory: a warn in the machine target does not fail doctor


# --- managed-block currency (instructions target) -----------------------------


def _write_instructions(root, version):
    for name, other in (("AGENTS.md", "CLAUDE.md"), ("CLAUDE.md", "AGENTS.md")):
        text = templates.instruction_file("Title", other, "Notes")
        text = text.replace(
            f"horus-block-version: {templates.BLOCK_VERSION}", f"horus-block-version: {version}"
        )
        (root / name).write_text(text, encoding="utf-8")


def test_doctor_flags_outdated_managed_block(tmp_path, capsys):
    _write_instructions(tmp_path, templates.BLOCK_VERSION - 1)
    cli.cmd_doctor(argparse.Namespace(path=str(tmp_path), target="instructions"))
    out = capsys.readouterr().out
    assert "to migrate" in out and "upgrade-project" in out


def test_doctor_current_managed_block_has_no_migrate_hint(tmp_path, capsys):
    _write_instructions(tmp_path, templates.BLOCK_VERSION)
    cli.cmd_doctor(argparse.Namespace(path=str(tmp_path), target="instructions"))
    out = capsys.readouterr().out
    assert "to migrate" not in out
