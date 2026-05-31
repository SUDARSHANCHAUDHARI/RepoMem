---
name: repomem-recall
description: Search RepoMem persistent memory database. Use when asked "did we fix this before?", "how did we solve X?", "what happened in DreamWeave last week?", or any question about past sessions across any project.
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
python3 -m repomem search "HomeViewModel crash"

# Search in specific project
python3 -m repomem search "Room migration" --project DreamWeave

# Search by type
python3 -m repomem search "AGP" --type upgrade

# Show pending tasks
python3 -m repomem pending
python3 -m repomem pending --project DreamWeave

# Show decisions
python3 -m repomem decisions

# Show stats
python3 -m repomem status
python3 -m repomem status --project DreamWeave

# Health check
python3 -m repomem doctor
```

## Saving during session

If you discover something important mid-session, save it immediately:

```bash
# Save a bugfix
python3 -m repomem add --type bugfix --summary "Fixed null pointer in HomeViewModel" --topic viewmodel

# Save a decision
python3 -m repomem add --type decision --summary "Use KSP over KAPT — KAPT deprecated in Kotlin 2.x" --topic build

# Add a pending task
python3 -m repomem add-pending "Add Room migration to v4" --project DreamWeave --priority P1
```

## REPOMEM_DIR

Default: `~/.repomem/memory.db`
Override: `export REPOMEM_DIR=/custom/path`
