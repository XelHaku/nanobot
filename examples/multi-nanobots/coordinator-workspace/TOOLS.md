# TOOLS.md — Local Notes

Skills define HOW tools work. This file is for YOUR specifics —
the stuff that's unique to your setup.

## Environment

- **OS**: (your OS, e.g., Linux Ubuntu 22.04)
- **User**: (your username)
- **Projects root**: (path to your projects, e.g., ~/projects/)
- **Provider**: OpenRouter (configured in agent config)
- **Model**: anthropic/claude-sonnet-4

## Build Tools Available

| Tool | Available | Notes |
|------|-----------|-------|
| git | Yes | Version control |
| python3 | Yes | Python projects |
| npm | Check | Node.js projects |
| cargo | Check | Rust projects |

## Built-in Tools

- **exec** — Execute terminal commands (builds, tests, git, diagnostics)
- **read_file** — Read file contents
- **write_file** — Write/create file contents
- **edit_file** — Edit specific parts of a file
- **list_dir** — List directory contents
- **web_search** — Search the web

## Fleet Status

| Agent | Port | Role | Notes |
|-------|------|------|-------|
| main | 18790 | Lead dev | Full system access |
| scout | 18791 | Specialist | Sandboxed to workspace |
| **coordinator** | 18792 | Research lead | **You are here** (unrestricted) |

## Fleet Management Commands

```bash
# Check all agent statuses
supervisorctl -c /path/to/multi-nanobots/supervisord.conf status

# Restart a specific agent
supervisorctl -c /path/to/multi-nanobots/supervisord.conf restart scout

# Restart all agents
supervisorctl -c /path/to/multi-nanobots/supervisord.conf restart all

# View agent logs
tail -f /path/to/multi-nanobots/logs/scout.log

# Read another agent's memory
cat /path/to/multi-nanobots/main-workspace/MEMORY.md
cat /path/to/multi-nanobots/scout-workspace/MEMORY.md
```

## Gotchas

- You have full system access — use it responsibly
- Scout is sandboxed — don't expect Scout to access files outside its workspace
- Always read before writing to other workspaces

---

*Add whatever helps you do your job. This is your cheat sheet.*
