"""Installed host package translation, permission fidelity, and unload ownership."""
import json
from pathlib import Path
import shlex
import sys

import pytest

from hermes_cli.host_plugin_compat import AgentPluginError, load_package, make_hook
from hermes_cli.plugins_discovery import scan_directory, gate_manifest


def package(tmp_path, host="claude", **manifest):
    root = tmp_path / "plugins" / "example"
    directory = root / f".{host}-plugin"
    directory.mkdir(parents=True)
    (directory / "plugin.json").write_text(json.dumps({"name": "example", **manifest}))
    return root


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize("host", ["claude", "codex", "cursor"])
def test_manifest_discovery_requires_explicit_enable_and_translates_mcp(tmp_path, host):
    root = package(tmp_path, host)
    write_json(root / ".mcp.json", {"mcpServers": {
        "broker": {"command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"]},
        "off": {"command": "python", "disabled": True}}})
    manifests = scan_directory(root.parent, "user")
    assert len(manifests) == 1
    from hermes_cli.plugins_cmd import _read_manifest_for_install, _looks_like_plugin_dir, _read_manifest_info
    assert _looks_like_plugin_dir(root)
    assert _read_manifest_for_install(root)["name"] == "example"
    assert _read_manifest_info(root, "")[3] == "example"
    assert gate_manifest(manifests[0], set(), None).action == "placeholder"
    assert gate_manifest(manifests[0], set(), {"example"}).action == "load"
    result, hooks = load_package(root, tmp_path / "data")
    assert result.mcp_servers["broker"]["args"] == [str(root / "server.py")]
    assert "off" not in result.mcp_servers
    assert hooks == []


def test_unsupported_security_hook_is_a_failure_not_a_partial_success(tmp_path):
    root = package(tmp_path)
    write_json(root / "hooks/hooks.json", {"hooks": {"PreToolUse": [{"hooks": [
        {"type": "prompt", "prompt": "Do not delete data"}]}]}})
    with pytest.raises(AgentPluginError, match="only command hooks"):
        load_package(root, tmp_path / "data")


def command_for(root, source):
    script = root / "hook.py"
    script.write_text(source)
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def test_permission_denial_and_hook_failure_block(tmp_path):
    root = package(tmp_path)
    command = command_for(root, 'import json,sys\np=json.load(sys.stdin)\nassert p["hook_event_name"] == "PreToolUse"\nassert p["tool_name"] == "Bash"\nprint(json.dumps({"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"protected"}}))\n')
    cb = make_hook(root, tmp_path / "data", "PreToolUse", {"command": command}, "Bash")
    assert cb(tool_name="read_file") is None
    assert cb(tool_name="terminal", args={"command": "rm"}) == {"action": "block", "message": "protected"}
    command = command_for(root, 'import sys\nsys.stderr.write("broken gate")\nsys.exit(1)\n')
    result = make_hook(root, tmp_path / "data", "PreToolUse", {"command": command}, "")()
    assert result["action"] == "block"
    assert "broken gate" in result["message"]


def test_unload_releases_portable_servers_and_callbacks(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    from hermes_cli.plugins import PluginManager
    root = package(tmp_path)
    write_json(root / ".mcp.json", {"mcpServers": {"demo": {"command": "python"}}})
    write_json(root / "hooks/hooks.json", {"hooks": {"PreToolUse": [{"hooks": [
        {"type": "command", "command": "echo '{}'"}]}]}})
    manifest = scan_directory(root.parent, "user")[0]
    manager = PluginManager()
    manager._load_plugin(manifest)
    assert manager._plugins["example"].enabled
    assert manager._portable_mcp_servers
    assert manager._hooks["pre_tool_call"]
    assert manager.unload("example")
    assert not manager._portable_mcp_servers
    assert not manager._hooks.get("pre_tool_call")


def test_escaping_manifest_is_rejected(tmp_path):
    root = package(tmp_path)
    path = root / ".claude-plugin/plugin.json"
    path.unlink()
    outside = tmp_path / "outside.json"
    outside.write_text('{"name":"escape"}')
    path.symlink_to(outside)
    with pytest.raises(AgentPluginError, match="in-root"):
        load_package(root, tmp_path / "data")


@pytest.mark.live_system_guard_bypass  # real owned subprocess tree cleanup races with reaping
def test_file_tool_input_translation_and_timeout_failure(tmp_path):
    root = package(tmp_path)
    command = command_for(root, 'import json,sys\np=json.load(sys.stdin)\nassert p["tool_input"]["file_path"] == "old"\nprint(json.dumps({"hookSpecificOutput":{"updatedInput":{"file_path":"new"}}}))\n')
    result = make_hook(root, tmp_path / "data", "PreToolUse", {"command": command}, "Read")(
        tool_name="read_file", args={"path": "old"})
    assert result == {"action": "modify", "args": {"path": "new"}}
    command = command_for(root, 'import time\ntime.sleep(10)\n')
    result = make_hook(root, tmp_path / "data", "PreToolUse", {"command": command, "timeout": .05}, "")()
    assert result["action"] == "block"
    assert "timed out" in result["message"]
