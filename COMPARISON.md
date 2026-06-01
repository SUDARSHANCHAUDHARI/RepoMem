# RepoMem vs. Alternatives

A detailed breakdown of why RepoMem was built instead of using an existing tool.

---

## Tools evaluated

| Tool | GitHub Stars | Language | Storage engine | Install |
|------|:-----------:|----------|----------------|---------|
| [claude-mem](https://github.com/cnych/claude-mem) | ~79k | TypeScript (compiled) | SQLite + Chroma vector DB | `npm install` |
| [Engram](https://github.com/NilsIrl/engram) | ~4k | Go (pre-compiled binary) | SQLite + FTS5 | download binary |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | ~500 | Python | Markdown flat files | `pip install` |
| [mem0](https://github.com/mem0ai/mem0) | ~57k | Python | Vector DB (cloud-hosted) | `pip install` + API key |
| **RepoMem** | — | Python (stdlib only) | SQLite + FTS5 | `bash install.sh` |

---

## Setup complexity

| Step | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|------|:----------:|:------:|:------------:|:----:|:-------:|
| Install runtime | Node.js | Go or binary | Python | Python | Python 3.11+ |
| Install dependencies | `npm install` | none (binary) | `pip install uv` | `pip install mem0ai` | **none** |
| API key required | ❌ | ❌ | ❌ | ✅ OpenAI key | ❌ |
| Configure MCP | Manual JSON | Manual JSON | ❌ no MCP | ❌ no MCP | Auto via `install.sh` |
| Hook wiring | Manual | Manual | ❌ | ❌ | Auto via `install.sh` |
| Cron jobs | ❌ | ❌ | ❌ | ❌ | Auto via `install.sh` |
| One-command setup | ❌ | ❌ | Partial | ❌ | ✅ `bash install.sh` |

---

## Full feature comparison

### Trust & privacy

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Zero API keys required | ✅ | ✅ | ✅ | ❌ OpenAI | ✅ |
| Zero telemetry | ❓ unknown | ✅ | ✅ | ❌ opt-out only | ✅ |
| Zero external dependencies | ❌ npm + Chroma | ❌ Go binary | ❌ several | ❌ vector DB | ✅ |
| Zero compiled binaries | ❌ | ❌ | ✅ | ✅ | ✅ |
| Fully auditable (read the source) | ❌ build step | Partial | ✅ | ✅ | ✅ |
| Works fully offline / air-gapped | ✅ | ✅ | ✅ | ❌ | ✅ |
| All data stored locally | ✅ | ✅ | ✅ | ❌ cloud | ✅ |
| Private content tagging | ❌ | ❌ | ❌ | ❌ | ✅ `<private>` tag |

### Capture & storage

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Automatic session-end capture (Stop hook) | ✅ | Partial | ❌ manual | ❌ manual | ✅ |
| Automatic session-start injection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Structured typed observations | ❌ flat text | ❌ flat text | ❌ Markdown | ❌ flat text | ✅ 8 types |
| Auto topic tagging | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entity extraction (classes, files, libs) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error / crash auto-detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Release version auto-detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Git branch auto-tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| `<private>` content stripping | ❌ | ❌ | ❌ | ❌ | ✅ |

### Search & retrieval

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Full-text search | ✅ FTS5 | ✅ FTS5 | Partial grep | ✅ vector | ✅ FTS5 |
| Filter by project | ❌ | ❌ | ❌ | ❌ | ✅ |
| Filter by observation type | ❌ | ❌ | ❌ | ❌ | ✅ |
| Recency × confidence ranking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Age labels on old observations | ❌ | ❌ | ❌ | ❌ | ✅ "3mo ago" |
| Search by entity name | ❌ | ❌ | ❌ | ❌ | ✅ |

### Intelligence & automation

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Sleep-time reflection (nightly) | ❌ | ❌ | ✅ | ❌ | ✅ |
| Duplicate / near-duplicate detection | ❌ | ❌ | ❌ | ✅ | ✅ 80% similarity |
| Contradiction / conflict detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cross-project pattern promotion | ❌ | ❌ | ❌ | ❌ | ✅ 3+ projects |
| Temporal decay (confidence over time) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Decision auto-promotion (seen 2+ times) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Weekly memory defrag + vacuum | ❌ | ❌ | ❌ | ❌ | ✅ |

### Interfaces

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| MCP server (mid-session queries) | ✅ | ✅ | ❌ | ❌ | ✅ 7 tools |
| CLI | ✅ | ✅ | ✅ | ✅ | ✅ 17 commands |
| Web viewer (dark mode, no build) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Terminal UI (vim keys) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Obsidian vault export | ❌ | ❌ | ❌ | ❌ | ✅ wikilinks |
| Git cross-machine sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Code graph (Graphify) integration | ❌ | ❌ | ❌ | ❌ | ✅ |

### Scale & maintenance

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Multi-repo / multi-project | ✅ | ✅ | ❌ | ✅ | ✅ |
| Per-project filtering | ❌ | ❌ | ❌ | ❌ | ✅ |
| DB schema auto-migration | ❌ | ❌ | ❌ | ❌ | ✅ v1→v3 |
| DB health check (doctor command) | ❌ | ❌ | ❌ | ❌ | ✅ |
| FTS5 index rebuild | ❌ | ❌ | — | — | ✅ |
| DB vacuum / size control | ❌ | ❌ | — | — | ✅ |

---

## Why not each one

### claude-mem

**Good:** High adoption, MCP server, Stop hook, FTS5 search.  
**Problems:**

- TypeScript requires `npm install` and a build step — not auditable without a toolchain
- Chroma vector DB is a heavyweight dependency for a developer note-taking problem
- No SessionStart injection — memory is only accessible when Claude explicitly queries it
- No background reflection — no dedup, no pattern promotion, no conflict detection
- npm dependency tree brings in dozens of transitive packages with unknown security posture

### Engram

**Good:** SQLite + FTS5 (same as RepoMem), MCP server, Go performance.  
**Problems:**

- Requires a compiled Go binary — trust and auditability concern; you're running someone's binary
- No SessionStart injection — must query memory explicitly
- No sleep-time reflection — memory accumulates but never gets cleaned or promoted
- No project-level scoping — all memories are global
- No web UI, TUI, or Obsidian sync
- No entity linking, error tracking, or release tracking

### Basic Memory

**Good:** Python, local storage, sleep-time reflection (the best idea in this space).  
**Problems:**

- Stores everything as Markdown flat files — no structured schema, no typed observations, no FTS5
- No MCP server — Claude cannot query memory mid-session
- No SessionStart injection — no automatic context
- AGPL license — complicates use in commercial or proprietary projects
- Does not scale well to many projects — no per-project filtering
- **What RepoMem borrows:** the sleep-time reflection concept, implemented as `crons/reflect.py`

### mem0

**Good:** High polish, YC-backed, vector search, 57k stars.  
**Problems:**

- Requires OpenAI (or compatible) API key — no fully local mode
- Telemetry enabled by default — must opt out; unsuitable for sensitive or private codebases
- Cloud-dependent — not suitable for offline, air-gapped, or privacy-first environments
- Vector DB adds significant complexity and cost for a developer memory problem
- Commercial product with pricing risk — feature set and pricing may change
- No Stop/SessionStart hooks for Claude Code specifically

---

## Summary: when to choose RepoMem

| If you… | Choose |
|---------|--------|
| Want zero dependencies, zero config, zero API keys | **RepoMem** |
| Need memory injected automatically at session start | **RepoMem** |
| Work across many repos and want per-project filtering | **RepoMem** |
| Want sleep-time reflection, conflict detection, pattern promotion | **RepoMem** |
| Want a web UI or TUI to browse your memory | **RepoMem** |
| Use Obsidian and want memory synced to your vault | **RepoMem** |
| Need cross-machine memory via git | **RepoMem** |
| Are comfortable with TypeScript and want the largest community | claude-mem |
| Want the simplest possible setup (just a binary) | Engram |
| Want vector similarity search (semantic, not keyword) | mem0 |

---

## What RepoMem uniquely adds

| Feature | Why it matters |
|---------|----------------|
| **SessionStart injection** | Memory arrives at session start automatically — no prompting needed |
| **Structured observation types** | 8 queryable types (bugfix, decision, error…) — not just text blobs |
| **Conflict detection** | Contradicting decisions are flagged and linked — never silently re-litigated |
| **Error tracking** | Crash patterns auto-detected, recurrence counted, fixes surfaced next session |
| **Sleep-time reflection** | Nightly: dedup, pattern promotion, contradiction flagging, confidence decay |
| **Graphify integration** | Knows which files have the most connections in your codebase (God Nodes) |
| **Release tracking** | Warns when no release has been detected in over 90 days |
| **Git sync** | Export/import memory chunks via git for cross-machine continuity |
| **Obsidian sync** | Export project memories as wikilinked Markdown for your vault |
| **Web + TUI interfaces** | Browse, search, and manage memory without touching the CLI |
| **100% stdlib** | `pip install` nothing — Python 3.11+ is the only requirement |
| **Schema migrations** | DB auto-migrates as new tables/columns are added — no manual steps |
| **One-command install** | `bash install.sh` wires hooks, MCP, crons, and health check |
