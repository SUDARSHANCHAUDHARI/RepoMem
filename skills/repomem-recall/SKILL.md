---
name: repomem-recall
description: Search RepoMem persistent memory database. Use when asked "did we fix this before?", "how did we solve X?", "what happened in this project last week?", or any question about past sessions across any project.
tools: Bash
---

# RepoMem Recall

Search persistent memory across all projects and sessions.

## When to use

- "Did we already fix this?"
- "How did we solve X last time?"
- "What's the current status of Y?"
- "What happened in [project] recently?"
- "What decisions did we make about Z?"
- "Any pending tasks for [project]?"

## Commands

```bash
# Search by keyword
repomem search "null pointer crash"

# Search in specific project
repomem search "database migration" --project my-app

# Search by type
repomem search "dependency upgrade" --type upgrade

# Show pending tasks
repomem pending
repomem pending --project my-app

# Show decisions
repomem decisions

# Show stats
repomem status
repomem status --project my-app

# Health check
repomem doctor
```

## Saving during session

If you discover something important mid-session, save it immediately:

```bash
# Save a bugfix
repomem add --type bugfix --summary "Fixed null pointer in UserRepository" --topic networking

# Save a decision
repomem add --type decision --summary "Use dependency injection over manual wiring" --topic build

# Add a pending task
repomem add-pending "Write integration tests" --project my-app --priority P1
```

## REPOMEM_DIR

Default: `~/.repomem/memory.db`
Override: `export REPOMEM_DIR=/custom/path`
