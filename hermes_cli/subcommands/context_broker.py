"""Discover and run the separately installed Context Broker CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys


def cmd_context_broker(args) -> int:
    """Forward parsed arguments without a shell and preserve the broker's exit status."""
    if args.broker_command is None:
        args.broker_parser.print_help()
        return 0
    if args.broker_command == "install":
        from hermes_cli.context_broker_install import install_broker
        try:
            return install_broker(args)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            sys.stderr.write(f"Context Broker installation failed ({type(exc).__name__}); "
                             "check uv, Python 3.13, project path, and network access.\n")
            return 1
    executable = shutil.which("context-broker")
    if executable is None:
        sys.stderr.write(
            "Context Broker is not installed on PATH. Install its separate runtime:\n"
            "  uv tool install --python 3.13 "
            "git+https://github.com/InSelfControll/context-broker-mcp.git\n"
            "Or install and configure together: "
            "relayhelm context-broker install --project-root /absolute/project\n"
        )
        return 127
    command = [executable, args.broker_command]
    if args.broker_command == "update" and args.check:
        command.append("--check")
    if args.broker_command == "serve":
        command += ["--port", str(args.port)]
    elif args.broker_command in {"connect", "integration-config"}:
        command += ["--project-root", args.project_root]
        if args.broker_command == "integration-config":
            command += ["--host", args.host]
            if args.print_only:
                command += ["--print"]
            if args.config_path:
                command += ["--config-path", args.config_path]
            if args.runtime_dir:
                command += ["--runtime-dir", args.runtime_dir]
    try:
        options = {}
        if args.broker_command in {"start", "stop", "update", "serve", "connect"}:
            from hermes_cli.context_broker_install import broker_environment
            env = broker_environment()
            if env is not None:
                options["env"] = env
        result = subprocess.run(command, check=False, **options)
        if args.broker_command == "update" and not args.check and result.returncode == 0:
            from hermes_cli.context_broker_install import refresh_broker_integration
            return refresh_broker_integration(executable)
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        sys.stderr.write(f"Context Broker could not start ({type(exc).__name__}). Check its installation.\n")
        return 1


def build_context_broker_parser(subparsers) -> None:
    """Expose help even before the optional MCP plugin or broker is installed."""
    parser = subparsers.add_parser(
        "context-broker",
        help="Run Context Broker or discover its commands",
        description="Run the separately installed context-broker runtime. "
        "Install for a project; 'connect' automatically starts the shared service. "
        "In chat, the enabled Context Broker plugin provides /context-broker status "
        "and /context-broker index (Index / No index choice).",
        epilog="Install: uv tool install --python 3.13 "
        "git+https://github.com/InSelfControll/context-broker-mcp.git",
    )
    parser.set_defaults(func=cmd_context_broker, broker_parser=parser)
    commands = parser.add_subparsers(dest="broker_command")
    install = commands.add_parser("install", help="Install runtime, MCP config, skill, and plugin")
    install.add_argument("--project-root", required=True)
    install.add_argument("--runtime-dir", default="")
    update = commands.add_parser("update", help="Update broker runtime and restart its service")
    update.add_argument("--check", action="store_true", help="Preview without changes")
    commands.add_parser("start", help="Start or reuse the shared service in the background")
    commands.add_parser("stop", help="Stop the shared service (disconnects all agents)")
    commands.add_parser("mcp", help="Start the standalone MCP server")
    commands.add_parser("dashboard", help="Run the broker dashboard")
    serve = commands.add_parser("serve", help="Start the shared memory service")
    serve.add_argument("--port", type=int, default=8771)
    connect = commands.add_parser("connect", help="Connect an MCP client for one project")
    connect.add_argument("--project-root", required=True)
    config = commands.add_parser("integration-config", help="Merge Context Broker into native client config")
    config.add_argument("--host", choices=("codex", "hermes", "relayhelm", "cursor", "claude-code"), required=True)
    config.add_argument("--project-root", required=True)
    config.add_argument("--runtime-dir", default="")
    config.add_argument("--config-path", default="", help="Override target config path")
    config.add_argument("--print", dest="print_only", action="store_true", help="Preview without writing")
