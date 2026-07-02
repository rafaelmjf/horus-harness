"""Tests for the read-only machine-wide skill map (observe-first slice)."""

from pathlib import Path

from horus import config, skillmap, skills


def _write_skill(base: Path, name: str, *, version: int | None = None, description: str = "") -> None:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {name}\n"
    if description:
        fm += f"description: >-\n  {description}\n"
    fm += "---\n"
    marker = f"<!-- horus-skill-version: {version} -->\n" if version is not None else ""
    (d / "SKILL.md").write_text(fm + marker + f"# {name}\n", encoding="utf-8")


def _home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    return home


def test_scan_covers_project_user_and_account_scopes(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    proj = tmp_path / "proj"
    proj.mkdir()
    config.register_project(proj)
    _write_skill(proj / ".claude" / "skills", "horus-consolidate", version=3)
    _write_skill(proj / ".agents" / "skills", "horus-consolidate", version=3)
    _write_skill(home / ".claude" / "skills", "my-notes", description="Personal notes helper.")
    _write_skill(home / ".codex" / "skills", "my-notes")
    acct = home / ".horus" / "accounts" / "claude-work"
    config.set_account_config_dir("work", str(acct))
    _write_skill(acct / "skills", "work-only")

    instances = skillmap.scan_machine()

    keyed = {(i.name, i.scope, i.agent, i.owner) for i in instances}
    assert ("horus-consolidate", "project", "claude", "proj") in keyed
    assert ("horus-consolidate", "project", "codex", "proj") in keyed
    assert ("my-notes", "user", "claude", "") in keyed
    assert ("my-notes", "user", "codex", "") in keyed
    assert ("work-only", "account", "claude", "work") in keyed


def test_bundled_verdicts_current_stale_unmarked(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    bundled = skills.SKILLS[0]
    base = tmp_path / "s"
    _write_skill(base, bundled.name, version=bundled.version)
    current = skillmap._scan_dir(base, scope="user", agent="claude", owner="")[0]
    assert skillmap.instance_verdict(current) == "current"

    _write_skill(base, bundled.name, version=bundled.version - 1)
    stale = skillmap._scan_dir(base, scope="user", agent="claude", owner="")[0]
    assert skillmap.instance_verdict(stale) == "stale"

    _write_skill(base, bundled.name, version=None)
    unmarked = skillmap._scan_dir(base, scope="user", agent="claude", owner="")[0]
    assert skillmap.instance_verdict(unmarked) == "unmarked"


def test_foreign_skills_are_presence_only(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    base = tmp_path / "s"
    _write_skill(base, "third-party-thing", version=99)
    inst = skillmap._scan_dir(base, scope="user", agent="claude", owner="")[0]
    assert skillmap.instance_verdict(inst) == "foreign"


def test_skill_map_groups_and_sorts_bundled_first(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    bundled = skills.SKILLS[0]
    _write_skill(home / ".claude" / "skills", "aaa-foreign")
    _write_skill(home / ".claude" / "skills", bundled.name, version=bundled.version - 1)

    groups = skillmap.skill_map()

    assert [g["name"] for g in groups] == [bundled.name, "aaa-foreign"]
    assert groups[0]["bundled"] is True and groups[0]["stale"] == 1
    assert groups[1]["bundled"] is False and groups[1]["latest"] is None


def test_block_scalar_description_extracted(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    base = tmp_path / "s"
    _write_skill(base, "described", description="Does a thing across two words.")
    inst = skillmap._scan_dir(base, scope="user", agent="claude", owner="")[0]
    assert inst.description == "Does a thing across two words."


def test_codex_home_env_respected(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "custom-codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_skill(codex_home / "skills", "env-skill")

    instances = skillmap.scan_machine()

    assert any(i.name == "env-skill" and i.agent == "codex" and i.scope == "user" for i in instances)


def test_cli_skill_map_reports(tmp_path, monkeypatch, capsys):
    from horus.cli import main

    home = _home(tmp_path, monkeypatch)
    bundled = skills.SKILLS[0]
    _write_skill(home / ".claude" / "skills", bundled.name, version=bundled.version - 1)
    _write_skill(home / ".claude" / "skills", "thirdparty")

    assert main(["skill", "map"]) == 0
    out = capsys.readouterr().out
    assert bundled.name in out
    assert "STALE" in out
    assert "foreign" in out
    assert "this machine only" in out


def test_dashboard_skills_page_renders(tmp_path, monkeypatch):
    from horus import dashboard

    home = _home(tmp_path, monkeypatch)
    bundled = skills.SKILLS[0]
    _write_skill(home / ".claude" / "skills", bundled.name, version=bundled.version)
    _write_skill(home / ".claude" / "skills", "thirdparty", description="A <script> unsafe & desc")

    body = dashboard.render_skill_map()

    assert bundled.name in body
    assert "thirdparty" in body
    assert "foreign" in body
    assert "<script> unsafe" not in body  # escaped
    assert "&lt;script&gt;" in body
    assert "this machine only" in body
