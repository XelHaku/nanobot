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

| Agent | Port | Status | Check |
|-------|------|--------|-------|
| main | 18790 | — | `curl -s http://localhost:18790/health` |
| scout | 18791 | — | `curl -s http://localhost:18791/health` |
| coordinator | 18792 | — | `curl -s http://localhost:18792/health` |

## Useful Commands

```bash
# Check all agent statuses
supervisorctl -c /path/to/multi-nanobots/supervisord.conf status

# Restart a specific agent
supervisorctl -c /path/to/multi-nanobots/supervisord.conf restart main

# Restart all agents
supervisorctl -c /path/to/multi-nanobots/supervisord.conf restart all

# View agent logs
tail -f /path/to/multi-nanobots/logs/main.log
```

## Gotchas

- (Add environment-specific notes here)

---

*Add whatever helps you do your job. This is your cheat sheet.*
