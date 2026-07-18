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


def test_proxy_env_base_keys_and_no_map_without_discovery(isolated):
    env = proxy.proxy_env(proxy.load_state())
    assert env["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{proxy.DEFAULT_PORT}"
    assert env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] == "1"
    # Default state has no model_map yet, so no alias pins are injected.
    assert not any(k.startswith("ANTHROPIC_DEFAULT_") for k in env)


def test_proxy_env_injects_alias_to_concrete_id_map(isolated):
    st = proxy.load_state()
    st["model_map"] = {"opus": "claude-opus-4-8", "sonnet": "claude-sonnet-5"}
    env = proxy.proxy_env(st)
    # Bug #2: a bare `--model opus` must resolve to a served id, not 502.
    assert env["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-8"
    assert env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-5"
    assert "ANTHROPIC_DEFAULT_HAIKU_MODEL" not in env  # not in the map → not pinned


def test_pick_model_map_picks_a_served_claude_id_per_tier(isolated):
    served = ["gpt-5.5", "claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5-20251001"]
    m = proxy._pick_model_map(served)
    assert m == {"opus": "claude-opus-4-8", "sonnet": "claude-sonnet-5",
                 "haiku": "claude-haiku-4-5-20251001"}
    assert proxy._pick_model_map(["gpt-5.5"]) == {}  # GPT-only proxy → no Claude pins


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


def test_enable_refuses_when_proxy_never_serves(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    monkeypatch.setattr(proxy, "logged_in_providers", lambda s: ["codex"])
    monkeypatch.setattr(schedule, "proxy_service_active", lambda: False)
    monkeypatch.setattr(schedule, "install_proxy_service", lambda **k: None)
    monkeypatch.setattr(proxy, "_await_models", lambda s, **k: (False, []))  # never serves
    ok, msg = proxy.enable(proxy.load_state())
    assert ok is False and "aborted" in msg.lower()
    assert proxy.load_state()["enabled"] is False


def test_enable_never_writes_settings_json_and_records_the_map(isolated, monkeypatch):
    # B's core safety property: enabling NEVER rewrites a settings.json, so it cannot
    # poison a running session. It only starts+verifies the service and stores the map.
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    monkeypatch.setattr(proxy, "logged_in_providers", lambda s: ["codex", "claude"])
    monkeypatch.setattr(schedule, "proxy_service_active", lambda: True)
    monkeypatch.setattr(proxy, "_await_models", lambda s, **k: (True, ["claude-opus-4-8", "gpt-5.5"]))
    acct = isolated / "acctA"
    acct.mkdir()
    monkeypatch.setattr(proxy, "_claude_config_dirs", lambda: [acct])

    ok, msg = proxy.enable(proxy.load_state())
    assert ok
    assert not (acct / "settings.json").exists()  # enable writes NO settings.json (the B guarantee)
    st = proxy.load_state()
    assert st["enabled"] is True and st["model_map"]["opus"] == "claude-opus-4-8"


def test_disable_stops_service_removes_container_and_clears_legacy(isolated, monkeypatch):
    monkeypatch.setattr(proxy, "docker_available", lambda: True)
    dirs = [isolated / "acctA", isolated / "acctB"]
    monkeypatch.setattr(proxy, "_claude_config_dirs", lambda: dirs)
    cleared, removed = [], []
    monkeypatch.setattr(proxy.config, "clear_proxy_env", lambda d: cleared.append(d) or True)
    monkeypatch.setattr(schedule, "remove_proxy_service", lambda: True)
    monkeypatch.setattr(proxy, "_remove_container", lambda s: removed.append(True))

    st = proxy.load_state(); st["enabled"] = True; proxy.save_state(st)
    ok, _ = proxy.disable(proxy.load_state())
    assert ok and removed == [True]              # bug #3: container force-removed
    assert cleared == dirs                        # legacy env cleaned (migration)
    assert proxy.load_state()["enabled"] is False


def test_build_env_injects_proxy_env_only_when_proxied_and_enabled(isolated, monkeypatch):
    from horus.adapters.claude import ClaudeAdapter
    from horus.adapters.base import SpawnSpec

    st = proxy.load_state(); st["enabled"] = True
    st["model_map"] = {"opus": "claude-opus-4-8"}; proxy.save_state(st)
    adapter = ClaudeAdapter(config_dirs={})

    plain = adapter.build_env(SpawnSpec(prompt="", project_dir=isolated, proxied=False))
    assert "ANTHROPIC_BASE_URL" not in plain          # untouched unless proxied

    proxied = adapter.build_env(SpawnSpec(prompt="", project_dir=isolated, proxied=True))
    assert proxied["ANTHROPIC_BASE_URL"] == f"http://127.0.0.1:{proxy.DEFAULT_PORT}"
    assert proxied["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-8"


def test_build_env_proxied_is_noop_when_disabled(isolated, monkeypatch):
    from horus.adapters.claude import ClaudeAdapter
    from horus.adapters.base import SpawnSpec

    # enabled defaults to False → even a proxied launch injects nothing.
    proxy.save_state(proxy.load_state())
    env = ClaudeAdapter(config_dirs={}).build_env(
        SpawnSpec(prompt="", project_dir=isolated, proxied=True))
    assert "ANTHROPIC_BASE_URL" not in env
