"""Bootstrap failure cannot enable a broken broker; profile paths remain explicit."""

import argparse
import subprocess
from unittest.mock import Mock

import pytest

from hermes_cli import context_broker_install as installer
from hermes_cli.subcommands.context_broker import build_context_broker_parser


@pytest.mark.parametrize("installed", [True, False])
def test_install_targets_active_profile_and_private_runtime(tmp_path, monkeypatch, installed):
    project = tmp_path / "project with spaces"
    project.mkdir()
    profile = tmp_path / "profile"
    monkeypatch.setenv("HERMES_HOME", str(profile))
    monkeypatch.setattr(installer, "find_broker", lambda: "/tools/context-broker" if installed else None)
    monkeypatch.setattr(installer.shutil, "which", lambda name:
        "/tools/context-broker" if name == "context-broker" and installed
        else "/tools/uv" if name == "uv" else None)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout="/tools\n"))
    monkeypatch.setattr(installer.subprocess, "run", run)
    parser = argparse.ArgumentParser()
    build_context_broker_parser(parser.add_subparsers())
    args = parser.parse_args(["context-broker", "install", "--project-root", str(project),
                              "--runtime-dir", str(tmp_path / "runtime")])
    assert args.func(args) == 0
    command = run.call_args.args[0]
    assert command[1:] == ["integration-config", "--host", "relayhelm", "--project-root",
        str(project), "--config-path", str(profile / "config.yaml"), "--runtime-dir",
        str(tmp_path / "runtime")]
    if not installed:
        assert run.call_args_list[0].args[0][-1] == installer.BROKER_SOURCE


def test_failed_bootstrap_never_configures_plugin(tmp_path, monkeypatch):
    monkeypatch.setattr(installer, "find_broker", lambda: None)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/tools/uv" if name == "uv" else None)
    run = Mock(side_effect=subprocess.CalledProcessError(1, ["uv"]))
    monkeypatch.setattr(installer.subprocess, "run", run)
    parser = argparse.ArgumentParser()
    build_context_broker_parser(parser.add_subparsers())
    args = parser.parse_args(["context-broker", "install", "--project-root", str(tmp_path)])
    assert args.func(args) == 1
    assert run.call_count == 1


@pytest.mark.parametrize("check,enabled", [(True, True), (False, True), (False, False)])
def test_update_targets_profile_runtime_and_respects_disable(tmp_path, monkeypatch, check, enabled):
    import yaml

    profile = tmp_path / "profile"
    profile.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(profile))
    runtime = str(tmp_path / "private-runtime")
    (profile / "config.yaml").write_text(yaml.safe_dump({
        "mcp_servers": {"context-broker": {"command": "context-broker", "enabled": enabled,
            "env": {"CONTEXT_BROKER_SHARED_RUNTIME_DIR": runtime}}},
        "plugins": {"enabled": ["context-broker"] if enabled else [],
            "entries": {"context-broker": {"settings": {"project_root": str(tmp_path)}}}},
    }))
    monkeypatch.setattr(installer.shutil, "which", lambda _: "/tools/context-broker")
    run = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(installer.subprocess, "run", run)
    parser = argparse.ArgumentParser()
    build_context_broker_parser(parser.add_subparsers())
    args = parser.parse_args(["context-broker", "update"] + (["--check"] if check else []))
    assert args.func(args) == 0
    assert run.call_args_list[0].kwargs["env"]["CONTEXT_BROKER_SHARED_RUNTIME_DIR"] == runtime
    assert run.call_count == (2 if enabled and not check else 1)


def test_discovery_finds_uv_executable_outside_path(tmp_path, monkeypatch):
    import os

    executable = tmp_path / ("context-broker.exe" if os.name == "nt" else "context-broker")
    executable.write_text("broker")
    executable.chmod(0o700)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/tools/uv" if name == "uv" else None)
    monkeypatch.setattr(installer.subprocess, "run", Mock(
        return_value=subprocess.CompletedProcess([], 0, stdout=str(tmp_path))))
    assert installer.find_broker() == str(executable)
