from pathlib import Path

from horus import machine_requirements


def _write(root: Path, frontmatter: str, body: str = "") -> Path:
    path = root / ".horus" / "requirements.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
    return path


def test_absent_declaration_is_optional(tmp_path):
    report = machine_requirements.inspect(tmp_path)
    assert not report.declared
    assert not report.requirements
    assert machine_requirements.findings(report) == []
    assert machine_requirements.warning_text(report) == ""


def test_inspect_probes_tools_and_config_paths_without_executing(tmp_path):
    config_path = tmp_path / "local" / "settings.toml"
    config_path.parent.mkdir()
    config_path.write_text("ready = true\n", encoding="utf-8")
    _write(
        tmp_path,
        """kind: machine-requirements
tools:
  - name: Fabric CLI
    probe: fab
    install: uv tool install fab
    needed_for: Fabric workspace operations
  - name: Power BI reader
    probe: pbir
    install: install pbir
    needed_for: report inspection
configs:
  - name: Local settings
    probe: local/settings.toml
    needed_for: authenticated access
""",
        "# Machine requirements\n\nDescribe non-probeable access here.\n",
    )

    report = machine_requirements.inspect(
        tmp_path,
        which=lambda name: "/usr/bin/fab" if name == "fab" else None,
    )

    assert report.declared and not report.issues
    assert [(item.name, item.available) for item in report.requirements] == [
        ("Fabric CLI", True),
        ("Power BI reader", False),
        ("Local settings", True),
    ]
    assert [item.name for item in report.missing] == ["Power BI reader"]
    warning = machine_requirements.warning_text(report)
    assert warning.startswith("⚠ this machine is missing: Power BI reader")
    assert "needed for report inspection" in warning
    assert "install: install pbir" in warning


def test_tool_probe_rejects_committed_shell_commands(tmp_path):
    _write(
        tmp_path,
        """kind: machine-requirements
tools:
  - name: Unsafe probe
    probe: fab --version
    install: never run this
    needed_for: proving probes are data
configs: []
""",
    )
    looked_up = []

    report = machine_requirements.inspect(
        tmp_path,
        which=lambda name: looked_up.append(name) or "/bin/anything",
    )

    assert looked_up == []
    assert not report.requirements
    assert "commands are never executed" in report.issues[0]
    assert "could not be fully checked" in machine_requirements.warning_text(report)


def test_invalid_declaration_surfaces_doctor_warning(tmp_path):
    _write(tmp_path, "kind: something-else\ntools: []\nconfigs: []\n")
    report = machine_requirements.inspect(tmp_path)
    findings = machine_requirements.findings(report)
    assert findings[0].level == "warn"
    assert "kind must be 'machine-requirements'" in findings[0].message
