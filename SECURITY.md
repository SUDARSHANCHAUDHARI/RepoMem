# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| Latest (`main`) | ✅ |
| Older commits | ❌ |

RepoMem does not have versioned releases yet. Always use the latest commit on `main`.

---

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security issue, report it privately:

1. Go to the [Security tab](../../security) on GitHub
2. Click **"Report a vulnerability"**
3. Provide a clear description, steps to reproduce, and potential impact

We will acknowledge your report within 48 hours and aim to release a fix within 7 days for confirmed vulnerabilities.

---

## Security design

RepoMem is designed with security in mind:

- **Local only** — all data stays in `~/.repomem/memory.db`, never transmitted anywhere
- **No network calls** — zero outbound connections, ever
- **No telemetry** — no usage data, crash reports, or analytics
- **No API keys** — no external services required
- **Private tag stripping** — content wrapped in `<private>…</private>` is stripped before storage
- **Zero dependencies** — only Python stdlib, no third-party packages with their own attack surface
- **SQLite WAL mode** — safe for concurrent access, no data corruption on crash

---

## Scope

In scope for security reports:

- SQL injection or data corruption in `repomem/db.py`
- Arbitrary code execution via MCP server (`server/mcp_server.py`)
- Hook escape — hooks blocking or crashing Claude Code sessions
- Private tag bypass — `<private>` content leaking into storage

Out of scope:

- Issues in tools that RepoMem integrates with (Claude Code, Obsidian, Graphify)
- Attacks requiring physical access to the machine
- Theoretical vulnerabilities without a practical exploit path
