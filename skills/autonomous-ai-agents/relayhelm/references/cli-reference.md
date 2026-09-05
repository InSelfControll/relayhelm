# Relayhelm CLI Reference

Live sources when anything looks stale: `relayhelm --help`, `hermes <command> --help`,
https://hermes-agent.nousresearch.com/docs/reference/cli-commands

### Global Flags

```
hermes [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
relayhelm chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
relayhelm setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
relayhelm model                Interactive model/provider picker
hermes fallback [add|remove|list]  Fallback provider chain
relayhelm config [show|edit|get|set|unset|path|env-path|check|migrate]
hermes login / logout       OAuth sign-in / clear stored auth
relayhelm doctor [--fix]       Check dependencies and config
relayhelm status [--all]       Component status
```

### Tools & Skills

```
relayhelm tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

relayhelm skills list|browse|search QUERY|inspect ID
relayhelm skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
relayhelm skills config        Enable/disable skills per platform
relayhelm skills check|update|uninstall|publish PATH
relayhelm skills tap add REPO  Add a GitHub repo as a skill source
hermes bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
hermes mcp add NAME (--url or --command) | remove | list | test NAME
hermes mcp catalog | install NAME     Curated catalog install
hermes mcp configure NAME             Toggle tool selection
hermes mcp serve                      Run Relayhelm as an MCP server
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
relayhelm gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `hermes photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
hermes sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
relayhelm cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
hermes webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
relayhelm profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
relayhelm profile rename A B | alias NAME | export NAME | import FILE
```

### Credentials & Pools

```
relayhelm auth                 Interactive credential manager
relayhelm auth add [PROVIDER]  Add OAuth or API-key credential (nous, openai-codex, qwen-oauth, …)
relayhelm auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
hermes desktop / gui        Native desktop app
relayhelm dashboard            Web admin panel + embedded chat (--stop / --status)
hermes proxy                OpenAI-compatible local proxy backed by an OAuth provider
hermes portal               Quick setup / sign in via Nous Portal
relayhelm kanban <verb>        Multi-agent work-queue board
hermes project              Named multi-folder workspaces
hermes skin list|use|set    Switch/tweak skins (see references/themes.md)
hermes pets <verb>          Pet mascots (see references/petdex.md)
relayhelm memory setup|status|off|reset   Memory provider
hermes secrets bitwarden|onepassword   External secret stores
hermes moa                  Mixture-of-Agents slots
hermes hooks / security / backup / import / checkpoints / console
hermes logs [-f] [errors]   View agent/error logs
hermes send                 One-off message through a gateway platform
hermes pairing / plugins / insights / journey / computer-use
relayhelm acp                  ACP server (IDE integration)
hermes completion bash|zsh|fish
relayhelm update / uninstall / claw migrate
```

Plugin- and provider-supplied subcommands (e.g. `hermes photon setup`) only appear once their plugin is installed/active.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `relayhelm config edit` · [Configuration docs](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) |
| Tools / toolsets | `relayhelm tools list` · [Tools reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference) |
| Skills catalog | `relayhelm skills browse` · [Skills catalog](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `relayhelm model` · [Providers guide](https://hermes-agent.nousresearch.com/docs/integrations/providers) |
| Env variables | `relayhelm config env-path` · [Env vars reference](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) |
| Gateway logs | `~/.relayhelm/logs/gateway.log` (or `hermes logs`) |
| Sessions | `hermes sessions browse` (reads state.db) |
