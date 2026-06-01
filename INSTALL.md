# RepoMem Installation Guide

---

## Requirements

- Python 3.11 or higher
- No other dependencies — RepoMem uses stdlib only

Check your Python version:
```bash
python3 --version
# Need 3.11+. Install via: brew install python@3.13
```

---

## Quick install (recommended)

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/RepoMem
cd RepoMem
bash install.sh
```

The script:
1. Detects Python 3.11+ (tries python3.13, 3.12, 3.11, python3)
2. Installs package to `~/.repomem/lib/`
3. Creates `~/.repomem/bin/repomem` wrapper script
4. Copies hooks to `~/.claude/hooks/`
5. Wires Stop + SessionStart hooks into `~/.claude/settings.json`
6. Wires MCP server into `~/.claude/settings.json`
7. Adds cron jobs (reflect: 2am daily, defrag: Sunday 3am)
8. Initializes the SQLite database
9. Runs a health check

After install, add `repomem` to your PATH if not auto-linked:
```bash
echo 'export PATH="$PATH:$HOME/.repomem/bin"' >> ~/.zshrc
source ~/.zshrc
```

---

## Per-agent setup

### Claude Code (recommended)

`install.sh` handles everything automatically. After running it:

1. **Restart Claude Code** — hooks activate on next launch
2. Verify: run `repomem status` in terminal
3. Verify MCP: in Claude Code, ask "what repomem tools do you have?" — Claude should list 7 tools

**Manual wiring** (if `install.sh` couldn't find `settings.json`):

Add to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "REPOMEM_INSTALL=~/.repomem/lib python3 ~/.claude/hooks/memory-capture.py",
        "timeout": 30,
        "statusMessage": "RepoMem: saving session memory..."
      }]
    }],
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "REPOMEM_INSTALL=~/.repomem/lib python3 ~/.claude/hooks/memory-inject.py",
        "timeout": 10,
        "statusMessage": "RepoMem: loading project memory..."
      }]
    }]
  },
  "mcpServers": {
    "repomem": {
      "command": "python3",
      "args": ["~/.repomem/lib/server/mcp_server.py"],
      "env": {"REPOMEM_INSTALL": "~/.repomem/lib"}
    }
  }
}
```

### Cursor

Cursor supports MCP servers. Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "repomem": {
      "command": "python3",
      "args": ["~/.repomem/lib/server/mcp_server.py"],
      "env": {"REPOMEM_INSTALL": "~/.repomem/lib"}
    }
  }
}
```

For hooks, you'll need to wire them manually via Cursor's extension hooks or run captures manually:
```bash
repomem add --type learning --summary "what you learned this session"
```

### Gemini CLI / other agents

For any agent that supports MCP, point it at the MCP server:
```
Command: python3 ~/.repomem/lib/server/mcp_server.py
Env:     REPOMEM_INSTALL=~/.repomem/lib
```

For agents without MCP, use the CLI directly at the end of each session:
```bash
repomem add --type decision --summary "Used Ktor over Retrofit for KMP" --topic networking
repomem add-pending "Add unit tests for ViewModel" --project MyApp --priority P1
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REPOMEM_DIR` | `~/.repomem` | Override storage location |
| `REPOMEM_INSTALL` | `~/.repomem/lib` | Override package location (hooks) |
| `REPOMEM_PROJECT` | (auto) | Override project detection |
| `REPOMEM_OBSIDIAN_VAULT` | `~/obsidian-vault/RepoMem` | Override Obsidian vault path |
| `REPOMEM_PORT` | `39000` | Web viewer port |

---

## Verify installation

```bash
repomem status        # should show DB stats
repomem doctor        # should show ✅ All checks passed
repomem server        # open http://localhost:39000 in browser
repomem tui           # full-screen terminal UI (press q to quit)
```

---

## Uninstall

```bash
# Remove package and data
rm -rf ~/.repomem

# Remove hooks from settings.json (edit manually)
# Remove cron jobs
crontab -l | grep -v repomem | crontab -

# Remove symlink if created
rm -f /usr/local/bin/repomem
```

---

## Updating

```bash
cd ~/path/to/RepoMem
git pull
bash install.sh   # idempotent — re-runs safely
```

The install script is idempotent: it skips already-wired hooks and MCP entries.
