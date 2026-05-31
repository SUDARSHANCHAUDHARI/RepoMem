# RepoMem

**Persistent memory for AI coding agents.**  
Pure Python · SQLite + FTS5 · Zero dependencies · Zero API keys · Zero telemetry · MIT

---

> Your AI coding assistant forgets everything when the session ends.  
> RepoMem gives it a brain — one that remembers across sessions, across projects, across weeks.

## Why RepoMem?

| | claude-mem | Engram | RepoMem |
|---|---|---|---|
| Language | TS (compiled) | Go (binary) | **Python (readable)** |
| API key | No | No | **No** |
| Telemetry | Unknown | No | **No** |
| Storage | SQLite+Chroma | SQLite+FTS5 | **SQLite+FTS5** |
| 190+ repos | ✅ | ✅ | **✅** |
| Graphify sync | ❌ | ❌ | **✅ (Phase 4)** |
| Android-specific | ❌ | ❌ | **✅** |
| Auditable | ❌ | Partial | **✅ 100%** |

## Install

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/RepoMem
cd RepoMem && bash install.sh
```

Restart Claude Code. Done.

## How it works

```
Session ends → Stop hook → capture.py extracts observations → memory.db
Session starts → SessionStart hook → inject.py queries memory.db → injected as context
/repomem-recall → CLI search across all 190 repos
```

## Quick Start

```bash
# Search past observations
repomem search "HomeViewModel crash"
repomem search "Room migration" --project DreamWeave

# Add observation manually
repomem add --type bugfix --summary "Fixed null pointer in HomeViewModel" --topic viewmodel

# View pending tasks
repomem pending
repomem pending --project DreamWeave

# Add pending task
repomem add-pending "Add ProGuard rules for Retrofit 3.x" --project DreamWeave --priority P1

# Architectural decisions
repomem decisions

# Stats
repomem status
repomem status --project DreamWeave

# Health check
repomem doctor
```

## Observation types

| Type | When |
|---|---|
| `bugfix` | Bug fixed — what was broken + how fixed |
| `decision` | Architectural choice made |
| `upgrade` | Version/dependency change |
| `warning` | Watch out for this |
| `learning` | New knowledge |
| `pending` | Next session task |
| `pattern` | Reusable solution |
| `error` | Crash/exception + root cause |

## Privacy

- All data stored locally in `~/.repomem/memory.db`
- Zero network calls
- Zero telemetry
- Wrap sensitive content in `<private>...</private>` — never stored
- Override location: `export REPOMEM_DIR=/custom/path`

## Schema

6 tables in Phase 1:
- `sessions` — one per Claude Code session
- `observations` — all captured facts (FTS5 indexed)
- `observations_fts` — FTS5 virtual table for fast full-text search
- `decisions` — architectural choices, never re-litigate
- `pending` — open tasks across all projects
- `patterns` — reusable solutions seen in 2+ projects

## Roadmap

- **Phase 1** (current) — Core: capture, inject, search, CLI
- **Phase 2** — MCP server, entity linking, sleep-time reflection, error tracking
- **Phase 3** — Conflict detection, Obsidian sync, git sync, doctor
- **Phase 4** — Graphify integration, web viewer, TUI, open source release

## Requirements

- Python 3.11+
- Claude Code (for hooks) or any MCP-compatible AI
- No other dependencies — stdlib only

## License

MIT © 2026 SudarshanTechLabs
