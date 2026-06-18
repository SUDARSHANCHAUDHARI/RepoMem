---
name: repomem
description: RepoMem memory interface — save, search, pending tasks, decisions, sync, web UI. Triggers on "save this", "did we fix this before?", "what's pending?", "show memory", "sync memory".
tools: Bash
---

# RepoMem

One skill for all memory operations. Detect intent from the user's request and run the right command.

---

## Intent routing

| User says | Action |
|-----------|--------|
| "save this", "remember this", "add to memory" | `repomem add` |
| "did we fix this?", "how did we solve X?", "search memory" | `repomem search` |
| "why did we…", "what's the decision on…", "answer from memory" | `repomem answer` |
| "what's pending?", "open tasks", "todo" | `repomem pending` |
| "add pending", "add task", "remember to do" | `repomem add-pending` |
| "what decisions?", "architecture decisions" | `repomem decisions` |
| "add decision", "we decided to" | `repomem add-decision` |
| "show memory", "project context", "what do you know" | `repomem status` + inject context |
| "health check", "is memory working?" | `repomem doctor` |
| "open web UI", "show dashboard", "open browser" | `repomem server` |
| "sync memory", "export memory" | `repomem sync --export` |
| "export to obsidian" | `repomem obsidian` |
| "show entities", "what classes are tracked?" | `repomem entities` |
| "show releases" | `repomem releases` |
| bare `/repomem` with no context | show status + recent observations |

---

## Commands reference

```bash
# Search
repomem search "<query>"
repomem search "<query>" --project <name>
repomem search "<query>" --type bugfix|decision|upgrade|warning|learning|error|pending
repomem search "<query>" --semantic   # embedding search; needs `pip install repomem[semantic]`

# Answer a question (grounded, #id-cited block — no LLM call)
repomem answer "<question>" [--project <name>] [--limit 8]

# Save observation
repomem add --type <type> --summary "<text>" [--detail "<detail>"] [--topic <topic>]

# Pending tasks
repomem pending [--project <name>]
repomem add-pending "<task>" [--project <name>] [--priority P1|P2|P3]
repomem resolve <id>

# Decisions
repomem decisions [--project <name>]
repomem add-decision --decision "<text>" --topic <topic> [--scope ALL|<project>] [--reason "<text>"]

# Status & health
repomem status [--project <name>]
repomem doctor

# Interfaces
repomem server [--port 39000]   # web UI
repomem tui                      # terminal UI

# Sync & export
repomem sync --export [--no-commit]
repomem sync --import
repomem obsidian [--project <name>]

# Entities
repomem entities [--project <name>] [--name <entity>]
```

---

## Observation types

| Type | Use when |
|------|----------|
| `bugfix` | Fixed a bug |
| `decision` | Made an architectural choice |
| `upgrade` | Changed a version or dependency |
| `warning` | Something to avoid |
| `learning` | New knowledge |
| `pending` | Task for next session |
| `pattern` | Reusable solution |
| `error` | Crash or exception |

---

## Examples

**Save a bugfix mid-session:**
```bash
repomem add \
  --type bugfix \
  --summary "Fixed null pointer in AuthService when token is expired" \
  --detail "Added null check before token validation" \
  --topic auth
```

**Save a decision:**
```bash
repomem add-decision \
  --decision "Use JWT for all authentication" \
  --topic auth \
  --scope ALL \
  --reason "Stateless, works across services"
```

**Add a pending task:**
```bash
repomem add-pending "Write integration tests for payment flow" \
  --priority P1
```

**Search across all projects:**
```bash
repomem search "authentication"
repomem search "crash" --type bugfix
```

**Show what Claude knows about current project:**
```bash
repomem status
repomem search "" --project $(git remote get-url origin 2>/dev/null | sed 's/.*\///' | sed 's/\.git//')
```

**Open web dashboard:**
```bash
repomem server
# Then open: http://localhost:39000
```

---

## Rules

- Always confirm what was saved after `repomem add` / `repomem add-pending` / `repomem add-decision`
- If user says "save this" mid-session, infer the type from context (fixing bug → bugfix, making a choice → decision, etc.)
- If `repomem` is not on PATH, use: `PYTHONPATH=~/.repomem/lib python3 -m repomem <command>`
- Never make up observations — only save what was actually done/decided in the session
- Private content: remind user to wrap sensitive info in `<private>...</private>`
