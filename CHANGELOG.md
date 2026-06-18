# Changelog

All notable changes to RepoMem are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Added
- **Optional semantic search** — `repomem search <q> --semantic` ranks observations by embedding cosine similarity. Fully opt-in via `pip install repomem[semantic]`; the default install stays zero-dependency and FTS5 is always the fallback (with a hint if the extra is missing). Embeddings live in their own `embeddings` table created on demand — core schema untouched. ([repomem/semantic.py](repomem/semantic.py))
- **Benchmark harness** — `bench/run_benchmark.py` measures recall@k for `fts` vs `semantic` modes, with a synthetic sample dataset and instructions for plugging in LongMemEval / LoCoMo. ([bench/](bench/))

---

## [0.3.0] — 2026-06-16

### Added
- `answer` primitive — `repomem answer "<question>"` and the `repomem_answer` MCP tool return a grounded, #id-cited block (observations + relevant decisions + unresolved errors) for the host agent to answer from. No LLM call, no API key. ([repomem/answer.py](repomem/answer.py))
- `repomem mcp-config --client <claude|cursor|windsurf|cline|codex>` prints the MCP server config snippet — the stdio server already works with any MCP client, this makes it discoverable
- MCP server now exposes 8 tools (was 7); CLI now has 22 commands (was 20)

---

## [0.2.2] — 2026-06-02

### Fixed
- `capture.py`: graphify enrichment was silently dead — `find_graph` was imported but the function is named `load_graph`; the `ImportError` was swallowed by `except Exception: pass`, meaning god-node enrichment never ran for any user since launch
- `web_viewer.py`: XSS — all database values rendered into HTML were unescaped; stack traces with `<`/`>` corrupted HTML, and malicious session content could execute JS in the local browser. Added `html.escape()` to every db field
- `search.py`: `_like_search` (FTS5 fallback) used hardcoded `DB_PATH` ignoring `REPOMEM_DIR` env var — wrong database hit for any non-default install path. Now uses `get_connection()` which already reads env var correctly
- `mcp_server.py`: tool errors leaked install path via `str(e)` — now returns a generic message; full error still logged
- `mcp_server.py`: `resources/list` and `prompts/list` returned `-32601 Method not found` causing noisy MCP client warnings — now returns empty list
- `mcp_server.py`: MCP `detail` field was uncapped — added 5000 char limit at ingestion
- `db.py`: `_col_exists()` PRAGMA f-string — added table whitelist to guard against future injection risk

---

## [0.2.1] — 2026-06-02

### Fixed
- `capture.py`: `detect_topic()` word-boundary fix was defined in config but never applied — short keywords like `"di"` now correctly use `\b` regex so `"audio"` no longer matches the `di` topic
- `capture.py`: `_RELEASE_SIGNALS` patterns were incomplete — `uploaded AAB`, `versionName`, `TestFlight build`, `git tag v`, and `bumped to` now correctly captured
- `mcp_server.py`: `handle_repomem_save` was missing `link_observation()` call — MCP-saved observations now get entity linking (was documented in 0.2.0 but not implemented)
- `pyproject.toml`: build backend changed from `setuptools.backends.legacy:build` to `setuptools.build_meta` — fixes PyPI publish on standard CI environments

### Changed
- Test fixtures use generic class names (`OrderService`, `UserRepository`) instead of Android-specific `HomeViewModel`
- Repo made public on GitHub with branch protection (no force push, CI required to merge)
- Dependabot enabled for weekly GitHub Actions version bumps

---

## [0.2.0] — 2026-06-01

19 improvements derived from deep study of `claude-code-memory-setup` and a line-by-line audit of RepoMem's own code.

### Fixed
- `db.py`: `get_stats()` used hardcoded `DB_PATH` for DB size — now reads from `REPOMEM_DIR` env var like `get_connection()` does
- `mcp_server.py`: `repomem_save` tool was missing `link_observation()` call — MCP-saved observations now get entity extraction and linking
- `capture.py`: `detect_topic()` used substring matching for all keywords — short keywords (`di`, `ui`, `sql`, `api`, `ksp`, `r8`, `orm`) now use word-boundary matching to prevent false positives (`"audio"` → `di`, `"build"` → `ui`)
- `capture.py`: `_RELEASE_SIGNALS` missed common Android/iOS patterns — now detects `versionName`, `uploaded AAB/APK`, `TestFlight build`, `git tag v`, `bumped to`, `App Store Connect`, `tagged v`

