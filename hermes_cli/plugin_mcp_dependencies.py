"""Keep explicit plugin dependencies in step with saved MCP configuration."""

import logging
import sys

from utils import is_truthy_value

logger = logging.getLogger(__name__)


def disable_unavailable_mcp_plugins(config):
    """Mutate a normalized save candidate; return only plugins newly disabled.

    MCP allowlists grant access, not dependency declarations. Only an explicit
    ``requires_mcp_servers`` list opts into coupled lifecycle behavior.
    """
    plugins = config.get("plugins")
    servers = config.get("mcp_servers") or {}
    if not isinstance(plugins, dict) or not isinstance(servers, dict):
        return []
    entries = plugins.get("entries") or {}
    enabled = plugins.get("enabled")
    if not isinstance(entries, dict) or not isinstance(enabled, list):
        return []
    removed = []
    for name in enabled:
        entry = entries.get(name)
        dependencies = entry.get("requires_mcp_servers") if isinstance(entry, dict) else None
        if not isinstance(dependencies, list) or not dependencies:
            continue
        for server in dependencies:
            definition = servers.get(server) if isinstance(server, str) else None
            if (not isinstance(definition, dict)
                    or not is_truthy_value(definition.get("enabled", True))):
                removed.append(name)
                break
    if removed:
        plugins["enabled"] = [name for name in enabled if name not in removed]
        disabled = plugins.get("disabled")
        plugins["disabled"] = list(dict.fromkeys((disabled if isinstance(disabled, list) else []) + removed))
    return removed


def unload_disabled_mcp_plugins(names):
    """After the atomic save, dispose only affected plugins in the active profile."""
    module = sys.modules.get("hermes_cli.plugins")
    if module is None:
        return
    for name in names:
        try:
            module.unload_plugins(name)
        except Exception:
            # Saved disabled state remains authoritative if a plugin's teardown
            # fails. Never silently claim that the live hooks have been removed.
            logger.exception("MCP disabled plugin %s in config, but live unload failed; restart this Relayhelm session", name)


def shutdown_disabled_mcp_servers(previous, current):
    """Apply saved disable/removal only to live transports, without starting MCP."""
    lifecycle = sys.modules.get("tools.mcp_tool_lifecycle")
    if lifecycle is None:
        return
    before = previous.get("mcp_servers") or {}
    after = current.get("mcp_servers") or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return
    for name, old in before.items():
        new = after.get(name)
        if not isinstance(old, dict) or not is_truthy_value(old.get("enabled", True)):
            continue
        if isinstance(new, dict) and is_truthy_value(new.get("enabled", True)):
            continue
        try:
            result = lifecycle.shutdown_mcp_server(name)
            if result.get("status") == "failed":
                logger.error("MCP server %s is disabled in config but transport shutdown failed: %s",
                             name, result.get("failure_reason", "unknown reason"))
        except Exception:
            logger.exception("MCP server %s is disabled in config but live shutdown failed; restart this Relayhelm session", name)


def apply_saved_mcp_teardown(previous, current, disabled_plugins, *, config_home):
    """Scope callbacks to the saved profile and ignore a superseded disable save.

    A second settings write may finish between atomic persistence and callbacks.
    Re-read that profile before teardown so an older save does not undo an
    already persisted re-enable. Transport identity checks handle replacements.
    """
    if not disabled_plugins and previous.get("mcp_servers") == current.get("mcp_servers"):
        return
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override
    from hermes_cli.config import load_config_readonly

    token = set_hermes_home_override(config_home)
    try:
        latest = load_config_readonly()
        plugins = latest.get("plugins") or {}
        enabled = plugins.get("enabled") or []
        disabled = plugins.get("disabled") or []
        pending = [name for name in disabled_plugins if name not in enabled or name in disabled]
        if pending:
            unload_disabled_mcp_plugins(pending)
        # A plugin's unload callback can itself save configuration.
        shutdown_disabled_mcp_servers(previous, load_config_readonly())
    finally:
        reset_hermes_home_override(token)
