# multi-nanobots

A reusable template for deploying multiple [nanobot](https://github.com/HKUDS/nanobot) agents as a coordinated fleet. Includes 3 example agents (Main, Scout, Coordinator) with process management, systemd integration, and workspace bootstrap files.

## Architecture

```
systemd (multi-nanobots.service)
  └── supervisord (supervisord.conf)
       ├── main        :18790  — Lead developer, full system access
       ├── scout       :18791  — Domain specialist, sandboxed to workspace
       └── coordinator :18792  — Research lead, reads all workspaces
```

Each agent runs as an independent nanobot process with its own:
- **Config file** (`<agent>.config.json`) — model, channels, provider, port
- **Workspace** (`<agent>-workspace/`) — identity, personality, memory, instructions

Agents communicate via their messaging channels (Telegram, Discord) or by reading each other's workspace files.

## Prerequisites

- **Python 3.11+** with pip
- **nanobot** installed (`pip install nanobot` or from source)
- **supervisord** installed (`pip install supervisor`)
- **An LLM API key** — [OpenRouter](https://openrouter.ai/) recommended (single key, all models)
- **A messaging channel** — Telegram bot token and/or Discord bot token (at least one)

## Quick Start

### 1. Copy the template

```bash
cp -r examples/multi-nanobots ~/my-agents
cd ~/my-agents
```

### 2. Add your API key

Edit all 3 config files and replace the OpenRouter placeholder:

```bash
# In main.config.json, scout.config.json, coordinator.config.json:
# Replace YOUR_OPENROUTER_API_KEY_HERE with your actual key
```

### 3. Enable a messaging channel

Pick Telegram or Discord (or both) and fill in the tokens:

**Telegram:**
1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token into each config's `channels.telegram.token`
3. Get your user ID (message [@userinfobot](https://t.me/userinfobot)) and add it to `allowFrom`
4. Set `channels.telegram.enabled` to `true`

**Discord:**
1. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy the bot token into each config's `channels.discord.token`
3. Add your Discord user ID to `allowFrom`
4. Set `channels.discord.enabled` to `true`

### 4. Customize your agents

- Edit `USER.md` in each workspace with your name, timezone, and preferences
- Edit `IDENTITY.md` to rename agents and define their roles
- Edit `SOUL.md` to adjust personality and behavioral rules

### 5. Start the fleet

```bash
./start-agents.sh
```

All 3 agents will start and auto-restart on failure. Logs go to `logs/`.

To stop:

```bash
./stop-agents.sh
```

## Configuration Guide

### Providers

The template uses [OpenRouter](https://openrouter.ai/) as the default provider, which gives access to models from Anthropic, OpenAI, Google, Meta, and more with a single API key.

To change the model, edit the `agents.defaults.model` field in each config:

```json
{
  "agents": {
    "defaults": {
      "model": "openrouter/anthropic/claude-sonnet-4"
    }
  }
}
```

Popular model choices:
- `openrouter/anthropic/claude-sonnet-4` — balanced (default)
- `openrouter/anthropic/claude-opus-4` — most capable
- `openrouter/anthropic/claude-haiku-4` — fastest, cheapest
- `openrouter/openai/gpt-4o` — OpenAI alternative

### Channels

Each agent can connect to multiple messaging channels independently. Configure per-agent in `<agent>.config.json`:

| Field | Description |
|-------|-------------|
| `channels.telegram.enabled` | Enable/disable Telegram |
| `channels.telegram.token` | Bot token from @BotFather |
| `channels.telegram.allowFrom` | Array of Telegram user IDs allowed to interact |
| `channels.discord.enabled` | Enable/disable Discord |
| `channels.discord.token` | Bot token from Discord Developer Portal |
| `channels.discord.allowFrom` | Array of Discord user IDs allowed to interact |
| `channels.discord.groupPolicy` | `"mention"` (respond only when @mentioned) or `"all"` |
| `channels.sendProgress` | Show "thinking..." indicators |
| `channels.sendToolHints` | Show which tools are being used |
| `channels.sendToolResults` | Show raw tool output |

### Permissions

| Field | Effect |
|-------|--------|
| `tools.restrictToWorkspace` | `true` = file access limited to workspace dir |
| `tools.exec.timeout` | Command execution timeout in seconds |
| `tools.web.search.maxResults` | Max web search results |

## Adding a New Agent

1. **Create the config:**
   ```bash
   cp main.config.json myagent.config.json
   ```

2. **Edit the config** — change:
   - `agents.defaults.workspace` → `"./myagent-workspace"`
   - `gateway.port` → a new unique port (e.g., `18793`)
   - `tools.restrictToWorkspace` → `true` or `false` as needed
   - Channel tokens (each agent needs its own bot)

3. **Create the workspace:**
   ```bash
   cp -r main-workspace myagent-workspace
   ```

4. **Customize the workspace:**
   - `IDENTITY.md` — name, role, responsibilities
   - `SOUL.md` — personality, behavioral rules
   - `TOOLS.md` — update fleet table

5. **Add to supervisord.conf:**
   ```ini
   [program:myagent]
   command=nanobot --config %(here)s/myagent.config.json gateway
   directory=%(here)s
   stdout_logfile=logs/myagent.log
   stderr_logfile=logs/myagent-err.log
   autorestart=true
   startsecs=5
   ```

6. **Restart supervisord:**
   ```bash
   ./stop-agents.sh && ./start-agents.sh
   ```

## Removing an Agent

1. Delete the config file: `rm myagent.config.json`
2. Delete the workspace: `rm -rf myagent-workspace`
3. Remove the `[program:myagent]` block from `supervisord.conf`
4. Restart: `./stop-agents.sh && ./start-agents.sh`

## Running as a System Service

To run the fleet automatically on boot:

1. **Edit the service file** — replace placeholders in `multi-nanobots.service`:
   - `YOUR_USERNAME` → your system username
   - `/path/to/multi-nanobots` → absolute path to this directory
   - `/usr/local/bin/supervisord` → path to your supervisord binary (`which supervisord`)

2. **Install the service:**
   ```bash
   sudo cp multi-nanobots.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable multi-nanobots.service
   sudo systemctl start multi-nanobots.service
   ```

3. **Manage the service:**
   ```bash
   sudo systemctl status multi-nanobots    # Check status
   sudo systemctl restart multi-nanobots   # Restart all agents
   sudo systemctl stop multi-nanobots      # Stop all agents
   journalctl -u multi-nanobots -f         # View logs
   ```

### Host Tool Access (PATH for systemd)

When agents run under systemd, the `exec` tool only sees systemd's minimal PATH:

```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Tools installed via version managers (nvm, Flutter SDK, Go, Cargo, etc.) are **not available** because systemd does not source `~/.bashrc` or `~/.profile`.

**Fix:** Add `Environment=` lines to your service file before installing it:

```ini
[Service]
# Expose host development tools to agent exec commands
# Build this PATH from your ~/.bashrc exports — include every tool your agents need
Environment=PATH=/home/you/.nvm/versions/node/v20.x.x/bin:/usr/local/go/bin:/home/you/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# Add any other env vars your tools need
Environment=GOPATH=/home/you/go
```

**How to build your PATH:**

```bash
# 1. Print your interactive shell's PATH (this has everything)
echo $PATH

# 2. Copy it into the Environment=PATH= line in the service file

# 3. After installing the service, verify it works:
sudo systemctl daemon-reload
sudo systemctl restart multi-nanobots
sleep 5
pid=$(pgrep -f "nanobot.*main" | head -1)
cat /proc/$pid/environ | tr '\0' '\n' | grep PATH
```

**Without this fix**, agents will get "command not found" errors when trying to run tools like `node`, `go`, `flutter`, `cargo`, `dotnet`, etc. via the `exec` tool.

### Host Tool Access (Docker)

If running agents inside Docker containers instead of bare metal, the systemd `Environment=PATH=...` approach does **not work** — host binaries don't exist inside the container's filesystem. You must install tools directly in the Docker image.

Example Dockerfile snippet for common development tools:

```dockerfile
FROM python:3.12-slim

# Go
COPY --from=golang:1.23 /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"

# Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Flutter
RUN git clone https://github.com/flutter/flutter.git /opt/flutter --branch stable --depth 1
ENV PATH="/opt/flutter/bin:${PATH}"

# Rust / Cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
```

Only install what your agents need — each tool adds to image size. Volume-mounting host binaries (`-v /usr/local/go:/usr/local/go`) is unreliable due to shared library mismatches between host and container.

## Customization Guide

Each workspace contains bootstrap files that define the agent's behavior:

| File | Purpose | When to Edit |
|------|---------|--------------|
| `IDENTITY.md` | Name, role, fleet info | Rename agent, change role |
| `SOUL.md` | Personality, rules, RULE ZERO | Adjust behavior, add rules |
| `USER.md` | User profile and preferences | Fill in your details |
| `TOOLS.md` | Environment notes, fleet status | Add local tool info |
| `HEARTBEAT.md` | Periodic tasks (when enabled) | Add recurring checks |
| `AGENTS.md` | Per-session workflow instructions | Change startup routine |
| `memory/MEMORY.md` | Persistent memory across sessions | Usually auto-updated by agent |

### RULE ZERO

The most important behavioral pattern is **RULE ZERO: ACT, DON'T TALK ABOUT ACTING**. This instructs the agent to use its tools immediately when asked to do something, rather than describing what it would do. It's included in every agent's `SOUL.md` and is the single most impactful rule for getting productive agent behavior.

### Workspace Boundaries

Scout is configured with `restrictToWorkspace: true`, which limits its file access to its own workspace directory. This is useful for:
- **Security** — preventing accidental modification of system files
- **Focus** — keeping the agent on-task within its domain
- **Safety** — isolating experimental or untrusted workloads

Main and Coordinator have unrestricted access for system administration and cross-agent coordination.

## Troubleshooting

### Agents won't start

```bash
# Check supervisord logs
cat logs/supervisord.log

# Check individual agent logs
cat logs/main-err.log

# Verify nanobot is installed
which nanobot
nanobot --version

# Verify config is valid JSON
python3 -c "import json; json.load(open('main.config.json')); print('OK')"
```

### "Connection refused" on agent port

The agent may still be starting up (wait 10 seconds) or may have crashed:

```bash
supervisorctl -c supervisord.conf status
```

### Agent can't connect to LLM provider

- Verify your OpenRouter API key is correct
- Check your account has credits at [openrouter.ai/account](https://openrouter.ai/account)
- Test the key: `curl -H "Authorization: Bearer YOUR_KEY" https://openrouter.ai/api/v1/models`

### Agent not responding on Telegram/Discord

- Verify the bot token is correct
- Ensure `enabled: true` for the channel
- Check that your user ID is in `allowFrom`
- Verify the bot has been started (Telegram: send `/start` to the bot)
- Check agent error logs: `cat logs/<agent>-err.log`

### "restrictToWorkspace" blocking Scout

This is by design. If Scout needs access to files outside its workspace, either:
1. Copy the files into Scout's workspace
2. Use the Coordinator to read and relay the information
3. Change `restrictToWorkspace` to `false` in `scout.config.json` (reduces isolation)

### Supervisor socket errors

```bash
# Remove stale socket
rm -f logs/supervisor.sock

# Restart
./start-agents.sh
```

### Agent `exec` tool can't find node/go/flutter/cargo

systemd uses a minimal PATH that doesn't include tools from version managers. Add `Environment=PATH=...` to your service file with the full PATH from your interactive shell. See "Host Tool Access" section above.

---

Built with [nanobot](https://github.com/HKUDS/nanobot).
