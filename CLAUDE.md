# RepoMem — Claude Code Context

## What is this project
RepoMem is a persistent memory system for AI coding agents.
Pure Python · SQLite + FTS5 · Zero dependencies · Zero API keys · Zero telemetry · MIT license.

## Status
- **All 4 phases COMPLETE** — 126/126 tests passing
- **Installed and running** at `~/.repomem/`
- **GitHub:** https://github.com/SUDARSHANCHAUDHARI/RepoMem (public, main branch)

## Architecture
```
repomem/
  config.py      ← paths, settings, topic keywords, OBS_TYPES
  models.py      ← Session, Observation, Decision, Pending, Pattern, SearchResult
  db.py          ← SQLite schema v3 + FTS5 triggers + CRUD + migrations
  capture.py     ← extracts observations, entities, errors, releases, branch tracking
  inject.py      ← builds context injection (2000 char cap, 8-section priority order)
  search.py      ← FTS5 + LIKE fallback search
  cli.py         ← 17 commands: search, add, pending, decisions, status, doctor,
                    entities, releases, branches, sync, obsidian, graphify, tui, server
  entity.py      ← PascalCase/file/library entity extraction + obs linking
  obsidian.py    ← export to Obsidian vault as wikilinked Markdown
  sync.py        ← cross-machine git sync (export/import JSON chunks)
  graphify.py    ← graphify-out/graph.json integration (god nodes, communities)
  tui.py         ← full-screen curses TUI (vim keys, 4 modes)
hooks/
  memory-capture.py  ← Stop hook (writes to DB at session end)
  memory-inject.py   ← SessionStart hook (reads from DB at session start)
server/
  mcp_server.py  ← stdio JSON-RPC MCP server (7 tools)
  web_viewer.py  ← stdlib http.server web UI (dark mode, port 39000)
skills/
  repomem-recall/    ← /recall upgrade
  repomem-add/       ← quick save during session
crons/
  reflect.py     ← nightly 2am: dedup, pattern promotion, contradiction detection
  defrag.py      ← weekly Sunday 3am: merge dupes, archive stale, vacuum
install.sh       ← one-command setup, auto-detects Python 3.11+, wires everything
```

## Database schema (15 tables, schema v3)
- `sessions` — one row per Claude Code session
- `observations` — all captured facts (FTS5 indexed), with conflict_id
- `observations_fts` — FTS5 virtual table
- `decisions` — architectural choices, never re-litigate
- `pending` — open tasks across all projects
- `patterns` — reusable solutions seen in 3+ projects
- `entities` — PascalCase classes, files, known libraries
- `entity_links` — entity ↔ observation many-to-many
- `errors` — crashes + root causes + fixes + recurrence
- `releases` — app releases auto-detected from session text
- `branches` — git branch tracking per project
- `schema_version` — auto-migration tracker

## Key decisions (never re-litigate)
- stdlib only — zero external deps (sqlite3, json, pathlib, http.server, curses)
- MIT license (AGPL complicates forks)
- ADD-only accumulation — archive instead of delete
- 2000 char injection cap — prevents token waste
- Priority order: decisions → pending → obs → conflicts → release warning → patterns → graphify → errors
- Tests use REPOMEM_DIR env var → tmp_path (never touches real ~/.repomem/)
- get_connection() reads REPOMEM_DIR dynamically — monkeypatch works in tests
- Session sentinel: CLI and MCP use session_id="manual" / "mcp" — _ensure_manual_session() creates the row
- Schema migrates automatically on init_db() from_version=0 on fresh DBs

## Running tests
```bash
python3.13 -m pytest tests/ -v
# Expected: 126/126 passing
```

## CLI usage
```bash
PYTHONPATH=~/.repomem/lib python3.13 -m repomem status
PYTHONPATH=~/.repomem/lib python3.13 -m repomem doctor
PYTHONPATH=~/.repomem/lib python3.13 -m repomem search "query"
PYTHONPATH=~/.repomem/lib python3.13 -m repomem server
# Or via wrapper (after install.sh):
~/.repomem/bin/repomem status
```

## Phase roadmap
```
Phase 1 ✅  Core: capture, inject, search, CLI, hooks, install
Phase 2 ✅  MCP server + entity linking + reflection + error tracking + temporal reasoning
Phase 3 ✅  Defrag + conflict detection + Obsidian sync + doctor + release/branch tracking + git sync
Phase 4 ✅  Graphify + web viewer + TUI + polish install + full docs
```

## Notes for Claude
- Never commit *.db files — gitignore covers this
- Never hardcode paths — use config.py or dynamic env var lookup
- capture.py strips <private> tags before storing anything
- Hooks must always exit 0 — never block session start/stop
- Never bypass hooks with --no-verify or core.hooksPath=/dev/null — fix the hook instead
- If a hook blocks something, STOP and ask — never self-resolve
- install.sh is idempotent — safe to re-run after updates
- graphify-out/graph.json exists — use `graphify query` for codebase questions
