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
python3 -m repomem add \
  --type bugfix \
  --summary "Fixed NullPointerException in HomeViewModel collectLatest" \
  --detail "Root cause: StateFlow not initialized before collect in onResume. Fix: move collect to lifecycleScope.launchWhenStarted" \
  --topic viewmodel

# Architectural decision
python3 -m repomem add \
  --type decision \
  --summary "Use DataStore Preferences over SharedPreferences in all new apps" \
  --detail "SharedPreferences deprecated, DataStore is type-safe and coroutine-friendly" \
  --topic datastore

# Pending task
python3 -m repomem add-pending \
  "Add ProGuard rules for Retrofit 3.x" \
  --project DreamWeave \
  --priority P1

# Warning
python3 -m repomem add \
  --type warning \
  --summary "Never use fallbackToDestructiveMigration() in production — data loss risk" \
  --topic room

# Upgrade
python3 -m repomem add \
  --type upgrade \
  --summary "AGP 9.2.1 — requires Crashlytics plugin 3.0.7+" \
  --topic agp
```

## Available topics

room, hilt, compose, agp, kotlin, networking, navigation, viewmodel, datastore, build, release, performance, security
