"""Discovery-to-hook regressions for selective shared broker context."""

import json

import pytest
import yaml


@pytest.fixture
def broker(tmp_path, monkeypatch):
    from hermes_cli import plugins
    from hermes_cli.config import get_config_path

    project = tmp_path / "project"
    project.mkdir()
    cfg = {
        "plugins": {"enabled": ["context-broker"], "entries": {
            "context-broker": {"mcp_allowlist": ["context-broker"],
                               "settings": {"project_root": str(project)}}}},
        "mcp_servers": {"context-broker": {"command": "context-broker", "enabled": True}},
    }
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg))
    calls = []
    response = {"value": {"status": "checked", "matches": []}}

    # Keep discovery, profile-scoped config, allowlist enforcement and MCP
    # envelope normalization real; replace only the outbound network handler.
    from tools import mcp_tool_handlers

    def make_handler(server, tool, timeout):
        def call(arguments):
            calls.append((server, tool, arguments))
            return json.dumps({"result": json.dumps(response["value"])})
        return call

    monkeypatch.setattr(mcp_tool_handlers, "_make_tool_handler", make_handler)
    manager = plugins.PluginManager()
    manager.discover_and_load()
    assert manager._plugins["context-broker"].enabled
    yield manager, cfg, path, project, calls, response
    manager.unload()


def test_prompt_history_is_selective_bounded_and_mcp_disable_stops_calls(broker):
    manager, cfg, path, project, calls, response = broker
    history = [{"role": "system", "content": "stable prefix"}]
    assert manager.invoke_hook("pre_llm_call", user_message="hello", conversation_history=history) == [{}]
    assert calls[-1][2] == {"query": "hello", "project_root": str(project.resolve())}
    manager.invoke_hook("pre_llm_call", user_message=[
        {"type": "image_url", "image_url": {"url": "data:private-attachment"}},
        {"type": "text", "text": "q" * 20000}])
    assert calls[-1][2]["query"] == "q" * 8000
    response["value"] = {"status": "checked", "matches": [
        {"source": "old.json", "text": "Previous task failed: database pool exhausted"}]}
    result = manager.invoke_hook("pre_llm_call", user_message="database pool exhausted", conversation_history=history)
    assert "Previous task failed" in result[0]["context"]
    assert history == [{"role": "system", "content": "stable prefix"}]
    assert len(result[0]["context"]) <= 7000
    cfg["platform_toolsets"] = {"cli": ["no_mcp"]}
    path.write_text(yaml.safe_dump(cfg))
    before = len(calls)
    assert manager.invoke_hook("pre_llm_call", user_message="database pool exhausted", platform="cli") == [{}]
    assert len(calls) == before
    cfg.pop("platform_toolsets")
    cfg["mcp_servers"]["context-broker"]["tools"] = {"exclude": ["lookup_project_history"]}
    path.write_text(yaml.safe_dump(cfg))
    assert manager.invoke_hook("pre_llm_call", user_message="database pool exhausted") == [{}]
    assert len(calls) == before
    cfg["mcp_servers"]["context-broker"].pop("tools")
    cfg["mcp_servers"]["context-broker"]["enabled"] = "false"
    path.write_text(yaml.safe_dump(cfg))
    before = len(calls)
    assert manager.invoke_hook("pre_llm_call", user_message="database pool exhausted") == [{}]
    assert len(calls) == before


def test_index_choice_uses_native_elicitation_and_failures_remain_failed(broker):
    manager, cfg, path, project, calls, response = broker
    command = manager._plugin_commands["context-broker"]["handler"]
    response["value"] = {"status": "failed", "failure_reason": "User confirmation unavailable"}
    result = json.loads(command("index"))
    assert calls[-1] == ("context-broker", "configure_history_indexing", {"project_root": str(project)})
    assert result["status"] == "failed"
    assert result["completed"] is False
    assert result["failure_reason"] == "User confirmation unavailable"
    hook_result = manager.invoke_hook("pre_llm_call", user_message="database pool exhausted")[0]
    assert hook_result["status"] == "failed" and not hook_result["completed"]
    assert "context" not in hook_result
    cfg["plugins"]["entries"]["context-broker"]["settings"].pop("project_root")
    path.write_text(yaml.safe_dump(cfg))
    before = len(calls)
    result = manager.invoke_hook("pre_llm_call", user_message="database pool exhausted")[0]
    assert result["status"] == "failed" and len(calls) == before
