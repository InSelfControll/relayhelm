# Coding-host plugins in Relayhelm

Relayhelm retains the native Hermes Python plugin API and adds installed package
adapters for `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and
`.cursor-plugin/plugin.json`. Existing Agent Plugins v1 packages remain supported.
The runtime does not claim that every proprietary host extension is portable.

Place a trusted package under `~/.relayhelm/plugins/<name>` and explicitly enable
it with `relayhelm plugins enable <name>`. Discovery alone never executes its code.
Project packages remain behind the existing project-plugin opt-in. A package with
conflicting host manifests is rejected instead of selecting different behavior
silently. Python import names stay compatible for existing Hermes plugins.

| Component | Relayhelm behavior |
| --- | --- |
| Standard `skills/*/SKILL.md` | Validated and registered under a collision-resistant namespace |
| `.mcp.json` or manifest `mcpServers` | Validated stdio or HTTP transport, plugin root/data expansion, disabled entries skipped |
| `hooks/hooks.json` or manifest `hooks` | Command hooks with per-process plugin environment and bounded execution timeout |
| `PreToolUse`, `PostToolUse` | Tool-event translation and regex matching; Bash/Read/Write/Edit aliases, file path translation |
| `Stop`, `SessionStart`, `SessionEnd` | Native verification and lifecycle callbacks; lifecycle matchers rejected when semantics cannot be preserved |
| Plugin disable/unload | Releases hook callbacks and portable MCP configuration; shuts down only the owned transport, preserving other sessions |
| Native Hermes Python plugins | Existing `register(ctx)` interfaces and ownership cleanup retained |
| Prompt, agent, HTTP, MCP hook types; other host events | Explicit load failure with reason; security hooks never silently skipped |
| Host agents, commands, LSP, monitors, apps, rules, dependencies, custom skills layouts | Explicit unsupported-component failure; run in the native host |

Command hooks receive JSON on stdin. `${PLUGIN_ROOT}`, `${PLUGIN_DATA}`,
`${CLAUDE_PLUGIN_ROOT}`, and `${CLAUDE_PLUGIN_DATA}` are available in their private
process environment. Tool calls include the native host event name, tool input,
session ID and current project directory. Unknown native/MCP tool names retain
their identity. This does not recreate host-specific transcript files or UI APIs.

Pre-tool denial and exit failures block execution. A hook requesting `ask` blocks
until the user handles approval rather than silently granting permission. Stop
hook failure requests continued verification. Timeout kills the hook process tree.
Malformed gate output fails closed. Unsupported host capabilities fail plugin
loading and leave no partial callbacks or MCP registrations behind.

Compatibility tests exercise real command subprocesses, permission denial,
timeouts, file-input changes, trust gates, all three manifest paths, and targeted
unload. Authentication, proprietary UI features, native transcript APIs, and every
third-party package require validation in their actual host environments.
