# Contributing to RepoMem

Thank you for your interest in contributing to RepoMem — a persistent memory system for AI coding agents built entirely on Python's standard library.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [Development workflow](#development-workflow)
- [How to extend RepoMem](#how-to-extend-repomem)
- [Testing](#testing)
- [Code style](#code-style)
- [Submitting a pull request](#submitting-a-pull-request)

---

## Philosophy

Before contributing, understand the core constraints — these are non-negotiable:

| Constraint | Why |
|------------|-----|
| **Zero external dependencies** | RepoMem must work with only Python 3.11+ — no `pip install`, no npm, no compiled binaries. If it's not in the stdlib, it doesn't belong here. |
| **No telemetry** | Never add network calls, analytics, crash reporting, or opt-in/opt-out mechanisms of any kind. All data stays local. |
| **Tests required** | Every new module must have a corresponding `tests/test_<module>.py`. No exceptions. |
| **Hooks must always exit 0** | Hooks that block session start/stop are unacceptable — Claude Code must never be held up by RepoMem. Fail silently. |
| **Surgical changes** | Fix the problem. Don't refactor adjacent code, rename things, or "improve" code you didn't need to touch. |

---

## Getting started

### Prerequisites

- Python 3.11 or higher
- `pytest` for running tests (`pip install pytest` — this is the only dev dependency)
- Git

### Setup

```bash
# Clone the repo
git clone https://github.com/your-username/RepoMem
cd RepoMem

# Verify tests pass out of the box (no install needed)
python3 -m pytest tests/ -v

# Optional: install locally for manual testing
bash install.sh
```

### Verify your environment

```bash
# Should show 126 passed (or more if you added tests)
python3 -m pytest tests/ -q

# Should show DB healthy
PYTHONPATH=. python3 -m repomem doctor
```

---

## Project structure

```
RepoMem/
│
├── repomem/                  # Core Python package
│   ├── config.py             # Paths, env vars, topic keywords, OBS_TYPES
│   ├── models.py             # Dataclasses: Session, Observation, Decision, Pending, Pattern
│   ├── db.py                 # SQLite schema, FTS5 triggers, CRUD helpers, migrations
│   ├── capture.py            # Observation extraction from session text + private tag stripping
│   ├── inject.py             # Session-start context builder (2000 char cap, priority order)
│   ├── search.py             # FTS5 search + LIKE fallback + result formatting
│   ├── cli.py                # All 17 CLI commands (argparse entry point)
│   ├── entity.py             # Entity extraction (PascalCase, files, libraries) + linking
│   ├── obsidian.py           # Obsidian vault export (frontmatter + wikilinks)
│   ├── sync.py               # Cross-machine git sync (export/import JSON chunks)
│   ├── graphify.py           # Graphify graph.json integration (god nodes, communities)
│   ├── tui.py                # Full-screen terminal UI (curses, vim keys)
│   ├── __init__.py
│   └── __main__.py           # Enables `python3 -m repomem`
│
├── server/
│   ├── mcp_server.py         # MCP server — stdio JSON-RPC, 7 tools
│   └── web_viewer.py         # Web UI — stdlib http.server, dark mode, port 39000
│
├── hooks/
│   ├── memory-capture.py     # Claude Code Stop hook (writes to DB at session end)
│   └── memory-inject.py      # Claude Code SessionStart hook (reads from DB)
│
├── crons/
│   ├── reflect.py            # Nightly 2am: dedup, pattern promotion, contradiction detection
│   └── defrag.py             # Weekly Sunday 3am: merge dupes, archive stale, vacuum
│
├── skills/
│   ├── repomem-recall/       # Claude Code skill — /recall search
│   └── repomem-add/          # Claude Code skill — quick observation save
│
├── tests/                    # pytest test suite (126 tests)
│   ├── test_db.py
│   ├── test_capture.py
│   ├── test_inject.py
│   ├── test_entity.py
│   ├── test_errors.py
│   ├── test_reflect.py
│   ├── test_defrag.py
│   ├── test_sync.py
│   ├── test_obsidian.py
│   ├── test_releases.py
│   ├── test_graphify.py
│   ├── test_mcp_server.py
│   ├── test_web_viewer.py
│   └── test_tui.py
│
├── install.sh                # One-command setup (auto-detects Python, wires hooks + MCP + crons)
├── pyproject.toml            # Package metadata
├── README.md
├── SCHEMA.md                 # Full DB table + column reference
├── COMPARISON.md             # Detailed comparison with alternative tools
├── INSTALL.md                # Per-agent setup guide
└── CONTRIBUTING.md           # This file
```

---

## Development workflow

### Branching

```bash
# Always branch from main
git checkout main && git pull
git checkout -b feat/your-feature-name   # new feature
git checkout -b fix/your-bug-name        # bug fix
git checkout -b docs/your-doc-change     # documentation only
```

### Making changes

1. Read the file you're about to change — understand what's already there
2. Make the minimum change needed to solve the problem
3. Write or update tests before considering it done
4. Run the full test suite — all tests must pass

### Commit format

```
feat: short description of what was added
fix: short description of what was corrected
docs: documentation change
refactor: code restructure with no behaviour change
test: test additions or corrections
```

---

## How to extend RepoMem

### Add a new observation type

1. Add the type string to `OBS_TYPES` in `repomem/config.py`
2. Add a capture regex pattern in `extract_observations_from_text()` in `repomem/capture.py`
3. Add an icon to the type icon map in `repomem/inject.py`
4. Add an icon to the type icon map in `server/web_viewer.py`
5. Add a CSS badge class in `server/web_viewer.py` (`.badge-<type>`)
6. Add tests in `tests/test_capture.py`
7. Document in `README.md` observation types table

### Add a new DB table

1. Add the `CREATE TABLE IF NOT EXISTS` DDL to the `DDL` string in `repomem/db.py`
2. Add any required indexes to the DDL
3. Add CRUD helper functions below the existing ones
4. Add a migration step in `_run_migrations()` and bump `SCHEMA_VERSION`
5. Add tests in `tests/test_db.py`
6. Document the table in `SCHEMA.md`

### Add a new CLI command

1. Add `cmd_<name>(args)` function in `repomem/cli.py`
2. Add the argparse subparser in `main()` with help text and all arguments
3. Add the command to the `commands` dict
4. Add tests in `tests/test_cli.py`
5. Update the CLI reference table in `README.md`

### Add a new MCP tool

1. Add the tool definition object to the `TOOLS` list in `server/mcp_server.py`
   - Include `name`, `description`, `inputSchema` with all parameters documented
2. Add `handle_<tool_name>(args: dict) -> dict` handler function
3. Add the handler to the `HANDLERS` dict
4. Add a test in `tests/test_mcp_server.py`
5. Update the MCP tools table in `README.md`

### Add a new web viewer page

1. Add a `page_<name>()` function in `server/web_viewer.py`
2. Add the route to `do_GET()` in `RepoMemHandler`
3. Add the nav link to `_page()` nav_links list
4. Add a test in `tests/test_web_viewer.py`

---

## Testing

### Running tests

```bash
# Full suite
python3 -m pytest tests/ -v

# Single file
python3 -m pytest tests/test_capture.py -v

# By keyword
python3 -m pytest tests/ -k "search" -v

# Quick pass/fail
python3 -m pytest tests/ -q
```

### Test isolation

Every test file uses an `autouse` fixture that:
- Sets `REPOMEM_DIR` to a fresh `tmp_path` via `monkeypatch`
- Calls `init_db()` to create a clean schema
- Tears down automatically after each test

```python
@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    yield
```

**Rule: tests must never touch `~/.repomem/`.** Always use this fixture. If you see a test connecting directly to `db.DB_PATH` (the module-level constant), it is wrong — use `db.get_connection()` instead, which reads `REPOMEM_DIR` dynamically.

### Testing curses (TUI)

The TUI uses `curses` which requires a real terminal. Tests mock `curses` functions and test the data loading and key handling logic directly — never the actual curses rendering. See `tests/test_tui.py` for the pattern.

### Testing the MCP server

The MCP server tests monkey-patch `ok()` and `err()` to capture responses instead of writing to stdout. See `tests/test_mcp_server.py` for the pattern.

---

## Code style

RepoMem doesn't enforce a formatter or linter. Follow these principles instead:

| Rule | Detail |
|------|--------|
| Readable over clever | If a junior dev can't understand it in 30 seconds, simplify it |
| Docstrings sparingly | Only when the *why* is non-obvious — not what the code already says |
| No stdout in library code | Library modules write to the log file, not stdout. Only CLI and hooks print to stdout |
| Type hints on public functions | Add `-> type` return hints and parameter types on public functions |
| Error handling | Catch specific exceptions. Never swallow errors silently in non-hook code |
| Hooks exit 0 always | Wrap hook `main()` in a broad try/except and always `sys.exit(0)` |

---

## Submitting a pull request

1. **Fork** the repo and create a feature branch from `main`
2. **Write tests** — all existing tests must pass, new code needs new tests
3. **No new dependencies** — `pip install` nothing
4. **Update docs** if you:
   - Add a CLI command → update `README.md` CLI table
   - Add a DB table → update `SCHEMA.md`
   - Change install behaviour → update `INSTALL.md`
5. **Check for personal info** — no usernames, local paths, or org names in docs or source
6. **Open a PR** with a clear title and description of what changed and why

### PR checklist

- [ ] All tests pass (`python3 -m pytest tests/ -q`)
- [ ] No new external dependencies added
- [ ] New code has corresponding tests
- [ ] Docs updated if needed (README, SCHEMA, INSTALL)
- [ ] No personal paths, usernames, or org names in changed files

---

## Reporting bugs

Open a GitHub issue with:
- Python version (`python3 --version`)
- RepoMem version (commit hash or tag)
- Steps to reproduce
- Expected vs actual behaviour
- Output of `repomem doctor`

---

## Questions

Open a GitHub issue with the `question` label. There's no Slack, Discord, or mailing list.
