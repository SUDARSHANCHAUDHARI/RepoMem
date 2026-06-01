# Changelog

All notable changes to RepoMem are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Added
- GitHub Actions CI (tests on Python 3.11/3.12/3.13, Ubuntu + macOS)
- Issue templates (bug report, feature request, question)
- PR template with checklist
- SECURITY.md with vulnerability reporting process
- CODE_OF_CONDUCT.md

---

## [0.1.0] — 2026-06-01

Initial open source release after 4 phases of development.

### Phase 4 — Open Source Release
- **Web viewer** (`repomem server`) — stdlib http.server, dark mode, 7 pages, port 39000
- **Terminal UI** (`repomem tui`) — full-screen curses UI, vim keys, 4 modes
- **Graphify integration** — god node detection, community tagging, session-start injection
- **Polish install** — auto-detect Python 3.11+, wrapper script, health check, idempotent cron
- **Full documentation** — README, SCHEMA, COMPARISON (12 tools), INSTALL, CONTRIBUTING

### Phase 3 — Polish + Integration
- **Defrag cron** — weekly: merge dupes (85% similarity), archive stale, trim oversized, rebuild FTS5, vacuum
- **Conflict detection** — contradicting decisions flagged and linked via `conflict_id`
- **Obsidian sync** (`repomem obsidian`) — export to vault as frontmatter + wikilinked Markdown
- **Doctor upgrade** — errors, conflicts, entities, FTS5 sync, orphans in one health check
- **Release tracking** — auto-detect version releases from session text, stale release warning
- **Branch tracking** — git branch auto-tracked per session
- **Git sync** (`repomem sync`) — cross-machine export/import via JSON chunks + watermark

### Phase 2 — Intelligence Layer
- **MCP server** (`server/mcp_server.py`) — 7 tools over stdio JSON-RPC, zero external deps
- **Entity linking** — PascalCase classes, files, known libraries extracted and linked to observations
- **Sleep-time reflection** (`crons/reflect.py`) — dedup, pattern promotion, contradiction detection
- **Temporal reasoning** — recency × confidence ranking, age labels on old observations
- **Error tracking** — auto-detect Exception/Crash/FAILED patterns, recurrence count, fix surfacing

### Phase 1 — Core Foundation
- **SQLite + FTS5 database** — 6 tables, FTS5 full-text search with triggers
- **Stop hook** (`hooks/memory-capture.py`) — auto-capture at session end
- **SessionStart hook** (`hooks/memory-inject.py`) — inject context at session start (≤2000 chars)
- **CLI** — search, add, pending, decisions, status, doctor (7 commands)
- **One-command install** (`bash install.sh`) — wires hooks, MCP, crons into Claude Code
- **Claude Code skills** — `/recall` and `/repomem-add`

---

[Unreleased]: https://github.com/your-username/RepoMem/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/RepoMem/releases/tag/v0.1.0
