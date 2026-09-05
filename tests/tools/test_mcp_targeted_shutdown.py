"""A targeted disable preserves other profiles, lazy servers, and retry state."""
import asyncio
import threading
from types import SimpleNamespace

import pytest

from tools import mcp_tool as core
from tools.mcp_tool_lifecycle import shutdown_mcp_server


@pytest.fixture
def state(monkeypatch):
    for name in ("_servers", "_server_scope_keys", "_lazy_server_configs", "_lazy_server_fingerprints",
                 "_lazy_server_tool_names", "_server_connect_retry_after", "_server_connect_failures",
                 "_server_connect_errors"):
        monkeypatch.setattr(core, name, {})
    monkeypatch.setattr(core, "_server_connecting", set())
    monkeypatch.setattr(core, "_mcp_registry_scope", lambda: "mine")
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(core, "_mcp_loop", loop)
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
    loop.close()


def test_only_selected_transport_and_its_cooldown_are_closed(state):
    calls = []

    async def shutdown():
        calls.append("selected")

    selected = SimpleNamespace(name="selected", shutdown=shutdown)
    other = SimpleNamespace(name="other", shutdown=shutdown)
    core._servers.update(selected=selected, other=other)
    core._server_scope_keys.update(selected="mine", other="other-profile")
    core._server_connect_retry_after.update(selected=1, other=2)
    core._server_connect_failures.update(selected=1, other=2)
    core._lazy_server_configs.update(selected={"command": "python"}, other={"command": "node"})
    result = shutdown_mcp_server("selected")
    assert result == {"status": "disabled", "completed": True, "server": "selected"}
    assert calls == ["selected"]
    assert core._servers == {"other": other}
    assert core._server_connect_retry_after == {"other": 2}
    assert core._server_connect_failures == {"other": 2}
    assert set(core._lazy_server_configs) == {"other"}
    assert state.is_running()


def test_shutdown_error_and_cross_profile_are_failed(state):
    async def shutdown():
        raise RuntimeError("transport refused shutdown")

    server = SimpleNamespace(name="broken", shutdown=shutdown)
    core._servers["broken"] = server
    core._server_scope_keys["broken"] = "another"
    result = shutdown_mcp_server("broken")
    assert result["status"] == "failed"
    assert "another profile" in result["failure_reason"]
    core._server_scope_keys["broken"] = "mine"
    result = shutdown_mcp_server("broken")
    assert result["completed"] is False
    assert "transport refused shutdown" in result["failure_reason"]
    assert core._servers["broken"] is server
    assert state.is_running()


def test_lazy_server_cannot_reconnect_after_disable(state):
    core._lazy_server_configs["lazy"] = {"command": "python"}
    assert shutdown_mcp_server("lazy")["status"] == "disabled"
    from tools.mcp_tool_discovery import _ensure_lazy_server_connected
    assert _ensure_lazy_server_connected("lazy") is False
