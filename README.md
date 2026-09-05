# Relayhelm

Relayhelm is an independent agent harness maintained at [InSelfControll/relayhelm](https://github.com/InSelfControll/relayhelm), built from [NousResearch's Hermes Agent](https://github.com/NousResearch/hermes-agent). Its updates and contributions belong to this repository. The original MIT license and contributor history are preserved.

Run the agent in a terminal, desktop interface, or messaging gateway. The inherited provider and platform adapters include Telegram, Discord, Slack, Microsoft Teams and other channels; each requires its own credentials and setup.

## Install

```bash
git clone https://github.com/InSelfControll/relayhelm.git
cd relayhelm
uv sync --extra dev --extra mcp
uv run relayhelm setup
uv run relayhelm
```

For the guided platform installer:

```bash
curl -fsSL https://raw.githubusercontent.com/InSelfControll/relayhelm/main/scripts/install.sh | bash
```

The commands are `relayhelm`, `relayhelm-agent` and `relayhelm-acp`. Default state is `~/.relayhelm` on Linux/macOS and `%LOCALAPPDATA%/relayhelm` on Windows. Existing Hermes state is not migrated automatically. Internal `hermes_cli`/`hermes_*` Python imports, plugin API names and explicitly supplied `HERMES_*` environment variables remain compatible with existing extensions. Use separate profiles for separate project bindings.

## Context Broker MCP

[Context Broker](https://github.com/InSelfControll/context-broker-mcp) supplies one shared model/memory pool with project-scoped history and exact model handoffs. Run `context-broker serve` once, then connect each coding host through `context-broker connect --project-root /absolute/project`.

Relayhelm's opt-in [Context Broker plugin](docs/context-broker-integration.md) looks up relevant issue history on each prompt, adds only bounded matching excerpts, and leaves unrelated sessions free of project-memory preload. `/context-broker index` asks whether to index; both choices continue reading original history. Disabling a required MCP disables the dependent plugin and releases its hooks.

The broker's delegation tool asks before splitting a task and retains the requested model. Handoffs preserve explicit messages, constraints, decisions, task states and file freshness checks. Failed work retains a failure reason; proposals still require integration and verification before completion.

## Plugins and coding hosts

Native Hermes Python plugins retain their API. Installed Claude Code, Codex and Cursor packages can use supported skills, MCP definitions and command hooks through the [host compatibility adapter](docs/plugin-compatibility.md). Packages must be explicitly enabled. Unsupported host-specific components fail with a reason; this is not a claim of complete compatibility with every proprietary plugin or UI feature.

Codex, Claude Code, Cursor and Hermes can also connect directly to Context Broker using its host configuration generator. Provider authentication, native host behavior and messaging delivery should be validated on your own setup.

## Development

```bash
scripts/run_tests.sh -j 4
```

Use the repository test runner so tests run with isolated state and credentials. See [AGENTS.md](AGENTS.md) for engineering conventions and [the documentation source](website/docs) for inherited functionality.

## Attribution

Relayhelm derives from Hermes Agent by Nous Research and its contributors. See [LICENSE](LICENSE) and [UPSTREAM.md](UPSTREAM.md). Hermes model names, third-party service URLs and compatibility identifiers are retained where they refer to those original interfaces or products.
