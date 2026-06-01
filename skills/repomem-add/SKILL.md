---
name: repomem-add
description: Save an observation to RepoMem persistent memory. Use when fixing a bug, making an architectural decision, discovering a pattern, or identifying a pending task that should be remembered across sessions.
tools: Bash
---

# RepoMem Add

Save observations to persistent memory during or after a session.

## Observation types

| Type | When to use |
|---|---|
| `bugfix` | Fixed a bug — save what was broken + how fixed |
| `decision` | Made an architectural choice |
| `upgrade` | Changed a version or dependency |
| `warning` | Something to watch out for |
| `learning` | New knowledge gained |
| `pending` | Task to do in a future session |
| `pattern` | Reusable solution found |
| `error` | Crash/exception with root cause |

## Usage

```bash
# Bug fix
repomem add \
  --type bugfix \
  --summary "Fixed null pointer exception in UserRepository on empty response" \
  --detail "Root cause: response body not checked before parsing. Fix: add null check before deserializing." \
  --topic networking

# Architectural decision
repomem add \
  --type decision \
  --summary "Use dependency injection framework for all new modules" \
  --detail "Manual wiring was causing circular dependencies and test difficulty" \
  --topic build

# Pending task
repomem add-pending \
  "Add migration rollback tests" \
  --project my-app \
  --priority P1

# Warning
repomem add \
  --type warning \
  --summary "Never use destructive migration in production — causes data loss" \
  --topic database

# Upgrade
repomem add \
  --type upgrade \
  --summary "Upgraded build tool to v9 — requires plugin 3.0.7+" \
  --topic build

# Learning
repomem add \
  --type learning \
  --summary "Background tasks need lifecycle-aware scope to avoid leaks" \
  --topic threading
```

## Available topics

database, networking, build, state, ui, testing, release, security, performance, auth