### Added
- `repomem/utils.py`: new shared `text_similarity()` utility — eliminates identical `_similarity()` function duplicated in `reflect.py` and `defrag.py`
- `obsidian.py`: **vault-aware wikilinks** — scans real `.md` files in the vault, links to existing notes (not blind PascalCase), code-block-safe, first-occurrence-only, longest-match-first, double-link prevention
- `obsidian.py`: **dynamic topic tags** in frontmatter — collects unique topic values from observations and adds them as Obsidian tags (e.g. `tags: [repomem, project-memory, ui, di, networking]`)
- `obsidian.py`: **`type:`, `status:`, `source:`, `processed:`** fields in frontmatter — enables Obsidian Dataview queries
- `obsidian.py`: **patterns section** — `🔁 Patterns` now exported per project
- `obsidian.py`: **releases section** — `🚀 Releases` now exported per project (Play Store + App Store history)
- `obsidian.py`: **open branches section** — `🌿 Open Branches` now exported per project
- `obsidian.py`: wikilinks now applied to **decisions, errors, and pending text** — not just observation summaries
- `obsidian.py`: **`--no-wikilinks`** flag on `repomem obsidian` command
- `cli.py`: **`repomem resolve-error <id>`** — mark a tracked error as resolved (db function existed, no CLI)
- `cli.py`: **`repomem merge-branch <branch>`** — mark a branch as merged with optional `--pr-number` / `--pr-url` (db function existed, no CLI)
- `cli.py`: **`repomem import-chat <file.md>`** — import a raw exported Claude session into memory via the existing `capture.py` pipeline; `--project` override, `--move` to delete source after import
- `inject.py`: top 3 frequently-touched entities (≥3 mentions) now surfaced in session-start context under `HOT ENTITIES`
- `config.py`: `SHORT_TOPIC_KEYWORDS` set exported for use in topic detection
- Tests: 146 → 186 (+40 new tests covering all 19 items)

---

## [0.1.1] — 2026-06-01

### Added
- `/repomem` Claude Code skill — consolidated single skill replacing `repomem-add` + `repomem-recall` sub-skills; auto-installed by `install.sh`
- `tests/test_config.py` — 9 tests for config path resolution, env override, `ensure_dirs()`
- `.github/workflows/publish.yml` — PyPI trusted publish on `v*` tag with version sync gate
- Version sync check in CI — `pyproject.toml` and `__init__.py` must match on every push

### Fixed
- `install.sh` now auto-creates `~/.claude/skills/` if missing; removes stale `repomem-add`/`repomem-recall` sub-skills on upgrade
- `graphify-out/` added to `.gitignore`
- Comparison tables (README + COMPARISON.md) fully re-verified against all 11 competitor repos — corrected stars, licenses, feature claims
- Acknowledgements expanded with proper per-repo credit table
- `Development Status` upgraded from Alpha → Beta in `pyproject.toml`

---

## [0.1.0] — 2026-06-01

Initial open source release after 4 phases of development.

### Phase 4 — Open Source Release
- **Web viewer** (`repomem server`) — stdlib http.server, dark mode, 7 pages, port 39000
- **Terminal UI** (`repomem tui`) — full-screen curses UI, vim keys, 4 modes
- **Graphify integration** — god node detection, community tagging, session-start injection
- **Polish install** — auto-detect Python 3.11+, wrapper script, health check, idempotent cron
- **Full documentation** — README, SCHEMA, COMPARISON (12 tools), INSTALL, CONTRIBUTING
- **GitHub Actions CI** — tests on Python 3.11/3.12/3.13 × Ubuntu + macOS, stdlib-only guard
- **Issue templates** — bug report, feature request, question
- **`/repomem` Claude Code skill** — consolidated single skill replacing sub-skills, auto-installed by `install.sh`
- **Verified comparison tables** — all 11 competitor repos checked against live GitHub
- **Proper acknowledgements** — per-repo credit table for everything borrowed

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
- **Claude Code skill** — `/repomem` (consolidated, covers all memory operations)

---

[Unreleased]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/releases/tag/v0.1.1
[0.1.0]: https://github.com/SUDARSHANCHAUDHARI/RepoMem/releases/tag/v0.1.0
