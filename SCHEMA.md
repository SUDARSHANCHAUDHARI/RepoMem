# RepoMem — Database Schema

SQLite + FTS5 · 11 tables · `~/.repomem/memory.db`

---

## sessions

One row per Claude Code session.

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | `"2026-06-01T14:32:00"` |
| `project` | TEXT | Project name (from git remote or dirname) |
| `folder` | TEXT | Parent folder (e.g. mobile, web, tools) |
| `repo_path` | TEXT | Absolute path to repo |
| `started_at` | INTEGER | Unix timestamp |
| `ended_at` | INTEGER | Unix timestamp (NULL while active) |
| `summary` | TEXT | First 500 chars of session summary |
| `obs_count` | INTEGER | Number of observations captured |

---

## observations

All captured facts — the core table.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | TEXT FK | → sessions.id |
| `project` | TEXT | Project name |
| `folder` | TEXT | Parent folder |
| `type` | TEXT | bugfix\|decision\|upgrade\|warning\|learning\|pending\|pattern\|error |
| `topic` | TEXT | Auto-detected: database|di|ui|build|networking|state|auth|storage|release|performance|security|testing |
| `summary` | TEXT | One-line summary (max 200 chars) |
| `detail` | TEXT | Full context (max 2000 chars after defrag) |
| `date` | TEXT | YYYY-MM-DD |
| `created_at` | INTEGER | Unix timestamp |
| `confidence` | REAL | 0.0–1.0 (default 1.0) |
| `seen_count` | INTEGER | Times this observation was seen (dedup counter) |
| `is_stale` | INTEGER | 0/1 — marked by reflect.py on contradiction/decay |
| `is_resolved` | INTEGER | 0/1 |
| `is_archived` | INTEGER | 0/1 — marked by defrag.py |
| `related_ids` | TEXT | Comma-separated related obs IDs |
| `conflict_id` | INTEGER | Links conflicting decision pairs |

**Indexes:** project, date, type, topic, is_stale, is_archived

---

## observations_fts

FTS5 virtual table — kept in sync via triggers.

```sql
CREATE VIRTUAL TABLE observations_fts USING fts5(
    summary, detail, topic, project,
    content='observations', content_rowid='id'
);
```

Triggers: `obs_ai` (INSERT), `obs_ad` (DELETE), `obs_au` (UPDATE)

---

## decisions

Architectural choices — never re-litigate.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `scope` | TEXT | `"ALL"` (global) or project name |
| `topic` | TEXT | DI\|networking\|state\|build\|release… |
| `decision` | TEXT | The decision text |
| `reason` | TEXT | Why this decision was made |
| `date` | TEXT | YYYY-MM-DD |
| `is_superseded` | INTEGER | 0/1 — marked when a newer decision overrides |

---

## pending

Open tasks across all projects.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `project` | TEXT | Project name |
| `task` | TEXT | Task description |
| `priority` | TEXT | P1\|P2\|P3 |
| `created_at` | TEXT | YYYY-MM-DD |
| `resolved_at` | TEXT | YYYY-MM-DD (NULL if open) |
| `session_id` | TEXT | Session that created this task |

---

## patterns

Reusable solutions promoted from observations seen in 3+ projects.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `topic` | TEXT | Topic tag |
| `title` | TEXT | Short title (max 100 chars) |
| `solution` | TEXT | Full solution text |
| `seen_in` | TEXT | Comma-separated project names |
| `seen_count` | INTEGER | Number of projects where seen |
| `date` | TEXT | YYYY-MM-DD |

---

## entities

Named entities extracted from observations (PascalCase classes, files, known libs).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `name` | TEXT | Entity name (e.g. `UserRepository`) |
| `type` | TEXT | class\|file\|library\|god_node |
| `project` | TEXT | Project where first seen |
| `first_seen` | TEXT | YYYY-MM-DD |
| `mention_count` | INTEGER | Times mentioned across all observations |

---

## entity_links

Many-to-many: entity ↔ observation.

| Column | Type | Description |
|--------|------|-------------|
| `entity_id` | INTEGER FK | → entities.id |
| `obs_id` | INTEGER FK | → observations.id |

---

## errors

Crashes and exceptions with root cause and fix.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `project` | TEXT | Project name |
| `error_text` | TEXT | The error/exception text (max 500 chars) |
| `root_cause` | TEXT | Detected root cause |
| `fix` | TEXT | Fix applied |
| `recurred` | INTEGER | How many times this error recurred |
| `first_seen` | TEXT | YYYY-MM-DD |
| `last_seen` | TEXT | YYYY-MM-DD |
| `session_id` | TEXT | Session where first seen |
| `is_resolved` | INTEGER | 0/1 |

---

## releases

Play Store / App Store release history.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `project` | TEXT | Project name |
| `version_name` | TEXT | `"1.2.1"` |
| `version_code` | INTEGER | Integer version code (optional) |
| `released_at` | TEXT | YYYY-MM-DD |
| `store` | TEXT | `"playstore"` \| `"appstore"` |
| `notes` | TEXT | Release notes |
| `session_id` | TEXT | Session where detected |

---

## branches

Git branch tracking per project.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `project` | TEXT | Project name |
| `branch` | TEXT | Branch name |
| `pr_number` | INTEGER | PR number (optional) |
| `pr_url` | TEXT | PR URL |
| `status` | TEXT | `"open"` \| `"merged"` |
| `purpose` | TEXT | What this branch is for |
| `created_at` | TEXT | YYYY-MM-DD |
| `merged_at` | TEXT | YYYY-MM-DD (NULL if open) |
| `session_id` | TEXT | Session where created |

---

## schema_version

Single-row version tracker for migrations.

| Column | Type | Description |
|--------|------|-------------|
| `version` | INTEGER PK | Current schema version |
