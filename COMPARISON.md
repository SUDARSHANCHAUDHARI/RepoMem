# RepoMem vs. Alternatives

A detailed breakdown of why RepoMem was built instead of using an existing tool.

---

## The tools evaluated

| Tool | Stars | Language | Storage |
|------|-------|----------|---------|
| [claude-mem](https://github.com/cnych/claude-mem) | ~79k | TypeScript | SQLite + Chroma |
| [Engram](https://github.com/NilsIrl/engram) | ~4k | Go (binary) | SQLite + FTS5 |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | ~500 | Python | Markdown |
| [mem0](https://github.com/mem0ai/mem0) | ~57k | Python | Vector DB |
| **RepoMem** | — | Python | SQLite + FTS5 |

---

## Feature matrix

| Feature | claude-mem | Engram | Basic Memory | mem0 | **RepoMem** |
|---------|-----------|--------|--------------|------|-------------|
| Zero API keys | ✅ | ✅ | ✅ | ❌ (OpenAI) | ✅ |
| Zero telemetry | Unknown | ✅ | ✅ | ❌ (opt-out) | ✅ |
| Zero compiled binaries | ❌ | ❌ | ✅ | ✅ | ✅ |
| Zero external deps | ❌ | ❌ | ❌ | ❌ | ✅ |
| Full-text search | ✅ | ✅ | Partial | ✅ | ✅ |
| MCP server | ✅ | ✅ | ❌ | ❌ | ✅ |
| Stop hook | ✅ | Partial | ❌ | ❌ | ✅ |
| SessionStart injection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Sleep-time reflection | ❌ | ❌ | ✅ | ❌ | ✅ |
| Conflict detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entity linking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Release tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Graphify integration | ❌ | ❌ | ❌ | ❌ | ✅ |
| Obsidian sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Git cross-machine sync | ❌ | ❌ | ❌ | ❌ | ✅ |
| Web viewer | ❌ | ❌ | ❌ | ❌ | ✅ |
| 190+ repo scale | ✅ | ✅ | ❌ | ✅ | ✅ |
| Android-specific | ❌ | ❌ | ❌ | ❌ | ✅ |
| Auditable source | ❌ | Partial | ✅ | ✅ | ✅ |
| License | MIT | MIT | AGPL | Apache 2 | **MIT** |

---

## Why not each one

### claude-mem

Good tool but TypeScript requires compilation, pulls in many npm dependencies, and
the Chroma vector DB is a heavyweight dependency. Not auditable without build tooling.

### Engram

Closest in spirit — SQLite + FTS5 like RepoMem. But requires a compiled Go binary,
which is a trust/auditability concern. No SessionStart injection, no sleep-time reflection.

### Basic Memory

Pure Python but stores everything as Markdown files — no structured schema, no FTS5,
no MCP server. The AGPL license complicates forks. Sleep-time reflection concept
(the best idea from Basic Memory) is adopted in RepoMem's `reflect.py`.

### mem0

57k stars, YC-backed, well-engineered. But requires OpenAI API keys (no local-only mode),
has telemetry on by default, and uses a vector database. Not suitable for offline/air-gapped
dev environments or for users who don't want cloud dependencies.

---

## What RepoMem uniquely adds

1. **SessionStart injection** — memory arrives at session start, not just on demand
2. **Graphify integration** — knows which files are God Nodes in your codebase
3. **Android-specific tracking** — topic keywords for Room, Hilt, Compose, AGP, etc.
4. **Sleep-time reflection** — nightly dedup, pattern promotion, contradiction flagging
5. **Error tracking** — detects crash patterns, tracks recurrence, surfaces fixes
6. **Release tracking** — warns when last Play Store release was >90 days ago
7. **Conflict detection** — flags contradicting decisions and links them
8. **100% stdlib** — no pip install needed beyond Python itself
