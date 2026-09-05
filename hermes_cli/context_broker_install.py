"""Bootstrap the optional broker runtime and configure the active RelayHelm profile."""

from pathlib import Path
import os
import shutil
import subprocess

from hermes_constants import get_hermes_home

# Reviewed companion broker revision; keep bootstrap installs reproducible.
BROKER_REVISION = "3af8b8ce319631d85db581c65a0e770462e70002"
BROKER_SOURCE = (
    "context-broker[dashboard,integrations] @ "
    "git+https://github.com/InSelfControll/context-broker-mcp.git@" + BROKER_REVISION
)


def _uv_broker_path(uv: str) -> Path:
    directory = subprocess.run([uv, "tool", "dir", "--bin"], check=True,
                               capture_output=True, text=True, timeout=15).stdout.strip()
    return Path(directory) / ("context-broker.exe" if os.name == "nt" else "context-broker")


def find_broker() -> str | None:
    """Find an installed broker even before uv's executable directory reaches PATH."""
    executable = shutil.which("context-broker")
    if executable:
        return executable
    uv = shutil.which("uv")
    if not uv:
        return None
    candidate = _uv_broker_path(uv)
    return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None


def install_broker(args) -> int:
    """Install missing runtime, then let the broker own native config and skill merging."""
    root = Path(args.project_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project_root must be a directory")
    executable = find_broker()
    if not executable:
        uv = shutil.which("uv")
        if not uv:
            raise RuntimeError("Install uv before running relayhelm context-broker install")
        subprocess.run([uv, "tool", "install", "--python", "3.13", BROKER_SOURCE],
                       check=True, timeout=1800)
        # uv's tool directory need not be in the invoking shell's PATH yet.
        executable = str(_uv_broker_path(uv))
    return configure_broker(executable, str(root), args.runtime_dir)


def configure_broker(executable: str, project_root: str, runtime_dir: str = "") -> int:
    """Use one owner for MCP, plugin, and skill configuration across install and update."""
    command = [executable, "integration-config", "--host", "relayhelm",
               "--project-root", project_root, "--config-path",
               str(get_hermes_home() / "config.yaml")]
    if runtime_dir:
        command += ["--runtime-dir", runtime_dir]
    return subprocess.run(command, check=False, timeout=120).returncode


def refresh_broker_integration(executable: str) -> int:
    """Refresh the active integration after updates without re-enabling disabled plugins."""
    from hermes_cli.config import load_config_readonly
    from utils import is_truthy_value

    config = load_config_readonly() or {}
    plugins = config.get("plugins") or {}
    entry = (config.get("mcp_servers") or {}).get("context-broker") or {}
    if ("context-broker" not in (plugins.get("enabled") or [])
            or "context-broker" in (plugins.get("disabled") or [])
            or not is_truthy_value(entry.get("enabled", True))):
        return 0
    settings = ((plugins.get("entries") or {}).get("context-broker") or {}).get("settings") or {}
    root = settings.get("project_root")
    if not root:
        raise ValueError("The enabled Context Broker plugin needs a project_root")
    runtime = (entry.get("env") or {}).get("CONTEXT_BROKER_SHARED_RUNTIME_DIR", "")
    return configure_broker(executable, root, runtime)


def broker_environment() -> dict[str, str] | None:
    """Manage the same runtime as the active profile's MCP connection."""
    from hermes_cli.config import load_config_readonly

    config = load_config_readonly() or {}
    entry = (config.get("mcp_servers") or {}).get("context-broker") or {}
    overrides = {key: value for key, value in (entry.get("env") or {}).items()
                 if key.startswith("CONTEXT_BROKER_") and isinstance(value, str)}
    return {**os.environ, **overrides} if overrides else None
