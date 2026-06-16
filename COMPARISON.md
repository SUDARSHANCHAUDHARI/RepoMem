# RepoMem vs. Alternatives

A detailed breakdown of why RepoMem was built instead of using an existing tool.

---

## Tools evaluated

> We studied 13 tools and 2 articles before building RepoMem. Full per-tool analysis below.
> Star counts verified June 2026 — numbers change over time.

| Tool | Stars | Language | Storage | API Key | License |
|------|------:|----------|---------|:-------:|---------|
| [claude-mem](https://github.com/thedotmack/claude-mem) | ~80k | TypeScript (compiled .cjs) | SQLite + Chroma | No | Apache 2 |
| [Engram](https://github.com/Gentleman-Programming/engram) | ~4k | Go (pre-compiled binary) | SQLite + FTS5 | No | MIT |
| [agentmemory](https://github.com/jayzeng/agentmemory) | ~5 | TypeScript | Markdown flat files + optional qmd | No* | MIT |
| [mem0](https://github.com/mem0ai/mem0) | ~57k | Python + TypeScript | Vector DB (Qdrant default) | **Yes** (LLM key) | Apache 2 |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | ~3k | Python | Markdown + SQLite | No | **AGPL** |
| [basic-memory-skills](https://github.com/basicmachines-co/basic-memory-skills) | ~20 | Markdown skills | Needs Basic Memory | No | MIT |
| [Letta / MemGPT](https://github.com/letta-ai/letta) | ~23k | Python | Tiered (RAM+disk) | Optional | Apache 2 |
| [Cognee](https://github.com/topoteretes/cognee) | ~18k | Python | Knowledge graph + vector | Optional | Apache 2 |
| [Zep](https://github.com/getzep/zep) | ~5k | Go + Python SDKs | Cloud (CE deprecated) | **Yes** | Apache 2 |
| [LangChain Memory](https://github.com/langchain-ai/langchain) | ~138k | Python | Flexible (pluggable) | Optional | MIT |
| [LlamaIndex Memory](https://github.com/run-llama/llama_index) | ~50k | Python/TS | Vector store | Optional | MIT |
| MindStudio / Milvus | — | Python | Milvus + SQLite | **Yes** (Voyage AI) | — |
| [claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup) | ~0 | Python + Bash | Obsidian vault (flat files) | No | MIT |
| [memanto](https://github.com/moorcheh-ai/memanto) | new | Python | Moorcheh engine (Docker/cloud) | No (local) / **Yes** (cloud) | MIT |
| **RepoMem** | — | **Python (stdlib only)** | **SQLite + FTS5** | **No** | **MIT** |

*agentmemory keyword search works without API key; semantic search requires an embedding API key.

---

## Setup complexity

| Step | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|------|:----------:|:------:|:------------:|:----:|:-------:|
| Install runtime | Node.js | Go or binary | Python | Python | Python 3.11+ |
| Install dependencies | `npm install` | none (binary) | `pip install uv` | `pip install mem0ai` | **none** |
| API key required | ❌ | ❌ | ❌ | ✅ OpenAI key | ❌ |
| Configure MCP | Auto | Auto | Auto | ❌ no MCP | Auto via `install.sh` |
| Hook wiring | Auto | Auto | Auto | ❌ | Auto via `install.sh` |
| Cron jobs | ❌ | ❌ | ❌ | ❌ | Auto via `install.sh` |
| One-command setup | ✅ `npx claude-mem install` | ✅ `brew install` | ✅ `uv tool install` | ❌ | ✅ `bash install.sh` |

---

## Full feature comparison

### Trust & privacy

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Zero API keys required | ✅ | ✅ | ✅ | ❌ OpenAI | ✅ |
| Zero telemetry | ❓ unknown | ✅ | ✅ | ❌ opt-out only | ✅ |
| Zero external dependencies | ❌ npm + Chroma | ❌ Go binary | ❌ several | ❌ vector DB | ✅ |
| Zero compiled binaries | ❌ | ❌ Go binary | ✅ | ✅ | ✅ |
| Fully auditable (read the source) | ❌ build step | ❌ Go binary | ✅ | ✅ | ✅ |
| Works fully offline / air-gapped | ✅ | ✅ | ✅ | ❌ | ✅ |
| All data stored locally | ✅ | ✅ | ✅ | ❌ cloud | ✅ |
| Private content tagging | ❌ | ❌ | ❌ | ❌ | ✅ `<private>` tag |

### Capture & storage

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Automatic session-end capture (Stop hook) | ✅ | ✅ | ❌ | ❌ manual | ✅ |
| Automatic session-start injection | ✅ | ✅ | ❌ | ❌ | ✅ |
| Structured typed observations | Partial | ✅ typed | ✅ categorical | ❌ flat text | ✅ 8 types |
| Auto topic tagging | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entity extraction (classes, files, libs) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error / crash auto-detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Release version auto-detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Git branch auto-tracking | ❌ | ❌ | ❌ | ❌ | ✅ |
| `<private>` content stripping | ✅ | ❌ | ❌ | ❌ | ✅ |

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
| Sleep-time reflection (nightly) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Duplicate / near-duplicate detection | ❌ | ❌ | ❌ | ✅ | ✅ 80% similarity |
| Contradiction / conflict detection | ❌ | Beta (needs LLM call) | ❌ | ❌ | ✅ autonomous |
| Cross-project pattern promotion | ❌ | ❌ | ❌ | ❌ | ✅ 3+ projects |
| Temporal decay (confidence over time) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Decision auto-promotion (seen 2+ times) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Weekly memory defrag + vacuum | ❌ | ❌ | ❌ | ❌ | ✅ |

### Interfaces

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| MCP server (mid-session queries) | ✅ 4 tools | ✅ 19 tools | ✅ | ❌ | ✅ 8 tools |
| CLI | ✅ | ✅ | ✅ | ✅ | ✅ 22 commands |
| Web viewer (local, no signup) | ✅ local | ❌ cloud only | ❌ cloud only | ❌ | ✅ local |
| Terminal UI (vim keys) | ❌ | ✅ | Partial | ❌ | ✅ |
| Obsidian vault export | ❌ | Beta | ✅ | ❌ | ✅ vault-aware wikilinks, dynamic tags, patterns/releases/branches |
| Git cross-machine sync | ❌ | ✅ | Manual | ❌ | ✅ |
| Code graph (Graphify) integration | ❌ | ❌ | ❌ | ❌ | ✅ |

### Scale & maintenance

| Feature | claude-mem | Engram | Basic Memory | mem0 | RepoMem |
|---------|:---------:|:------:|:------------:|:----:|:-------:|
| Multi-repo / multi-project | ✅ | ✅ | ✅ | ❌ | ✅ |
| Per-project filtering | ✅ | ✅ | ✅ | ❌ | ✅ |
| DB schema auto-migration | ❌ | ❌ confirmed | ✅ Alembic | ❌ | ✅ v1→v3 |
| DB health check (doctor command) | ❌ | ❌ | ❌ | ❌ | ✅ |
| FTS5 index rebuild | ❌ | ❌ | — | — | ✅ |
| DB vacuum / size control | ❌ | ❌ | — | — | ✅ |

---

## Why not each one

### claude-code-memory-setup

**Good:** Excellent Zettelkasten methodology guide. The vault-aware wikilink strategy (scan real notes, code-block-safe, first-occurrence-only, longest-match-first) is genuinely better than naive PascalCase linking. `SHORT_KEYWORDS` word-boundary fix for topic detection is a real bug catch. The `import-chat` pipeline concept (import historical exported sessions) fills a gap no other tool addresses. RepoMem borrowed all four of these ideas directly.  
**Problems:**

- Not a system — a guide + one 280-line Python script. No automation, no hooks, no database, no injection
- Manual `/save` and `/resume` commands required every session — zero automation
- No database: memory is flat Markdown files, no FTS search, no relational queries
- Requires external dependencies: `claude-conversation-extractor`, browser extension for Web chats
- No background reflection, no dedup, no pattern promotion, no conflict detection, no temporal decay
- No error tracking, no release tracking, no entity linking

**What RepoMem took:** vault-aware wikilink strategy, `SHORT_KEYWORDS` word-boundary matching, `import-chat` concept, dynamic Obsidian frontmatter tags with `type/status/source/processed` fields.

### claude-mem

**Good:** Massive adoption (~80k stars), MCP server, Stop hook, SessionStart injection, web viewer, one-command install (`npx claude-mem install`).  
**Problems:**

- TypeScript compiled to `.cjs` — requires Node.js and npm; not auditable without a build toolchain
- Chroma vector DB is a heavyweight dependency for a developer note-taking problem
- npm dependency tree brings in dozens of transitive packages with unknown security posture
- No background reflection — no dedup, no pattern promotion, no conflict detection
- License is Apache 2.0 (not MIT) — fewer reuse permissions
- No per-project filtering — all memories are global

### Engram

**Good:** SQLite + FTS5, 19 MCP tools, Stop + SessionStart hooks, structured typed observations, TUI, git sync, one-command install (`brew install`). Closest competitor to RepoMem feature-for-feature.
**Problems:**

- Requires a compiled Go binary — trust and auditability concern; you're running someone else's binary, not readable source
- No sleep-time reflection — memory accumulates but is never cleaned, deduplicated, or promoted autonomously
- Web viewer is cloud-only (Engram Cloud, opt-in) — no local web dashboard
- Conflict detection is beta and requires an external LLM call (Claude Code / OpenCode CLI) — not autonomous
- No entity linking, release tracking, cross-project pattern promotion
- No `<private>` content stripping
- Obsidian sync is beta
- No per-project DB schema auto-migrations confirmed

### Basic Memory

**Good:** Python, local storage, MCP server, per-project filtering, Obsidian sync, DB migrations (Alembic), one-command install.
**Problems:**

- No Stop hook — session-end capture is manual, not automatic
- No SessionStart injection — Claude does not receive memory automatically at session start
- No sleep-time reflection — no nightly dedup, conflict detection, or pattern promotion
- AGPL license — complicates use in commercial or proprietary projects
- Web viewer is cloud-only (basicmemory.com) — requires account for the UI
- No `<private>` content stripping, no error tracking, no entity linking
- Markdown flat files for storage — no FTS5, no typed observation schema, no confidence ranking
- **What RepoMem borrows:** Alembic-style schema migrations concept, per-project filtering

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

---

## Additional tools studied (deeper research)

The tools above were evaluated first. We then studied 5 more tools and 2 articles before finalising the RepoMem design. Each contributed specific ideas.

---

### agentmemory — [jayzeng/agentmemory](https://github.com/jayzeng/agentmemory)

**Stars:** 5 · **Language:** TypeScript · **License:** MIT · **Storage:** Markdown flat files + qmd optional

**What it does:**
Pure markdown memory system. Three-layer file structure:
```
~/.agent-memory/
  MEMORY.md           ← curated long-term facts
  SCRATCHPAD.md       ← active checklist (highest priority)
  daily/YYYY-MM-DD.md ← append-only daily log
  topics/<name>.md    ← per-topic cross-session notes
```

Context injection priority (before every turn):
1. Open scratchpad items (2K chars)
2. Recent topic entries (2K chars)
3. Today's daily log (3K chars)
4. qmd semantic search on user's prompt (2.5K chars)
5. MEMORY.md (4K chars)
6. Yesterday's daily log (3K chars)
Total cap: 16K chars

**Brilliant ideas we borrowed:**
- **Scratchpad as highest-priority context** → `pending` table, injected first
- **Topic files** → per-topic observation filtering via `topic` column
- **Hard injection cap** → our 2000-char cap in `inject.py`
- **Graceful degradation** → if search fails, injection still works
- **`!agent-memory context`** pattern → single command builds full context string

**Why we didn't use it:**
- No per-project isolation — one `~/.agent-memory/` for everything
- Breaks badly at 10+ repos — daily files from unrelated projects pollute context
- No structured schema — can't query "all bugfixes in project X"
- Semantic search requires qmd + external embedding API (we need zero API keys)
- TypeScript compiled to binary — not fully auditable

---

### Letta (formerly MemGPT)

**Stars:** ~23k · **Language:** Python · **License:** Apache 2.0 · **Self-hosted:** Yes

**What it does:**
OS-inspired tiered memory architecture mimicking how an operating system manages RAM vs disk:

```
Tier 1 — Main context (RAM):   what the agent is actively working on
Tier 2 — External storage (disk): everything else, retrieved on demand
```

Agents call functions explicitly to read/write/archive memory. No passive capture — **intentional writes only**. This gives agents agency over their own memory.

**Key innovations:**
- Sleep-time compute — agents process memories during idle time (inspired Basic Memory's reflection)
- Context window management via intelligent swapping between tiers
- Enables effectively unlimited memory despite fixed context constraints

**Ideas we borrowed:**
- **Tiered priority injection** → decisions always injected (like RAM), old observations retrieved on demand (like disk)
- **Intentional writes concept** → `repomem add` for manual saves during session
- **Sleep-time compute** → our `crons/reflect.py` nightly reflection

**Why we didn't use it:**
- Designed for building long-running AI agents, not for personal developer tooling
- Higher learning curve — unique architecture requires significant setup
- Less mature ecosystem for Claude Code specifically

---

### Cognee

**Stars:** ~18k · **Language:** Python · **License:** Apache 2.0 · **Self-hosted:** Yes

**What it does:**
Builds a knowledge graph from unstructured data — documents, conversations, code. Agents reason over relationships, not just text blobs.

```
Input: conversations + docs + code
  → entity extraction
  → relationship mapping
  → knowledge graph
  → graph traversal + vector search combined
```

**Key innovation:** Graph traversal reveals connections that keyword or vector search misses. "What is related to UserRepository?" finds all files, decisions, and bugs connected through the graph — not just documents mentioning the word.

**Ideas we borrowed:**
- **Knowledge graph integration** → Phase 4: `repomem graphify` reads `graphify-out/graph.json`
- **Entity relationship mapping** → Phase 2: `entity_links` table connecting observations to entities
- **Structural context enrichment** → session start shows God Nodes (high-connectivity files) near current work

**Why we didn't use it:**
- Graph complexity adds significant infrastructure overhead
- Vector search requires embedding model or API
- More suited for knowledge-intensive enterprise workflows than personal developer memory

---

### Zep

**Source:** [ML Mastery article — 6 Best AI Agent Memory Frameworks](https://machinelearningmastery.com/the-6-best-ai-agent-memory-frameworks-you-should-try-in-2026/)  
**Type:** Cloud-first platform (Community Edition deprecated) · **License:** Apache 2.0 · **Stars:** ~5k

**What it does:**
Context engineering platform with sub-200ms retrieval. Uses Graphiti (open-source temporal knowledge graph) to build relationship-aware context that understands how information evolves over time. Supports chat history, business data, documents, and events.

```
Conversation → entity extraction → intent detection → structured facts
Temporal knowledge graph: understands how information changes over time
Temporal search: "what was the state of X last Tuesday?"
```

**Unique feature:** Temporal knowledge graph via Graphiti is genuinely impressive — relationship-aware retrieval that understands the evolution of information, not just recency.

**Ideas we borrowed:**
- **Temporal reasoning** → our `inject.py` ranks observations by `recency × confidence`, labels old observations with age ("3mo ago")
- **Progressive summarisation** → `reflect.py` deduplicates and promotes high-confidence observations

**Why we didn't use it:**
- Cloud-first — Community Edition has been deprecated; self-hosted path is unclear
- Requires API key / account for meaningful use
- Designed for production AI applications, not personal developer tooling
- Pricing risk for a personal productivity tool

---

### LangChain Memory

**Source:** [ML Mastery article — 6 Best AI Agent Memory Frameworks](https://machinelearningmastery.com/the-6-best-ai-agent-memory-frameworks-you-should-try-in-2026/)  
**Language:** Python · **License:** MIT · **Self-hosted:** Yes

**What it does:**
Modular memory types — conversation buffer, summary, entity memory, knowledge graph. Flexible backends: in-memory, vector databases, traditional databases.

**Strength:** Highly composable. Mix and match memory types for your exact use case.

**Why we didn't use it:**
- Requires LangChain ecosystem — significant dependency weight
- Designed for building AI applications, not for personal developer tooling
- No Claude Code hooks or session-level memory injection
- Developer must configure and manage storage infrastructure manually

---

### LlamaIndex Memory

**Source:** [ML Mastery article — 6 Best AI Agent Memory Frameworks](https://machinelearningmastery.com/the-6-best-ai-agent-memory-frameworks-you-should-try-in-2026/)  
**Language:** Python/TypeScript · **License:** MIT · **Self-hosted:** Yes

**What it does:**
Combines chat history with document context. Excellent for knowledge-intensive agents that need to reason over large document collections alongside conversation history.

**Strength:** Best in class for document-heavy workflows. Composable query engines.

**Why we didn't use it:**
- Designed for document RAG pipelines, not session-level developer memory
- Steeper learning curve — query engine configuration required
- No Claude Code hooks

---

### basic-memory-skills — [basicmachines-co/basic-memory-skills](https://github.com/basicmachines-co/basic-memory-skills)

**Stars:** 20 · **Language:** Markdown skills only · **License:** MIT

This is the **skills companion** to the Basic Memory MCP server. It provides 10 skills that teach AI agents HOW to use Basic Memory effectively.

| Skill | Purpose |
|-------|---------|
| `memory-reflect` | Sleep-time reflection — reviews recent sessions, consolidates insights |
| `memory-defrag` | Weekly cleanup — splits bloated files, merges duplicates, removes stale |
| `memory-tasks` | Task tracking that survives context compaction |
| `memory-lifecycle` | Archive-never-delete — folder-based status transitions |
| `memory-schema` | Schema validation — consistency across note types |
| `memory-ingest` | Parse meeting transcripts and pasted documents into structured notes |
| `memory-notes` | How to write good notes — frontmatter, wikilinks, observations |
| `memory-metadata-search` | Query notes by frontmatter fields |
| `memory-research` | Web research → structured entity notes |
| `memory-literary-analysis` | Full literary work → knowledge graph |

**Key principles we borrowed:**
- **Archive, never delete** → `is_archived` flag in observations, never hard-delete
- **Wikilinks between observations** → `related_ids` column + entity_links table
- **Schema validation** → Contributing guide requires schema docs for new tables
- **Memory ingest** → our `capture.py` processes session text similarly to `memory-ingest`

**Why we didn't use it:**
- Requires Basic Memory MCP server (AGPL-3.0) as backend
- AGPL licence on the server complicates use in proprietary or commercial contexts

---

### MindStudio / Milvus approach

**Source:** [MindStudio article — AI Agent Persistent Memory with Claude + Milvus](https://www.mindstudio.ai/blog/ai-agent-persistent-memory-claude-milvus)

This article describes building a 3-layer memory stack from scratch using Milvus (vector DB) + Voyage AI embeddings + SQLite:

```
Layer 1 — Short-term:  Claude context window (active session)
Layer 2 — Semantic:    Milvus vector DB (similarity search over all history)
Layer 3 — Episodic:    SQLite (structured conversation logs)
```

At query time: **parallel retrieval** from semantic + episodic, merged into context.

**Key implementation insights:**
- **Chunking overlap:** 10-20% overlap at chunk boundaries — without it, context at seams is lost
- **Similarity threshold:** Filter results below 0.65–0.75 cosine similarity — weak matches pollute context
- **Quality over quantity:** 5 high-quality chunks beat 20 mixed ones
- **Same embedding model:** Ingestion and query MUST use the same model — mismatch = wrong results
- **Always log to episodic:** Without conversation logs, follow-up questions break

**Ideas we borrowed:**
- **Quality over quantity** → our injection cap (2000 chars) + confidence-ranked results
- **Similarity threshold** → `reflect.py` only merges observations at >80% similarity
- **Episodic logging** → `sessions` table records every session

**Why we didn't use this approach:**
- Requires Voyage AI API key for embeddings (we need zero API keys)
- Milvus is a heavyweight vector DB — significant infrastructure
- Python build complexity (pdfplumber, LangChain text splitters)
- FTS5 keyword search covers 90% of real-world developer memory queries without any external deps

---

## Complete tools evaluated matrix

| Tool | Stars | Studied | Borrowed | Used |
|------|------:|---------|---------|------|
| [claude-mem](https://github.com/thedotmack/claude-mem) | ~80k | ✅ Deep | `<private>` tags, progressive disclosure, web viewer | ❌ compiled binary, Apache 2 license |
| [Engram](https://github.com/Gentleman-Programming/engram) | ~4k | ✅ Deep | FTS5, session lifecycle, sleep-time reflection, TUI, git sync | ❌ Go binary (not auditable) |
| [agentmemory](https://github.com/jayzeng/agentmemory) | 5 | ✅ Deep | Scratchpad, topic files, injection cap, graceful degradation | ❌ no per-project |
| [mem0](https://github.com/mem0ai/mem0) | 57k | ✅ Deep | Entity linking, temporal reasoning, ADD-only | ❌ API key + telemetry |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) | 3k | ✅ Deep | Sleep-time reflection, defrag, archive-never-delete | ❌ AGPL |
| [basic-memory-skills](https://github.com/basicmachines-co/basic-memory-skills) | 20 | ✅ Deep | Skill design patterns, wikilinks, schema validation | ❌ needs Basic Memory |
| Letta / MemGPT | ~23k | ✅ Article | Tiered memory (RAM/disk), intentional writes | ❌ agent framework |
| Cognee | ~18k | ✅ Deep | Knowledge graph integration concept | ❌ vector search needed |
| Zep | ~5k | ✅ Deep | Temporal reasoning, progressive summarisation | ❌ CE deprecated, cloud-first |
| LangChain Memory | ~138k | ✅ Article | Modular design concept | ❌ heavy ecosystem |
| LlamaIndex Memory | ~50k | ✅ Article | Document-aware context | ❌ wrong use case |
| MindStudio/Milvus | — | ✅ Article | Chunk quality, similarity thresholds | ❌ needs Voyage AI |
