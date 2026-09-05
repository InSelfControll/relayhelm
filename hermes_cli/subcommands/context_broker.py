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
    executable = shutil.which("context-broker")
    if executable is None:
        sys.stderr.write(
            "Context Broker is not installed on PATH. Install its separate runtime:\n"
            "  uv tool install --python 3.13 "
            "git+https://github.com/InSelfControll/context-broker-mcp.git\n"
            "Then run: relayhelm context-broker serve\n"
        )
        return 127
    command = [executable, args.broker_command]
    if args.broker_command == "serve":
        command += ["--port", str(args.port)]
    elif args.broker_command in {"connect", "integration-config"}:
        command += ["--project-root", args.project_root]
        if args.broker_command == "integration-config":
            command += ["--host", args.host]
            if args.runtime_dir:
                command += ["--runtime-dir", args.runtime_dir]
    try:
        result = subprocess.run(command, check=False)
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except OSError as exc:
        sys.stderr.write(f"Context Broker could not start ({type(exc).__name__}). Check its installation.\n")
        return 1


def build_context_broker_parser(subparsers) -> None:
    """Expose help even before the optional MCP plugin or broker is installed."""
    parser = subparsers.add_parser(
        "context-broker",
        help="Run Context Broker or discover its commands",
        description="Run the separately installed context-broker runtime. "
        "Start 'serve' once, then use 'connect' for each project. "
        "In chat, the enabled Context Broker plugin provides /context-broker status "
        "and /context-broker index (Index / No index choice).",
        epilog="Install: uv tool install --python 3.13 "
        "git+https://github.com/InSelfControll/context-broker-mcp.git",
    )
    parser.set_defaults(func=cmd_context_broker, broker_parser=parser)
    commands = parser.add_subparsers(dest="broker_command")
    commands.add_parser("mcp", help="Start the standalone MCP server")
    commands.add_parser("dashboard", help="Run the broker dashboard")
    serve = commands.add_parser("serve", help="Start the shared memory service")
    serve.add_argument("--port", type=int, default=8771)
    connect = commands.add_parser("connect", help="Connect an MCP client for one project")
    connect.add_argument("--project-root", required=True)
    config = commands.add_parser("integration-config", help="Print native client config")
    config.add_argument("--host", choices=("codex", "hermes", "relayhelm", "cursor", "claude-code"), required=True)
    config.add_argument("--project-root", required=True)
    config.add_argument("--runtime-dir", default="")
