# RepoMem

**Persistent memory for AI coding agents.**  
Pure Python · SQLite + FTS5 · Zero dependencies · Zero API keys · Zero telemetry · MIT

---

> Your AI coding assistant forgets everything when the session ends.  
> RepoMem gives it a brain — one that remembers across sessions, across projects, across months.

## What it does

Every time a Claude Code session ends, RepoMem:
1. Extracts observations from the session (bugs fixed, decisions made, errors seen)
2. Stores them in a local SQLite + FTS5 database (`~/.repomem/memory.db`)
3. At the next session start, injects relevant context back into Claude's system prompt

The result: Claude arrives knowing what broke last time, what decisions were made, and what's still pending — without you having to repeat yourself.

## Install

```bash
git clone https://github.com/your-username/RepoMem
cd RepoMem && bash install.sh
```

Restart Claude Code. Done.

**Requirements:** Python 3.11+ · No other dependencies (stdlib only)

## Quick start

```bash
repomem status                           # DB stats
repomem doctor                           # health check
repomem search "null pointer crash"      # search memory
repomem search "database migration" --project my-app
repomem pending                          # open tasks
repomem decisions                        # architectural decisions
repomem server                           # web UI → http://localhost:39000
repomem tui                              # full-screen terminal UI
repomem graphify                         # god nodes for current repo
repomem obsidian                         # export to Obsidian vault
repomem sync --export                    # export for cross-machine sync
```

## How it works

```
Session ends
  → Stop hook → capture.py
    → extract observations (bugfix, decision, upgrade, warning, learning, error)
    → detect entities (PascalCase classes, files, libraries)
    → detect errors (Exception/Crash/FAILED patterns)
    → detect releases (version strings)
    → track current branch
    → write to memory.db

Session starts
  → SessionStart hook → inject.py
    → query decisions (global + project)
    → query pending tasks
    → rank observations by recency × confidence
    → show unresolved errors + conflicts
    → show graphify god nodes (if graph.json present)
    → inject as Claude system message (≤2000 chars)

Nightly (2am)
  → reflect.py: dedup, pattern promotion, contradiction detection, temporal decay

Weekly (Sunday 3am)
  → defrag.py: merge dupes, archive stale, trim oversized, rebuild FTS5, vacuum
```

## MCP tools

When Claude Code is connected to RepoMem's MCP server, it can query memory mid-session:

| Tool | Description |
|------|-------------|
| `repomem_search` | FTS5 search across all observations |
| `repomem_save` | Persist an observation immediately |
| `repomem_context` | Get full project context |
| `repomem_pending` | List open tasks |
| `repomem_decisions` | List architectural decisions |
| `repomem_add_pending` | Add a task |
| `repomem_resolve` | Mark task resolved |

## Observation types

| Type | Captured when |
|------|---------------|
| `bugfix` | "fixed crash", "resolved issue" |
| `decision` | "decided to use", "switched to" |
| `upgrade` | "upgraded to", "bumped version" |
| `warning` | "watch out", "never", "avoid" |
| `learning` | "learned", "discovered", "note:" |
| `pending` | "todo", "next:", "still need" |
| `pattern` | Promoted from observations seen in 3+ projects |
| `error` | Exception/Crash/FAILED + root cause + fix |

## CLI reference

```
repomem search <query> [--project] [--type] [--limit]
repomem add --type <type> --summary <text> [--detail] [--topic] [--project]
repomem pending [--project]
repomem add-pending <task> [--project] [--priority P1|P2|P3]
repomem resolve <id>
repomem decisions [--project]
repomem add-decision --decision <text> --topic <topic> [--scope] [--reason]
repomem status [--project]
repomem doctor
repomem entities [--project] [--name <entity>] [--min <count>]
repomem releases [--project] [--limit]
repomem branches [--project]
repomem sync --export | --import [--no-commit]
repomem obsidian [--project] [--vault <path>]
repomem graphify [--project] [--repo <path>] [--threshold <n>]
repomem tui
repomem server [--port 39000]
```

## Web viewer

```bash
repomem server
# open http://localhost:39000
```

Pages: Dashboard · Observations · Decisions · Pending · Errors · Projects · Search  
Dark mode · No build step · Keyboard shortcut: `/` to focus search

## Terminal UI

```bash
repomem tui
```

Keys: `j`/`k` navigate · `/` search · `Enter` detail · `o`/`p`/`d`/`e` switch mode · `q` quit

## Privacy

- All data stored locally in `~/.repomem/memory.db` — never leaves your machine
- Zero network calls, zero telemetry, zero API keys
- Wrap sensitive content in `<private>...</private>` — stripped before storage
- Override location: `export REPOMEM_DIR=/custom/path`

## Schema

15 tables across 4 phases:

| Table | Purpose |
|-------|---------|
| `sessions` | One row per Claude Code session |
| `observations` | All captured facts (FTS5 indexed) |
| `observations_fts` | FTS5 virtual table |
| `decisions` | Architectural choices, never re-litigate |
| `pending` | Open tasks across all projects |
| `patterns` | Reusable solutions seen in 3+ projects |
| `entities` | PascalCase classes, files, known libraries |
| `entity_links` | Entity ↔ observation links |
| `errors` | Crashes + root causes + fixes |
| `releases` | App store releases |
| `branches` | Git branch tracking |

See [SCHEMA.md](SCHEMA.md) for full column reference.

## Why not claude-mem / Engram / Basic Memory?

See [COMPARISON.md](COMPARISON.md) for a detailed breakdown. Short answer:

| | claude-mem | Engram | Basic Memory | **RepoMem** |
|---|---|---|---|---|
| Language | TypeScript | Go binary | Python | **Python** |
| External deps | Many | Binary | Some | **Zero** |
| Graphify integration | ❌ | ❌ | ❌ | **✅** |
| Sleep-time reflection | ❌ | ❌ | ✅ | **✅** |
| MCP server | ✅ | ✅ | ❌ | **✅** |
| Web viewer | ❌ | ❌ | ❌ | **✅** |
| Terminal UI | ❌ | ❌ | ❌ | **✅** |
| Obsidian sync | ❌ | ❌ | ❌ | **✅** |
| Git cross-machine sync | ❌ | ❌ | ❌ | **✅** |
| License | MIT | MIT | AGPL | **MIT** |

## License

MIT
