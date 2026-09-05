"""Explicit, fail-closed adapters for installed coding-host plugin packages.

Discovery still goes through PluginManager's enabled list and project trust gate.
No package code runs during manifest inspection or the MCP startup probe.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

from hermes_cli.agent_plugins import (
    AgentPluginError, AgentPluginPackage, _inside, _read_json_object,
    _discover_skills, _translate_remote, _translate_stdio,
)

MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json")
EVENTS = {"PreToolUse": "pre_tool_call", "PostToolUse": "post_tool_call",
          "Stop": "pre_verify", "SessionStart": "on_session_start", "SessionEnd": "on_session_end"}
# Unknown tool names remain unchanged, so native MCP names keep their identity.
TOOL_NAMES = {"terminal": "Bash", "read_file": "Read", "write_file": "Write", "patch": "Edit"}


def manifest_path(root: Path) -> Path | None:
    found = [root / name for name in MANIFESTS if (root / name).exists() or (root / name).is_symlink()]
    if any(not _inside(path, root) or not path.is_file() for path in found):
        raise AgentPluginError("host plugin manifest must be an in-root regular file")
    if len(found) > 1:
        # Multiple host manifests are common. Require identical declarations instead of
        # silently selecting one host's different capabilities.
        values = [_read_json_object(p, label=str(p)) for p in found]
        if any(value != values[0] for value in values[1:]):
            raise AgentPluginError("host manifests disagree; install one host variant")
    return found[0] if found else None


def read_manifest(root: Path) -> dict:
    path = manifest_path(root)
    if path is None or not _inside(path, root) or not path.is_file():
        raise AgentPluginError("host plugin manifest must be an in-root regular file")
    value = _read_json_object(path, label=str(path))
    name = value.get("name")
    if not isinstance(name, str) or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", name) is None:
        raise AgentPluginError("host plugin requires a valid name")
    for field in ("description", "version"):
        if field in value and not isinstance(value[field], str):
            raise AgentPluginError(f"host plugin {field} must be a string")
    return value


def _component(root: Path, value, default: str):
    if isinstance(value, dict):
        return value
    path = root / (value if isinstance(value, str) else default)
    if value is not None and not isinstance(value, str):
        raise AgentPluginError(f"unsupported {default} declaration")
    if not path.exists() and not path.is_symlink() and value is None:
        return {}
    if not _inside(path, root) or not path.is_file():
        raise AgentPluginError(f"{default} must be an in-root regular file")
    return _read_json_object(path, label=default)


def discover_mcp(root: Path, data_root: Path, *, create_data: bool = False) -> dict:
    manifest = read_manifest(root)
    value = _component(root, manifest.get("mcpServers"), ".mcp.json")
    servers = value.get("mcpServers", value)
    if not isinstance(servers, dict):
        raise AgentPluginError("mcpServers must be an object")
    result = {}
    for name, raw in servers.items():
        if not isinstance(name, str) or not name or not isinstance(raw, dict):
            raise AgentPluginError(f"MCP {name}: expected an object")
        if raw.get("disabled") is True or raw.get("enabled") is False:
            continue
        server = json.loads(json.dumps(raw).replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}")
                            .replace("${CLAUDE_PLUGIN_DATA}", "${PLUGIN_DATA}"))
        server.pop("disabled", None)
        server.pop("enabled", None)
        transport = server.pop("type", "http" if "url" in server else "stdio")
        try:
            if transport == "stdio":
                command = server.get("command", "")
                if isinstance(command, str) and command.startswith("${PLUGIN_ROOT}/"):
                    server["command"] = "./" + command[len("${PLUGIN_ROOT}/"):]
                translated = _translate_stdio(server, root, data_root, create_data)
                translated["env"].update(CLAUDE_PLUGIN_ROOT=str(root), CLAUDE_PLUGIN_DATA=str(data_root))
            elif transport in {"http", "streamable-http"}:
                translated = _translate_remote(server)
            else:
                raise ValueError(f"unsupported transport {transport}")
        except ValueError as exc:
            raise AgentPluginError(f"MCP {name}: {exc}") from exc
        result[name] = translated
    return result


def read_hooks(root: Path, manifest: dict) -> list[tuple[str, dict, str]]:
    value = _component(root, manifest.get("hooks"), "hooks/hooks.json")
    groups = value.get("hooks", value)
    if not isinstance(groups, dict):
        raise AgentPluginError("hooks must be an object")
    result = []
    for event, entries in groups.items():
        if event not in EVENTS:
            raise AgentPluginError(f"unsupported host hook event: {event}")
        if not isinstance(entries, list):
            raise AgentPluginError(f"{event} hooks must be an array")
        for group in entries:
            if not isinstance(group, dict) or set(group) - {"matcher", "hooks"}:
                raise AgentPluginError(f"unsupported {event} hook group")
            matcher = group.get("matcher", "")
            if not isinstance(matcher, str):
                raise AgentPluginError("hook matcher must be a string")
            if matcher and event not in {"PreToolUse", "PostToolUse"}:
                raise AgentPluginError(f"{event} matcher semantics are unsupported")
            try:
                re.compile(matcher)
            except re.error as exc:
                raise AgentPluginError(f"invalid hook matcher: {exc}") from exc
            hooks = group.get("hooks", [])
            if not isinstance(hooks, list):
                raise AgentPluginError("hook group hooks must be an array")
            for hook in hooks:
                if not isinstance(hook, dict) or hook.get("type") != "command":
                    raise AgentPluginError(f"{event}: only command hooks are supported")
                if set(hook) - {"type", "command", "timeout", "statusMessage"}:
                    raise AgentPluginError(f"{event}: unsupported command hook options")
                timeout = hook.get("timeout", 60)
                if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
                    raise AgentPluginError("hook timeout must be between 0 and 300 seconds")
                if not isinstance(hook.get("command"), str) or not hook["command"].strip():
                    raise AgentPluginError("hook command must be non-empty")
                result.append((event, hook, matcher))
    return result


def load_package(root: Path, data_root: Path) -> tuple[AgentPluginPackage, list]:
    root, data_root = root.resolve(strict=True), data_root.resolve()
    manifest = read_manifest(root)
    # These require host services or semantics Relayhelm cannot faithfully supply.
    for field in ("agents", "commands", "lspServers", "monitors", "apps", "rules", "dependencies", "outputStyles", "settings"):
        if manifest.get(field) or (root / field).exists():
            raise AgentPluginError(f"unsupported host component: {field}; use its native host")
    if (root / ".app.json").exists():
        raise AgentPluginError("host apps require the native host")
    if manifest.get("skills") not in (None, "./skills", "skills", ["./skills"], ["skills"]):
        raise AgentPluginError("custom skills paths are unsupported; use the skills directory")
    hooks = read_hooks(root, manifest)
    diagnostics = []
    skills = _discover_skills(root, diagnostics)
    if diagnostics:
        raise AgentPluginError("; ".join(item.message for item in diagnostics))
    servers = discover_mcp(root, data_root, create_data=True)
    if hooks:
        data_root.mkdir(parents=True, exist_ok=True)
    return AgentPluginPackage(manifest["name"], manifest.get("version", ""),
                              manifest.get("description", ""), root, data_root, manifest,
                              skills, servers, ()), hooks


def make_hook(root: Path, data_root: Path, event: str, hook: dict, matcher: str):
    """Execute a trusted plugin command without changing process-global environment.

    The owning PluginContext leases this callback; unload removes it. Failures on
    permission/verification gates block instead of being mistaken for approval.
    """
    from agent.shell_hooks import _parse_pre_tool_call, _parse_pre_verify
    from hermes_cli._subprocess_compat import kill_process_tree

    def callback(**kwargs):
        tool_name = TOOL_NAMES.get(kwargs.get("tool_name"), kwargs.get("tool_name"))
        if matcher and re.search(matcher, tool_name or "") is None:
            return None
        tool_input = dict(kwargs.get("args") or {})
        file_tool = kwargs.get("tool_name") in {"read_file", "write_file", "patch"}
        if file_tool and "path" in tool_input:
            tool_input["file_path"] = tool_input.pop("path")
        payload = {"hook_event_name": event, "tool_name": tool_name,
                   "tool_input": tool_input, "tool_response": kwargs.get("result"),
                   "session_id": kwargs.get("session_id", ""), "cwd": os.getcwd()}
        env = dict(os.environ, PLUGIN_ROOT=str(root), PLUGIN_DATA=str(data_root),
                   CLAUDE_PLUGIN_ROOT=str(root), CLAUDE_PLUGIN_DATA=str(data_root))
        blocking = event in {"PreToolUse", "Stop"}

        def failed(reason):
            if blocking:
                return {"action": "block" if event == "PreToolUse" else "continue", "message": reason}
            raise RuntimeError(reason)

        proc = None
        try:
            proc = subprocess.Popen(hook["command"], shell=True, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    encoding="utf-8", errors="replace", env=env,
                                    start_new_session=os.name != "nt")
            stdout, stderr = proc.communicate(json.dumps(payload, default=str), timeout=hook.get("timeout", 60))
        except Exception as exc:
            if proc is not None:
                try:
                    kill_process_tree(proc)
                except Exception:
                    pass  # retain the original hook failure even if cleanup also fails
                try:
                    proc.communicate(timeout=1)
                except Exception:
                    pass
            return failed(f"{event} hook failed: {exc}")
        if proc.returncode:
            return failed(f"{event} hook failed (exit {proc.returncode}): {stderr[:2000] or stdout[:2000]}")
        if not stdout.strip():
            return None
        try:
            data = json.loads(stdout)
            if not isinstance(data, dict):
                raise ValueError("expected an object")
        except ValueError as exc:
            return failed(f"{event} hook returned invalid JSON: {exc}")
        specific = data.get("hookSpecificOutput", {})
        if specific and not isinstance(specific, dict):
            return failed("hookSpecificOutput must be an object")
        if data.get("continue") is False:
            return failed(data.get("stopReason") or "hook stopped the task")
        if specific.get("hookEventName", event) != event:
            return failed("hookSpecificOutput names a different event")
        if event == "PreToolUse":
            if set(specific) - {"hookEventName", "permissionDecision", "permissionDecisionReason", "updatedInput", "additionalContext"}:
                return failed("unsupported pre-tool hook output")
            decision = specific.get("permissionDecision")
            if decision is not None and (not isinstance(decision, str) or decision not in {"allow", "deny", "ask"}):
                return failed("unsupported hook permission decision")
            if decision in {"deny", "ask"}:
                return failed(specific.get("permissionDecisionReason") or "hook requires user approval")
            if isinstance(specific.get("updatedInput"), dict):
                updated = dict(specific["updatedInput"])
                if file_tool and "file_path" in updated:
                    updated["path"] = updated.pop("file_path")
                return {"action": "modify", "args": updated}
            parsed = _parse_pre_tool_call(data)
            if parsed and parsed.get("action") == "modify" and file_tool and "file_path" in parsed["args"]:
                parsed["args"]["path"] = parsed["args"].pop("file_path")
            return parsed
        if event == "Stop":
            return _parse_pre_verify(data)
        context = specific.get("additionalContext")
        return {"context": context} if isinstance(context, str) and context else None

    return callback


def release_mcp_server(manager, name: str) -> None:
    """Remove discovery config and verify the owned transport actually stopped."""
    manager._portable_mcp_servers.pop(name, None)
    from tools.mcp_tool_lifecycle import shutdown_mcp_server
    result = shutdown_mcp_server(name)
    if result["status"] == "failed":
        raise RuntimeError(result["failure_reason"])
