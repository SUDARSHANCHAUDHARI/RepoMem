# RepoMem vs. Alternatives

A detailed breakdown of why RepoMem was built instead of using an existing tool.

---

## Tools evaluated

| Tool | Stars | Language | Storage | License |
|------|-------|----------|---------|---------|
| [claude-mem](https://github.com/cnych/claude-mem) | ~79k | TypeScript (compiled) | SQLite + Chroma vector DB | MIT |
| [Engram](https://github.com/NilsIrl/engram) | ~4k | Go (binary) | SQLite + FTS5 | MIT |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | ~500 | Python | Markdown files | AGPL |
| [mem0](https://github.com/mem0ai/mem0) | ~57k | Python | Vector DB (cloud) | Apache 2 |
| **RepoMem** | — | Python (stdlib only) | SQLite + FTS5 | **MIT** |

---

## Full feature comparison

### Core

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Zero API keys required | ✅ | ✅ | ✅ | ❌ OpenAI | ✅ |
| Zero telemetry | ❓ unknown | ✅ | ✅ | ❌ opt-out | ✅ |
| Zero external dependencies | ❌ | ❌ | ❌ | ❌ | ✅ |
| Zero compiled binaries | ❌ | ❌ | ✅ | ✅ | ✅ |
| Fully auditable source | ❌ | Partial | ✅ | ✅ | ✅ |
| Works offline / air-gapped | ✅ | ✅ | ✅ | ❌ | ✅ |
| Local-only storage | ✅ | ✅ | ✅ | ❌ | ✅ |

### Capture & search

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Stop hook (session end capture) | ✅ | Partial | ❌ | ❌ | ✅ |
| SessionStart injection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Full-text search (FTS5) | ✅ | ✅ | Partial | ✅ | ✅ |
| Structured observation types | ❌ | ❌ | ❌ | ❌ | ✅ |
| Auto topic detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entity linking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error / crash detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Release tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Branch tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Private tag stripping | ❌ | ❌ | ❌ | ❌ | ✅ |

### Intelligence

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Sleep-time reflection | ❌ | ❌ | ✅ | ❌ | ✅ |
| Duplicate detection | ❌ | ❌ | ❌ | ✅ | ✅ |
| Conflict / contradiction detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pattern promotion (cross-project) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Temporal decay / confidence scoring | ❌ | ❌ | ❌ | ❌ | ✅ |
| Recency × confidence ranking | ❌ | ❌ | ❌ | ❌ | ✅ |

### Interfaces

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| MCP server | ✅ | ✅ | ❌ | ❌ | ✅ |
| CLI | ✅ | ✅ | ✅ | ✅ | ✅ |
| Web viewer | ❌ | ❌ | ❌ | ❌ | ✅ |
| Terminal UI (TUI) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Obsidian sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Git cross-machine sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Graphify code graph integration | ❌ | ❌ | ❌ | ❌ | ✅ |

### Scale & maintenance

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Multi-repo / multi-project | ✅ | ✅ | ❌ | ✅ | ✅ |
| Weekly defrag / vacuum | ❌ | ❌ | ❌ | ❌ | ✅ |
| DB schema migrations | ❌ | ❌ | ❌ | ❌ | ✅ |
| DB health diagnostics (doctor) | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Why not each one

### claude-mem

- **Language barrier** — TypeScript requires `npm install` + compilation step; not auditable without a build toolchain
- **Heavy storage** — uses Chroma vector DB alongside SQLite; significant dependency footprint
- **No session injection** — memory is available on demand via MCP but not injected at session start automatically
- **No reflection** — no background process to dedup, promote patterns, or flag contradictions

### Engram

The closest alternative in spirit — also uses SQLite + FTS5. Main gaps:

- **Binary distribution** — requires a compiled Go binary, which is a trust and auditability concern
- **No SessionStart injection** — memory must be queried explicitly, not injected automatically
- **No sleep-time reflection** — no nightly dedup, pattern promotion, or conflict flagging
- **No web/TUI interface** — CLI only
- **No project-level tracking** — treats all memories as a global flat store

### Basic Memory

- **No structured schema** — stores everything as Markdown files; no typed observations, no FTS5 index
- **No MCP server** — cannot be queried mid-session by Claude
- **No SessionStart injection** — no automatic context at session start
- **AGPL license** — complicates forks and commercial use
- **Best idea adopted** — sleep-time reflection concept from Basic Memory is implemented in RepoMem's `reflect.py`

### mem0

- **Requires API keys** — no local-only mode; OpenAI (or similar) required for embeddings
- **Telemetry on by default** — must actively opt out; not suitable for sensitive codebases
- **Cloud dependency** — not suitable for offline or air-gapped environments
- **Vector DB overhead** — adds significant complexity for what is fundamentally a developer note-taking problem
- **YC-backed / commercial trajectory** — pricing model may change

---

## What RepoMem uniquely adds

| Feature | Why it matters |
|---------|----------------|
| **SessionStart injection** | Memory arrives automatically at session start — no prompting needed |
| **Structured observation types** | `bugfix`, `decision`, `upgrade`, `warning`, `error` etc. — queryable, not just text blobs |
| **Conflict detection** | Contradicting decisions are flagged and linked — never re-litigate silently |
| **Error tracking** | Crash patterns auto-detected, recurrence counted, fixes surfaced at next session |
| **Sleep-time reflection** | Nightly: dedup, pattern promotion, contradiction flagging, confidence decay |
| **Graphify integration** | Knows which files in your codebase have the most connections (God Nodes) |
| **Release tracking** | Warns when no release has been made in over 90 days |
| **Git sync** | Export/import memory chunks via git for cross-machine continuity |
| **Obsidian sync** | Export all project memories as interlinked Markdown for your vault |
| **Web + TUI interfaces** | Browse, search, and manage memory without touching the CLI |
| **100% stdlib** | `pip install` nothing — Python 3.11+ is all you need |
| **Schema migrations** | DB auto-migrates as RepoMem adds new tables/columns — no manual steps |
