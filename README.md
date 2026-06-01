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

---

## Install

```bash
git clone https://github.com/your-username/RepoMem
cd RepoMem && bash install.sh
```

Restart Claude Code. Done.

**Requirements:** Python 3.11+ · No other dependencies (stdlib only)

---

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

---

## How it works

```
Session ends
  → Stop hook → capture.py
    → extract observations (bugfix, decision, upgrade, warning, learning, error)
    → detect entities (PascalCase classes, files, libraries)
    → detect errors (Exception/Crash/FAILED patterns)
    → detect releases (version strings)
    → track current git branch
    → write to ~/.repomem/memory.db

Session starts
  → SessionStart hook → inject.py
    → query decisions (global + project-scoped)
    → query open pending tasks
    → rank observations by recency × confidence
    → show unresolved errors + conflicts
    → show graphify god nodes (if graph.json present)
    → inject as Claude system message (≤2000 chars)

Nightly (2am cron)
  → reflect.py: dedup, pattern promotion, contradiction detection, temporal decay

Weekly (Sunday 3am cron)
  → defrag.py: merge dupes, archive stale, trim oversized, rebuild FTS5, vacuum
```

---

## MCP tools

When Claude Code is connected to RepoMem's MCP server, it can query memory mid-session without any prompting:

| Tool | What it does |
|------|-------------|
| `repomem_search` | FTS5 full-text search across all observations |
| `repomem_save` | Persist an observation immediately during a session |
| `repomem_context` | Get the full project context (decisions + pending + recent obs) |
| `repomem_pending` | List all open tasks, optionally filtered by project |
| `repomem_decisions` | List architectural decisions (global + project-scoped) |
| `repomem_add_pending` | Add a pending task to the queue |
| `repomem_resolve` | Mark a pending task as resolved by ID |

---

## Observation types

RepoMem captures 8 structured observation types automatically from session text:

| Type | Auto-detected from | Example |
|------|--------------------|---------|
| `bugfix` | "fixed crash", "resolved issue", "repaired bug" | Fixed null pointer in UserRepository |
| `decision` | "decided to use", "switched to", "migrated to" | Use dependency injection over manual wiring |
| `upgrade` | "upgraded to", "bumped version", "updated" | Upgraded database library to 2.8.4 |
| `warning` | "watch out", "never", "avoid", "caution" | Never cache this value across config reloads |
| `learning` | "learned", "discovered", "found out", "note:" | Learned that background tasks need lifecycle scope |
| `pending` | "todo", "next:", "still need", "needs to" | Still need to write migration rollback tests |
| `pattern` | Auto-promoted from observations seen in 3+ projects | Use fake repository pattern for unit testing |
| `error` | Exception/Crash/FAILED + root cause + fix | NullPointerException in onCreate — fixed by null check |

---

## Interfaces

### CLI

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

### Web viewer

```bash
repomem server
# open http://localhost:39000
```

| Page | Content |
|------|---------|
| Dashboard | Stats overview + recent observations + unresolved errors |
| Observations | Browsable / filterable observation list |
| Decisions | All architectural decisions by scope |
| Pending | Open task queue with priority |
| Errors | Unresolved errors with recurrence count and fix |
| Projects | All tracked projects with activity stats |
| Search | Full-text search across all observations |

Dark mode · No build step · Press `/` to focus search from any page

### Terminal UI

```bash
repomem tui
```

| Key | Action |
|-----|--------|
| `j` / `↓` | Move down |
| `k` / `↑` | Move up |
| `Enter` | Open detail view |
| `/` | Enter search mode |
| `Esc` | Exit search |
| `o` | Switch to Observations |
| `p` | Switch to Pending |
| `d` | Switch to Decisions |
| `e` | Switch to Errors |
| `r` | Refresh data |
| `q` | Quit |

---

## Schema

15 tables across 4 phases of development:

| Table | Phase | Purpose |
|-------|-------|---------|
| `sessions` | 1 | One row per Claude Code session |
| `observations` | 1 | All captured facts (FTS5 indexed) |
| `observations_fts` | 1 | FTS5 virtual table for fast full-text search |
| `decisions` | 1 | Architectural choices — never re-litigate |
| `pending` | 1 | Open tasks across all projects |
| `patterns` | 1 | Reusable solutions seen in 3+ projects |
| `entities` | 2 | PascalCase classes, files, known libraries |
| `entity_links` | 2 | Entity ↔ observation many-to-many links |
| `errors` | 2 | Crashes + root causes + fixes + recurrence count |
| `releases` | 3 | App store releases auto-detected from session text |
| `branches` | 3 | Git branch tracking per project |

See [SCHEMA.md](SCHEMA.md) for full column-level documentation.

---

## Privacy

| Guarantee | Detail |
|-----------|--------|
| Local only | All data stored in `~/.repomem/memory.db` — never leaves your machine |
| No network | Zero outbound connections, ever |
| No telemetry | No usage data, no crash reports, nothing |
| No API keys | No OpenAI, no Anthropic, no external services |
| Private tags | Wrap sensitive content in `<private>...</private>` — stripped before storage |
| Custom path | `export REPOMEM_DIR=/your/path` to relocate the database |

---

## vs. Alternatives

Short version — see [COMPARISON.md](COMPARISON.md) for the full breakdown:

| | claude-mem | Engram | Basic Memory | mem0 | **RepoMem** |
|---|:---:|:---:|:---:|:---:|:---:|
| Zero dependencies | ❌ | ❌ | ❌ | ❌ | ✅ |
| Zero API keys | ✅ | ✅ | ✅ | ❌ | ✅ |
| SessionStart injection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Sleep-time reflection | ❌ | ❌ | ✅ | ❌ | ✅ |
| Conflict detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| MCP server | ✅ | ✅ | ❌ | ❌ | ✅ |
| Web viewer | ❌ | ❌ | ❌ | ❌ | ✅ |
| Terminal UI | ❌ | ❌ | ❌ | ❌ | ✅ |
| Obsidian sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Git cross-machine sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Schema migrations | ❌ | ❌ | ❌ | ❌ | ✅ |
| License | MIT | MIT | AGPL | Apache 2 | **MIT** |

---

## License

MIT
