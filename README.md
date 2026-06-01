# RepoMem

[![Tests](https://github.com/SUDARSHANCHAUDHARI/RepoMem/actions/workflows/tests.yml/badge.svg)](https://github.com/SUDARSHANCHAUDHARI/RepoMem/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Persistent memory for AI coding agents.**  
Pure Python · SQLite + FTS5 · Zero dependencies · Zero API keys · Zero telemetry · MIT

---

> Your AI coding assistant forgets everything when the session ends.  
> RepoMem gives it a brain — one that remembers across sessions, across projects, across months.

---

## What it does

Every time a Claude Code session ends, RepoMem:
1. Extracts structured observations from the session (bugs fixed, decisions made, errors seen)
2. Stores them in a local SQLite + FTS5 database at `~/.repomem/memory.db`
3. At the next session start, injects relevant context back as a Claude system message

The result: Claude arrives knowing what broke last time, what decisions were made, and what's still pending — without you having to repeat yourself.

---

## Install

```bash
git clone https://github.com/SUDARSHANCHAUDHARI/RepoMem
cd RepoMem && bash install.sh
```

Restart Claude Code. Done.

**Requirements:** Python 3.11+ · No other dependencies (stdlib only)

`install.sh` handles everything automatically:

| Step | What happens |
|------|-------------|
| Python detection | Finds Python 3.11/3.12/3.13 automatically |
| Package install | Copies package to `~/.repomem/lib/` |
| Hook wiring | Registers Stop + SessionStart hooks in Claude Code settings |
| MCP server | Registers MCP server in Claude Code settings |
| Skill install | Installs `/repomem` skill to `~/.claude/skills/repomem/` |
| Cron jobs | Adds nightly reflection + weekly defrag |
| Health check | Verifies DB is initialized and healthy |

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

## Claude Code skill — `/repomem`

RepoMem ships a native Claude Code skill at `skills/repomem/`. Once installed, type `/repomem` in any Claude Code session to get a full memory interface without touching the CLI.

**Install the skill:**

`install.sh` handles this automatically. If you need to reinstall manually:
```bash
mkdir -p ~/.claude/skills/repomem
cp skills/repomem/SKILL.md ~/.claude/skills/repomem/
```

**Triggers:**

| You type | What happens |
|----------|-------------|
| `/repomem` | Status + recent observations for current project |
| `"save this to memory"` | Saves current context as an observation |
| `"what did we fix before?"` | Searches memory for past bugfixes |
| `"add pending task"` | Adds a task to the pending queue |
| `"show decisions"` | Lists architectural decisions |
| `"open web UI"` | Starts `repomem server` → http://localhost:39000 |
| `"sync memory"` | Runs `repomem sync --export` |

The skill is **Claude Code-only** — it uses Claude Code's `SKILL.md` format. The underlying RepoMem tool is AI-agnostic and works with any agent that can run CLI commands.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code session                      │
└────────────────┬───────────────────────────┬────────────────┘
                 │ session ends               │ session starts
                 ▼                            ▼
        ┌──────────────┐             ┌──────────────────┐
        │  Stop hook   │             │ SessionStart hook │
        │ capture.py   │             │   inject.py       │
        └──────┬───────┘             └────────┬─────────┘
               │ write                         │ read + rank
               ▼                               ▼
        ┌──────────────────────────────────────────────┐
        │           ~/.repomem/memory.db               │
        │  SQLite + FTS5 · 15 tables · local only      │
        └──────┬───────────────────────────────────────┘
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
 reflect.py  defrag.py    MCP server
 (2am daily) (Sun 3am)  (mid-session)
```

**What happens at session end:**

| Step | Detail |
|------|--------|
| Extract observations | Regex patterns detect bugfix/decision/upgrade/warning/learning/error/pending |
| Tag topics | Keywords match build, networking, database, compose, etc. |
| Link entities | PascalCase classes, known libraries, filenames extracted and linked |
| Detect errors | Exception/Crash/FAILED patterns captured with root cause + fix |
| Detect releases | "released v1.2.0" / "Play Store upload" patterns |
| Track branch | `git branch --show-current` saved per project |
| Store | All written to SQLite with FTS5 triggers for instant search |

**What gets injected at session start (priority order):**

| Priority | Content | Cap |
|----------|---------|-----|
| 1 | Global + project architectural decisions | up to 20 |
| 2 | Open pending tasks for this project | up to 5 |
| 3 | Recent observations ranked by recency × confidence | up to 10 |
| 4 | Conflict warnings (contradicting decisions) | up to 4 |
| 5 | Release age warning (if >90 days since last release) | 1 line |
| 6 | Graphify god nodes (high-blast-radius files) | up to 5 |
| 7 | Unresolved errors with fixes | up to 3 |
| — | **Hard cap: ≤2000 characters total** | — |

---

## MCP tools

When Claude Code connects to RepoMem's MCP server, 7 tools become available mid-session:

| Tool | Arguments | What it does |
|------|-----------|-------------|
| `repomem_search` | `query`, `project?`, `type?`, `limit?` | FTS5 full-text search across all observations |
| `repomem_save` | `type`, `summary`, `detail?`, `topic?`, `project?` | Persist an observation immediately |
| `repomem_context` | `project?` | Full project context (decisions + pending + recent obs) |
| `repomem_pending` | `project?` | List all open tasks |
| `repomem_decisions` | `scope?` | Architectural decisions (global or project-scoped) |
| `repomem_add_pending` | `task`, `project?`, `priority?` | Add a pending task to the queue |
| `repomem_resolve` | `id` | Mark a pending task as resolved |

---

## Observation types

RepoMem captures 8 structured types automatically from session text:

| Type | Trigger phrases | What gets stored |
|------|-----------------|-----------------|
| `bugfix` | "fixed crash", "resolved issue", "repaired bug" | What was broken + how it was fixed |
| `decision` | "decided to use", "switched to", "migrated to" | The choice made and why |
| `upgrade` | "upgraded to", "bumped version", "updated" | Library/tool and new version |
| `warning` | "watch out", "never", "avoid", "caution" | The thing to remember not to do |
| `learning` | "learned", "discovered", "found out", "note:" | New knowledge gained |
| `pending` | "todo", "next:", "still need", "needs to" | Work left for next session |
| `pattern` | Auto-promoted from obs seen in 3+ projects | Reusable solution across codebases |
| `error` | Exception / Crash / FAILED / fatal | Error text + root cause + fix |

---

## Interfaces

### CLI — 17 commands

| Command | Description |
|---------|-------------|
| `repomem search <q>` | FTS5 full-text search, optional `--project`, `--type`, `--limit` |
| `repomem add` | Manually add an observation (`--type`, `--summary`, `--detail`) |
| `repomem pending` | List open tasks, optional `--project` |
| `repomem add-pending <task>` | Add a task with `--priority P1/P2/P3` |
| `repomem resolve <id>` | Mark a pending task resolved |
| `repomem decisions` | List architectural decisions |
| `repomem add-decision` | Record a decision with `--topic`, `--scope`, `--reason` |
| `repomem status` | DB stats: obs count, sessions, projects, DB size |
| `repomem doctor` | Health: FTS5 sync, conflicts, unresolved errors, orphans |
| `repomem entities` | List extracted entities; `--name` to find obs by entity |
| `repomem releases` | List auto-detected releases |
| `repomem branches` | List tracked open branches |
| `repomem sync` | `--export` to git chunk, `--import` to merge peers |
| `repomem obsidian` | Export to Obsidian vault as wikilinked Markdown |
| `repomem graphify` | God nodes for current repo, `--threshold` edges |
| `repomem tui` | Full-screen terminal UI |
| `repomem server` | Start web viewer, default port 39000 |

### Web viewer

```bash
repomem server    # → http://localhost:39000
```

| Page | Content |
|------|---------|
| Dashboard | Stats overview + recent observations + unresolved errors |
| Observations | Browsable list with type badge, project, date |
| Decisions | All decisions by scope (global / project) |
| Pending | Task queue sorted by priority (P1 → P3) |
| Errors | Unresolved errors, recurrence count, known fix |
| Projects | All projects, observation count, last activity date |
| Search | Full-text search across all observations |

Dark mode · No build step · Press `/` to focus search from any page

### Terminal UI

```bash
repomem tui
```

| Key | Action |
|-----|--------|
| `j` / `↓` | Move cursor down |
| `k` / `↑` | Move cursor up |
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

## Background automation

| Job | Schedule | What it does |
|-----|----------|-------------|
| `reflect.py` | 2am daily | Dedup near-identical obs (80% similarity), promote cross-project patterns (3+ projects), flag contradictions, apply confidence decay (90d, <0.5 confidence) |
| `defrag.py` | Sunday 3am | Merge dupes (85% similarity), archive stale low-confidence obs, trim oversized detail to 2000 chars, rebuild FTS5 index, vacuum DB |

---

## Schema

15 tables across 4 phases of development:

| Table | Phase | Key columns |
|-------|-------|-------------|
| `sessions` | 1 | id, project, folder, repo_path, started_at, ended_at, obs_count |
| `observations` | 1 | type, topic, summary, detail, confidence, seen_count, is_stale, conflict_id |
| `observations_fts` | 1 | FTS5 virtual table (auto-synced via INSERT/UPDATE/DELETE triggers) |
| `decisions` | 1 | scope (ALL / project), topic, decision, reason, is_superseded |
| `pending` | 1 | project, task, priority (P1/P2/P3), resolved_at |
| `patterns` | 1 | topic, title, solution, seen_in (projects), seen_count |
| `entities` | 2 | name, type (class/file/library/god_node), mention_count |
| `entity_links` | 2 | entity_id ↔ obs_id many-to-many join |
| `errors` | 2 | error_text, root_cause, fix, recurred, is_resolved |
| `releases` | 3 | project, version_name, version_code, released_at, store |
| `branches` | 3 | project, branch, status (open/merged), pr_number, merged_at |

See [SCHEMA.md](SCHEMA.md) for full column-level documentation.

---

## Configuration

| Environment variable | Default | Purpose |
|---------------------|---------|---------|
| `REPOMEM_DIR` | `~/.repomem` | Override storage location |
| `REPOMEM_INSTALL` | `~/.repomem/lib` | Override package path (used by hooks) |
| `REPOMEM_PROJECT` | auto (git remote) | Override project name detection |
| `REPOMEM_OBSIDIAN_VAULT` | `~/.repomem/exports/obsidian` | Override Obsidian vault export path |
| `REPOMEM_PORT` | `39000` | Web viewer port |

---

## Privacy

| Guarantee | Detail |
|-----------|--------|
| Local only | All data in `~/.repomem/memory.db` — never leaves your machine |
| No network | Zero outbound connections, ever |
| No telemetry | No usage data, no crash reports, nothing |
| No API keys | No OpenAI, Anthropic, or any external service needed |
| Private tags | `<private>…</private>` content stripped before storage |
| Relocatable | `REPOMEM_DIR=/your/path` moves the entire database |

---

## vs. Alternatives

Short summary — see [COMPARISON.md](COMPARISON.md) for 5 detailed comparison tables:

| | [claude-mem](https://github.com/thedotmack/claude-mem) | [Engram](https://github.com/Gentleman-Programming/engram) | [Basic Memory](https://github.com/basicmachines-co/basic-memory) | [mem0](https://github.com/mem0ai/mem0) | **RepoMem** |
|---|:---:|:---:|:---:|:---:|:---:|
| Zero dependencies | ❌ npm | ❌ Go binary | ❌ | ❌ | ✅ stdlib only |
| Zero API keys | ✅ | ✅ | ✅ | ❌ | ✅ |
| One-command install | ✅ | ✅ | ✅ | ❌ | ✅ |
| SessionStart auto-injection | ✅ | ✅ | ✅ | ❌ | ✅ |
| Structured typed observations | Partial | ✅ | ✅ | ❌ | ✅ 8 types |
| Sleep-time reflection | ❌ | ✅ | ❌ | ❌ | ✅ |
| Conflict detection | ❌ | Beta | ❌ | ❌ | ✅ |
| Error tracking | ❌ | ✅ | ❌ | ❌ | ✅ |
| MCP server | ✅ | ✅ | ✅ | ❌ | ✅ |
| Web viewer (local) | ✅ | Cloud only | ✅ | ❌ | ✅ local |
| Terminal UI | Partial | ✅ | ✅ | ❌ | ✅ |
| Obsidian sync | ❌ | Beta | ✅ | ❌ | ✅ |
| Git cross-machine sync | ❌ | ✅ | Partial | ❌ | ✅ |
| DB schema migrations | ❌ | ✅ | ✅ | ❌ | ✅ |
| Fully auditable (no binary) | ❌ | ❌ Go binary | ✅ | ✅ | ✅ |
| License | Apache 2 | MIT | **AGPL** | Apache 2 | **MIT** |

---

## FAQ

**Does it work with agents other than Claude Code?**  
The core tool is AI-agnostic — any agent that can run bash commands can use the CLI. The MCP server works with any MCP-compatible agent (Cursor, Gemini CLI, etc.). The `/repomem` skill and automatic Stop/SessionStart hooks are **Claude Code-specific**. Without Claude Code, use the CLI to add observations manually. See [INSTALL.md](INSTALL.md).

**Does it slow down session start?**  
No. The SessionStart hook has a 10-second timeout and injects ≤2000 characters. In practice it runs in under 1 second on a warm DB.

**What happens if the DB is corrupted or missing?**  
All hooks exit 0 and fail silently — a missing or broken DB never blocks a Claude Code session. Run `repomem doctor` to diagnose and `bash install.sh` to reinitialize.

**How do I stop it capturing something sensitive?**  
Wrap it in `<private>…</private>` in your session text. RepoMem strips that content before writing to the DB. Alternatively, set `REPOMEM_PROJECT=skip` to disable capture for a session entirely.

**Can I use it across multiple machines?**  
Yes. `repomem sync --export` writes a JSON chunk to `~/.repomem/sync/` and commits via git. On another machine, `repomem sync --import` merges peer chunks. A watermark ensures only new observations are exported each run.

**How do I update?**  
```bash
cd ~/path/to/RepoMem && git pull && bash install.sh
```
`install.sh` is idempotent — skips already-wired hooks and MCP entries, and runs DB schema migrations automatically.

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

- [Report a bug](.github/ISSUE_TEMPLATE/bug_report.md)
- [Request a feature](.github/ISSUE_TEMPLATE/feature_request.md)
- [Ask a question](.github/ISSUE_TEMPLATE/question.md)
- [Security vulnerabilities](SECURITY.md) — please report privately

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full history.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

Ideas borrowed from:
- [Basic Memory](https://github.com/basicmachines-co/basic-memory) — sleep-time reflection concept
- [Engram](https://github.com/NilsIrl/engram) — SQLite + FTS5 architecture
- [agentmemory](https://github.com/jayzeng/agentmemory) — injection priority and cap design

See [COMPARISON.md](COMPARISON.md) for a full breakdown of tools studied.
