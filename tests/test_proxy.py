"""The optional CLIProxyAPI integration (vision-branch-x4 stage 1).

Deterministic logic — state, env, command building, guided enable/disable gating —
is unit-tested here; the live global rewire (settings.json + Docker service) is in
the PR's runtime probe.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from horus import proxy, schedule


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(proxy.config, "config_dir", lambda: tmp_path / "horus")
    monkeypatch.setattr(proxy.Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


def test_state_round_trips_and_defaults(isolated):
    st = proxy.load_state()
    assert st["enabled"] is False and st["port"] == proxy.DEFAULT_PORT
    st["enabled"] = True
    proxy.save_state(st)
    assert proxy.load_state()["enabled"] is True


def test_api_key_minted_once(isolated):
    st = proxy.load_state()
    k1 = proxy.ensure_api_key(st)
    assert k1.startswith("sk-horus-")
    assert proxy.ensure_api_key(proxy.load_state()) == k1  # persisted, stable


def test_proxy_env_is_baseurl_token_discovery_only(isolated):
    env = proxy.proxy_env(proxy.load_state())
    assert env["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{proxy.DEFAULT_PORT}"
    assert env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"
    # No alias remap: Claude aliases stay Claude, GPT appears via discovery (mode B).
    assert not any(k.startswith("ANTHROPIC_DEFAULT_") for k in env)


def test_logged_in_providers_reads_the_auth_dir(isolated):
    auth = isolated / ".cli-proxy-api"
    auth.mkdir(parents=True)
    (auth / "codex-me-plus.json").write_text("{}", encoding="utf-8")
    (auth / "claude-me.json").write_text("{}", encoding="utf-8")
    (auth / "error-root.log").write_text("noise", encoding="utf-8")
    assert proxy.logged_in_providers(proxy.load_state()) == ["claude", "codex"]


def test_docker_run_command_binds_localhost_and_names_the_binary(isolated):
    cmd = proxy.docker_run_command(proxy.load_state())
    assert cmd[0] == "docker" and "--name" in cmd and proxy.CONTAINER_NAME in cmd
    assert f"127.0.0.1:{proxy.DEFAULT_PORT}:{proxy.DEFAULT_PORT}" in cmd
    assert cmd[-3:] == ("/CLIProxyAPI/CLIProxyAPI", "-config", "/CLIProxyAPI/config.yaml")


def test_login_command_publishes_callback_port_only_for_claude(isolated):
    st = proxy.load_state()
    assert "-codex-device-login" in proxy.login_command(st, "codex")
    assert "-p" not in proxy.login_command(st, "codex")
    claude = proxy.login_command(st, "claude")
    assert "-claude-login" in claude and "54545:54545" in claude and "-oauth-callback-port" in claude


def test_enable_refuses_without_docker(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: False)
    ok, msg = proxy.enable(proxy.load_state())
    assert ok is False and "Docker" in msg


def test_enable_refuses_without_a_login(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    monkeypatch.setattr(proxy, "logged_in_providers", lambda s: [])
    ok, msg = proxy.enable(proxy.load_state())
    assert ok is False and "logged in" in msg


def test_enable_refuses_to_wire_a_dead_proxy(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    monkeypatch.setattr(proxy, "logged_in_providers", lambda s: ["codex"])
    monkeypatch.setattr(schedule, "proxy_service_active", lambda: False)
    monkeypatch.setattr(schedule, "install_proxy_service", lambda **k: None)
    monkeypatch.setattr(proxy, "_wait_reachable", lambda s, **k: False)  # never serves
    wrote = []
    monkeypatch.setattr(proxy.config, "write_proxy_env", lambda d, e: wrote.append(d) or True)
    ok, msg = proxy.enable(proxy.load_state())
    assert ok is False and "not wiring" in msg.lower()
    assert wrote == []  # never touched settings.json when the proxy isn't serving


def test_enable_then_disable_writes_and_clears_env(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    monkeypatch.setattr(proxy, "logged_in_providers", lambda s: ["codex", "claude"])
    monkeypatch.setattr(schedule, "proxy_service_active", lambda: True)
    monkeypatch.setattr(proxy, "_wait_reachable", lambda s, **k: True)
    dirs = [isolated / "acctA", isolated / "acctB"]
    monkeypatch.setattr(proxy, "_claude_config_dirs", lambda: dirs)
    wrote, cleared = [], []
    monkeypatch.setattr(proxy.config, "write_proxy_env", lambda d, e: wrote.append(d) or True)
    monkeypatch.setattr(proxy.config, "clear_proxy_env", lambda d: cleared.append(d) or True)
    monkeypatch.setattr(schedule, "remove_proxy_service", lambda: True)

    ok, _ = proxy.enable(proxy.load_state())
    assert ok and wrote == dirs and proxy.load_state()["enabled"] is True
    ok, _ = proxy.disable(proxy.load_state())
    assert ok and cleared == dirs and proxy.load_state()["enabled"] is False
