# Context Broker in Relayhelm

Relayhelm connects to one Context Broker service, which owns the shared model pool;
project roots separate history and handoffs. Each agent's `connect` process automatically
starts or reuses the service. No manual `serve` command is required.

```sh
relayhelm context-broker install --project-root /absolute/project
relayhelm context-broker update --check
relayhelm context-broker update
```

Install bootstraps a missing runtime through uv using a pinned source revision and
the dashboard/integrations extras. It installs the broker usage skill under the
active profile's `skills/context-broker`, merges MCP configuration, and enables the
bundled history plugin. Existing configuration is backed up and unrelated entries
are preserved. Restart the agent to load the integration in a new session.
`--runtime-dir` selects a separate private shared service directory.

Update delegates to the broker's installation-aware updater and refreshes the
active enabled integration's configuration and skill. Disabled integrations remain
disabled. It restarts an active service after success; existing agents must reconnect.
An update failure leaves the service stopped for repair. Nix and other externally
managed installations must be updated with their package manager. An older broker
without the new update command needs its package/repository updated first.
`relayhelm update` continues to own Relayhelm's own code and gateway lifecycle;
`relayhelm context-broker update` owns the separate broker runtime.

The installer generates the equivalent of these entries in the active profile's
`config.yaml`, using an absolute interpreter path and 90-second connection timeout:

```yaml
mcp_servers:
  context-broker:
    command: context-broker
    args: [connect, --project-root, /absolute/project]
    enabled: true
plugins:
  enabled: [context-broker]
  entries:
    context-broker:
      mcp_allowlist: [context-broker]
      requires_mcp_servers: [context-broker]
      settings:
        server: context-broker
        project_root: /absolute/project
```

Use a separate Relayhelm profile for each project. An absolute existing project directory is required: a messaging gateway's working directory does not establish the sender's project. The plugin never guesses one from the process cwd. Configure the same canonical directory in the connection and plugin settings.

Run `/context-broker index` to receive the broker's actual **Index / No index** choice through MCP elicitation. No index still reads the original history records. If the client cannot obtain consent, the operation fails and changes nothing. `/context-broker status` shows the active project binding.

For each text-bearing user turn, the plugin calls `lookup_project_history` using at most 8,000 query characters. It adds only up to three relevant excerpts, bounded to 7,000 total context characters, to the current user message using Relayhelm's existing context hook. Empty matches add nothing. It does not modify the system prompt, reload full project memory, store per-model copies, or add attachment bytes to the search. History is untrusted evidence; previous solutions and failures require verification against the current code. Lookup failures remain failed records and are logged; they are never reported as successful lookup results. No history is injected when lookup fails.

Disabling the broker MCP (including a saved `enabled: false`) or disabling the plugin stops subsequent history calls immediately. The plugin does not reconnect the disabled server. The explicit `requires_mcp_servers` declaration also removes the plugin from the enabled list and unloads its hooks when Relayhelm saves a disabled or removed dependency. Other plugins and MCP servers are unaffected. The native MCP transport closes only the disabled server; the shared broker service and unrelated MCP servers remain available to other sessions. A shutdown failure is reported with its reason. Re-enable both entries to resume on subsequent turns.

Use the broker's native tools for the remaining operations:

| Tool | Contract |
| --- | --- |
| `save_model_handoff` / `load_model_handoff` | Explicit, project-scoped exact checkpoints with freshness checks; reject stale or oversized loads instead of silently truncating |
| `delegate_large_task` | Ask the user before splitting, retain the exact selected model, and return proposals for integration and verification |
| `configure_history_indexing` | Persist only an actual user choice; never accept an agent-supplied approval boolean |

These tools stay on the native MCP client path so permission prompts, structured errors and broker validation remain authoritative. The history plugin does not automatically invent a handoff, mark an agent proposal completed, or change provider/model/reasoning settings. A failed task must retain its failure reason; a successful proposal still needs integration and verification before completion.

Codex, Claude Code and Cursor can connect directly to the same service using `context-broker integration-config --host codex|claude-code|cursor --project-root /absolute/project` (choose one host value). Their own permission and plugin/hook surfaces remain host-specific; this Relayhelm plugin is not a claim that every native host feature has an identical API.
