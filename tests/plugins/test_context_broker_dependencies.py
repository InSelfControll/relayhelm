"""MCP picker save must disable and unload explicitly dependent plugins."""

import yaml


def test_mcp_picker_disables_dependent_plugin_and_leaves_unrelated_plugin(tmp_path, monkeypatch):
    from hermes_cli import config, mcp_picker, plugins

    project = tmp_path / "project"
    project.mkdir()
    cfg = {
        "plugins": {"enabled": ["context-broker", "disk-cleanup"], "entries": {
            "context-broker": {"requires_mcp_servers": ["context-broker"],
                               "mcp_allowlist": ["context-broker"],
                               "settings": {"project_root": str(project)}}}},
        "mcp_servers": {"context-broker": {"command": "context-broker", "enabled": True},
                        "other": {"command": "other", "enabled": True}},
    }
    config.save_config(cfg)
    manager = plugins.PluginManager()
    monkeypatch.setattr(plugins, "_plugin_manager", manager)
    manager.discover_and_load()
    assert manager._plugins["context-broker"].enabled
    assert "context-broker" in manager._plugin_commands
    from tools import mcp_tool_lifecycle
    shutdown_calls = []
    real_shutdown = mcp_tool_lifecycle.shutdown_mcp_server

    def shutdown(name):
        shutdown_calls.append(name)
        return real_shutdown(name)

    monkeypatch.setattr(mcp_tool_lifecycle, "shutdown_mcp_server", shutdown)
    mcp_picker._enable_disable("context-broker", enable=False)
    saved = config.load_config()
    assert "context-broker" not in saved["plugins"]["enabled"]
    assert "context-broker" in saved["plugins"]["disabled"]
    assert "context-broker" not in manager._plugin_commands
    assert "context-broker" not in manager._plugins
    assert manager._plugins["disk-cleanup"].enabled
    assert saved["mcp_servers"]["other"]["enabled"] is True
    assert shutdown_calls == ["context-broker"]
    # Turning a server back on must not silently override the user's plugin choice.
    mcp_picker._enable_disable("context-broker", enable=True)
    assert "context-broker" not in config.load_config()["plugins"]["enabled"]
    manager.unload()


def test_partial_save_honors_dependency_but_not_access_grant(tmp_path):
    from hermes_cli import config

    config.save_config({
        "plugins": {"enabled": ["dependent", "optional"], "entries": {
            "dependent": {"requires_mcp_servers": ["broker"]},
            "optional": {"mcp_allowlist": ["broker"]}}},
        "mcp_servers": {"broker": {"command": "broker", "enabled": True}},
    })
    config.save_config({"mcp_servers": {"broker": {"enabled": "false"}}}, merge_existing=True)
    raw = yaml.safe_load(config.get_config_path().read_text())
    assert raw["plugins"]["enabled"] == ["optional"]
    assert raw["plugins"]["disabled"] == ["dependent"]
    assert raw["mcp_servers"]["broker"]["command"] == "broker"


def test_later_reenable_supersedes_pending_disable_callback(tmp_path, monkeypatch):
    from hermes_cli import config, plugin_mcp_dependencies as dependencies
    from hermes_constants import get_hermes_home

    active_home = get_hermes_home()
    saved_home = tmp_path / "other-profile"
    saved_home.mkdir()
    enabled = {"mcp_servers": {"broker": {"enabled": True}},
               "plugins": {"enabled": ["consumer"], "disabled": []}}
    disabled = {"mcp_servers": {"broker": {"enabled": False}},
                "plugins": {"enabled": [], "disabled": ["consumer"]}}
    # Model a later atomic write already restoring both entries in the saved
    # profile, while the caller's active profile has a different configuration.
    (saved_home / "config.yaml").write_text(yaml.safe_dump(enabled))
    calls = []
    monkeypatch.setattr(dependencies, "unload_disabled_mcp_plugins", lambda names: calls.extend(names))
    from tools import mcp_tool_lifecycle
    monkeypatch.setattr(mcp_tool_lifecycle, "shutdown_mcp_server", lambda name: calls.append(name))
    dependencies.apply_saved_mcp_teardown(enabled, disabled, ["consumer"], config_home=saved_home)
    assert calls == []
    assert get_hermes_home() == active_home
