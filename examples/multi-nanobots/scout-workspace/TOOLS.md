# TOOLS.md — Local Notes

Skills define HOW tools work. This file is for YOUR specifics —
the stuff that's unique to your setup.

## Environment

- **OS**: (your OS, e.g., Linux Ubuntu 22.04)
- **User**: (your username)
- **Workspace**: ./scout-workspace (sandboxed)
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

- **exec** — Execute terminal commands (workspace-scoped)
- **read_file** — Read file contents (workspace-scoped)
- **write_file** — Write/create file contents (workspace-scoped)
- **edit_file** — Edit specific parts of a file (workspace-scoped)
- **list_dir** — List directory contents (workspace-scoped)
- **web_search** — Search the web

## Fleet Status

| Agent | Port | Role | Notes |
|-------|------|------|-------|
| main | 18790 | Lead dev | Full system access |
| **scout** | 18791 | Specialist | **You are here** (sandboxed) |
| coordinator | 18792 | Research lead | Full system access |

## Gotchas

- You are sandboxed — file operations are limited to your workspace
- If you need data from outside your workspace, ask the Coordinator

---

*Add whatever helps you do your job. This is your cheat sheet.*
