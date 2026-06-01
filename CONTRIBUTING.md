# Contributing to RepoMem

RepoMem is a personal tool built by SudarshanTechLabs for managing memory across 190+ repos.
Contributions are welcome — please read this first.

---

## Philosophy

- **Zero external dependencies** — stdlib only. No pip installs, no npm, no compiled binaries.
- **Surgical changes** — fix the problem, don't refactor the neighbourhood.
- **Tests required** — every new module needs a `tests/test_<module>.py`.
- **No telemetry** — never add network calls, analytics, or opt-in/opt-out anything.

---

## Setup

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/RepoMem
cd RepoMem

# Run tests (no install needed — stdlib only)
python3.11 -m pytest tests/ -v

# Install locally for manual testing
bash install.sh
```

---

## Project structure

```
repomem/          # Core Python package
  config.py       # Paths, settings, topic keywords
  models.py       # Dataclasses for every table
  db.py           # SQLite schema, CRUD, FTS5
  capture.py      # Observation extraction from session text
  inject.py       # Context injection for SessionStart
  search.py       # FTS5 + LIKE fallback search
  cli.py          # All CLI commands
  entity.py       # Entity extraction and linking
  obsidian.py     # Obsidian vault export
  sync.py         # Cross-machine git sync
  graphify.py     # Graphify integration
  tui.py          # Full-screen terminal UI (curses)
server/
  mcp_server.py   # MCP server (stdio JSON-RPC)
  web_viewer.py   # Web UI (stdlib http.server)
hooks/
  memory-capture.py   # Stop hook
  memory-inject.py    # SessionStart hook
crons/
  reflect.py      # Nightly reflection
  defrag.py       # Weekly cleanup
skills/
  repomem-recall/ # /recall upgrade skill
  repomem-add/    # Quick save skill
tests/            # pytest test suite
install.sh        # One-command setup
```

---

## Adding a new observation type

1. Add the type to `OBS_TYPES` in `repomem/config.py`
2. Add a capture pattern to `extract_observations_from_text()` in `repomem/capture.py`
3. Add icon mapping in `repomem/inject.py` and `server/web_viewer.py`
4. Add tests in `tests/test_capture.py`

## Adding a new DB table

1. Add the DDL to the `DDL` string in `repomem/db.py`
2. Add CRUD helpers below the existing ones
3. Update `SCHEMA_VERSION` in `repomem/db.py`
4. Add tests in `tests/test_db.py`
5. Document in `SCHEMA.md`

## Adding a new CLI command

1. Add `cmd_<name>(args)` function in `repomem/cli.py`
2. Add the argparse subparser in `main()`
3. Add to the `commands` dict
4. Update README.md CLI reference

## Adding a new MCP tool

1. Add the tool definition to `TOOLS` in `server/mcp_server.py`
2. Add `handle_<tool_name>(args)` handler
3. Add to `HANDLERS` dict
4. Add a test in `tests/test_mcp_server.py`

---

## Testing

```bash
# Run all tests
python3.11 -m pytest tests/ -v

# Run specific file
python3.11 -m pytest tests/test_capture.py -v

# Tests use REPOMEM_DIR env var to isolate from real ~/.repomem
# Each test gets a fresh tmp_path via the autouse fixture
```

**Rule:** Tests must never touch `~/.repomem/`. Always use the `temp_db` fixture.

---

## Code style

- No type stubs, no mypy, no black — just readable Python
- Docstrings only when the WHY is non-obvious
- No logging to stdout in library code — use the log file
- All hooks must exit 0 — never block a session

---

## Pull requests

1. Fork → feature branch → PR to `main`
2. All 100 tests must pass
3. No new external dependencies
4. Update `SCHEMA.md` if you change the DB schema
5. Update `README.md` CLI reference if you add a command
