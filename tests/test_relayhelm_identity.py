"""Relayhelm must coexist with the upstream installation."""

from pathlib import Path


def test_default_home_does_not_read_upstream_state(tmp_path, monkeypatch):
    import hermes_constants

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    original = tmp_path / ".hermes"
    original.mkdir()
    (original / "config.yaml").write_text("model: upstream-only\n")
    actual = hermes_constants.get_process_hermes_home()
    assert actual != original
    assert actual.name in {".relayhelm", "relayhelm"}
    assert not (actual / "config.yaml").exists()
    # An explicitly configured compatibility override remains authoritative.
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "chosen-profile"))
    assert hermes_constants.get_process_hermes_home() == tmp_path / "chosen-profile"


def test_uninstaller_leaves_upstream_command_untouched(tmp_path, monkeypatch):
    from hermes_cli.uninstall import remove_wrapper_script

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    directory = tmp_path / ".local" / "bin"
    directory.mkdir(parents=True)
    original = directory / "hermes"
    original.write_text("#!/bin/sh\nexec python -m hermes_cli.main\n")
    own = directory / "relayhelm-agent"
    own.write_text("#!/bin/sh\n# relayhelm\nexec python run_agent.py\n")
    removed = remove_wrapper_script()
    assert own in removed and not own.exists()
    assert original.exists()


def test_update_remote_recognizes_only_relayhelm_as_official():
    from hermes_cli.banner import _is_official_ssh_remote

    assert _is_official_ssh_remote("git@github.com:InSelfControll/relayhelm.git")
    assert not _is_official_ssh_remote("git@github.com:NousResearch/hermes-agent.git")
