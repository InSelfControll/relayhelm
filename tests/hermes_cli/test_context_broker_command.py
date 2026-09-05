"""Broker discovery works before enabling any optional plugin."""
import argparse
from unittest.mock import Mock

import pytest
from hermes_cli.subcommands import context_broker as command


def parser():
    result = argparse.ArgumentParser()
    command.build_context_broker_parser(result.add_subparsers())
    return result


def test_help_without_installed_broker(monkeypatch, capsys):
    monkeypatch.setattr(command.shutil, 'which', Mock(side_effect=AssertionError('resolved executable')))
    args = parser().parse_args(['context-broker'])
    assert args.func(args) == 0
    output = capsys.readouterr()
    assert 'integration-config' in output.out
    assert not output.err
    with pytest.raises(SystemExit) as exc:
        parser().parse_args(['context-broker', '--help'])
    assert exc.value.code == 0
    assert '/context-broker index' in capsys.readouterr().out


def test_forwarding_preserves_project_and_failure(monkeypatch):
    monkeypatch.setattr(command.shutil, 'which', lambda _: '/bin/context-broker')
    run = Mock(return_value=Mock(returncode=7))
    monkeypatch.setattr(command.subprocess, 'run', run)
    args = parser().parse_args(['context-broker', 'connect', '--project-root', '/project with spaces'])
    assert args.func(args) == 7
    run.assert_called_once_with(['/bin/context-broker', 'connect', '--project-root', '/project with spaces'], check=False)


def test_missing_installation_is_failure(monkeypatch, capsys):
    monkeypatch.setattr(command.shutil, 'which', lambda _: None)
    args = parser().parse_args(['context-broker', 'serve'])
    assert args.func(args) == 127
    assert 'uv tool install --python 3.13' in capsys.readouterr().err


def test_main_parser_discovers_command():
    from hermes_cli.main import _build_cli_parser
    main, _ = _build_cli_parser()
    args = main.parse_args(['context-broker', 'serve'])
    assert args.func is command.cmd_context_broker


def test_relayhelm_native_configuration_forwarding(monkeypatch):
    monkeypatch.setattr(command.shutil, 'which', lambda _: '/bin/context-broker')
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(command.subprocess, 'run', run)
    args = parser().parse_args(['context-broker', 'integration-config', '--host', 'relayhelm',
                               '--project-root', '/project with spaces'])
    assert args.func(args) == 0
    run.assert_called_once_with(['/bin/context-broker', 'integration-config', '--project-root',
                                 '/project with spaces', '--host', 'relayhelm'], check=False)
