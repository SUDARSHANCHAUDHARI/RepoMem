"""
RepoMem database layer — SQLite + FTS5.
Handles: schema creation, migrations, CRUD, FTS5 search.
"""
from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import DB_PATH, ensure_dirs
from .models import Session, Observation, Decision, Pending, Pattern, SearchResult

SCHEMA_VERSION = 1

DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Sessions ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    folder      TEXT NOT NULL DEFAULT '',
    repo_path   TEXT NOT NULL DEFAULT '',
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    summary     TEXT NOT NULL DEFAULT '',
    obs_count   INTEGER NOT NULL DEFAULT 0
);

-- ── Observations ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS observations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    project     TEXT NOT NULL,
    folder      TEXT NOT NULL DEFAULT '',
    type        TEXT NOT NULL,
    topic       TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    date        TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    confidence  REAL NOT NULL DEFAULT 1.0,
    seen_count  INTEGER NOT NULL DEFAULT 1,
    is_stale    INTEGER NOT NULL DEFAULT 0,
    is_resolved INTEGER NOT NULL DEFAULT 0,
    is_archived INTEGER NOT NULL DEFAULT 0,
    related_ids TEXT NOT NULL DEFAULT '',
    conflict_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ── FTS5 virtual table ────────────────────────────────────────────────────────
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
    summary,
    detail,
    topic,
    project,
    content='observations',
    content_rowid='id'
);

-- ── FTS5 triggers to keep index in sync ───────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, summary, detail, topic, project)
    VALUES (new.id, new.summary, new.detail, new.topic, new.project);
END;

CREATE TRIGGER IF NOT EXISTS obs_ad AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, summary, detail, topic, project)
    VALUES ('delete', old.id, old.summary, old.detail, old.topic, old.project);
END;

CREATE TRIGGER IF NOT EXISTS obs_au AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, summary, detail, topic, project)
    VALUES ('delete', old.id, old.summary, old.detail, old.topic, old.project);
    INSERT INTO observations_fts(rowid, summary, detail, topic, project)
    VALUES (new.id, new.summary, new.detail, new.topic, new.project);
END;

-- ── Decisions ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    scope          TEXT NOT NULL,
    topic          TEXT NOT NULL,
    decision       TEXT NOT NULL,
    reason         TEXT NOT NULL DEFAULT '',
    date           TEXT NOT NULL,
    is_superseded  INTEGER NOT NULL DEFAULT 0
);

-- ── Pending tasks ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pending (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    task        TEXT NOT NULL,
    priority    TEXT NOT NULL DEFAULT 'P2',
    created_at  TEXT NOT NULL,
    resolved_at TEXT,
    session_id  TEXT NOT NULL DEFAULT ''
);

-- ── Patterns ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patterns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT NOT NULL,
    title       TEXT NOT NULL,
    solution    TEXT NOT NULL,
    seen_in     TEXT NOT NULL DEFAULT '',
    seen_count  INTEGER NOT NULL DEFAULT 1,
    date        TEXT NOT NULL
);

-- ── Errors ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS errors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project     TEXT NOT NULL,
    error_text  TEXT NOT NULL,
    root_cause  TEXT NOT NULL DEFAULT '',
    fix         TEXT NOT NULL DEFAULT '',
    recurred    INTEGER NOT NULL DEFAULT 0,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT,
    session_id  TEXT NOT NULL DEFAULT '',
    is_resolved INTEGER NOT NULL DEFAULT 0
);

-- ── Entities ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,              -- class|file|library|concept
    project       TEXT NOT NULL DEFAULT '',
    first_seen    TEXT NOT NULL DEFAULT (date('now')),
    mention_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entity_links (
    entity_id INTEGER NOT NULL,
    obs_id    INTEGER NOT NULL,
    PRIMARY KEY (entity_id, obs_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (obs_id)    REFERENCES observations(id)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_obs_project  ON observations(project);
CREATE INDEX IF NOT EXISTS idx_obs_date     ON observations(date);
CREATE INDEX IF NOT EXISTS idx_obs_type     ON observations(type);
CREATE INDEX IF NOT EXISTS idx_obs_topic    ON observations(topic);
CREATE INDEX IF NOT EXISTS idx_obs_stale    ON observations(is_stale);
CREATE INDEX IF NOT EXISTS idx_obs_archived ON observations(is_archived);
CREATE INDEX IF NOT EXISTS idx_pending_proj ON pending(project);
CREATE INDEX IF NOT EXISTS idx_pending_res  ON pending(resolved_at);
CREATE INDEX IF NOT EXISTS idx_decisions_sc ON decisions(scope);
CREATE INDEX IF NOT EXISTS idx_sessions_proj  ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_errors_proj    ON errors(project);
CREATE INDEX IF NOT EXISTS idx_errors_res     ON errors(is_resolved);
CREATE INDEX IF NOT EXISTS idx_entities_name  ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_proj  ON entities(project);
CREATE INDEX IF NOT EXISTS idx_elinks_obs     ON entity_links(obs_id);
"""


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory. Reads DB path dynamically so tests can override via REPOMEM_DIR env."""
    import os as _os
    from pathlib import Path as _Path
    db_path = _Path(_os.environ.get("REPOMEM_DIR", str(DB_PATH.parent))) / "memory.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    """Context manager for DB connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create schema if not exists."""
    ensure_dirs()
    conn = get_connection()
    try:
        conn.executescript(DDL)
        # Set schema version if not set
        cur = conn.execute("SELECT version FROM schema_version")
        row = cur.fetchone()
        if not row:
            conn.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    finally:
        conn.close()


# ── Sessions ──────────────────────────────────────────────────────────────────

def save_session(session: Session) -> str:
    with db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sessions
            (id, project, folder, repo_path, started_at, ended_at, summary, obs_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session.id, session.project, session.folder, session.repo_path,
              session.started_at, session.ended_at, session.summary, session.obs_count))
    return session.id


def end_session(session_id: str, summary: str, obs_count: int) -> None:
    with db() as conn:
        conn.execute("""
            UPDATE sessions SET ended_at=?, summary=?, obs_count=?
            WHERE id=?
        """, (int(time.time()), summary, obs_count, session_id))


def get_session(session_id: str) -> Optional[dict]:
    with db() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None


# ── Observations ──────────────────────────────────────────────────────────────

def save_observation(obs: Observation) -> int:
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO observations
            (session_id, project, folder, type, topic, summary, detail,
             date, created_at, confidence, seen_count, is_stale, is_resolved,
             is_archived, related_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (obs.session_id, obs.project, obs.folder, obs.type, obs.topic,
              obs.summary, obs.detail, obs.date, obs.created_at, obs.confidence,
              obs.seen_count, obs.is_stale, obs.is_resolved, obs.is_archived,
              obs.related_ids))
        return cur.lastrowid


def get_observations(project: str, limit: int = 10,
                     obs_type: Optional[str] = None,
                     topic: Optional[str] = None,
                     include_stale: bool = False,
                     include_archived: bool = False) -> list[dict]:
    filters = ["project = ?"]
    params: list = [project]

    if not include_stale:
        filters.append("is_stale = 0")
    if not include_archived:
        filters.append("is_archived = 0")
    if obs_type:
        filters.append("type = ?")
        params.append(obs_type)
    if topic:
        filters.append("topic LIKE ?")
        params.append(f"%{topic}%")

    where = " AND ".join(filters)
    params.append(limit)

    with db() as conn:
        rows = conn.execute(f"""
            SELECT * FROM observations
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]


def search_observations(query: str, project: Optional[str] = None,
                        limit: int = 20) -> list[SearchResult]:
    """FTS5 full-text search across observations."""
    params: list = [query, limit]
    project_filter = ""
    if project:
        project_filter = "AND o.project = ?"
        params.insert(1, project)

    with db() as conn:
        rows = conn.execute(f"""
            SELECT o.id, o.project, o.type, o.topic, o.summary,
                   o.date, o.confidence, o.detail,
                   rank as rank
            FROM observations_fts
            JOIN observations o ON observations_fts.rowid = o.id
            WHERE observations_fts MATCH ?
              AND o.is_stale = 0
              AND o.is_archived = 0
              {project_filter}
            ORDER BY rank
            LIMIT ?
        """, params).fetchall()

        return [SearchResult(
            id=r["id"], project=r["project"], type=r["type"],
            topic=r["topic"], summary=r["summary"], date=r["date"],
            confidence=r["confidence"], rank=r["rank"], detail=r["detail"]
        ) for r in rows]


def mark_stale(obs_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE observations SET is_stale=1 WHERE id=?", (obs_id,))


def mark_resolved(obs_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE observations SET is_resolved=1 WHERE id=?", (obs_id,))


def mark_archived(obs_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE observations SET is_archived=1 WHERE id=?", (obs_id,))


# ── Decisions ─────────────────────────────────────────────────────────────────

def save_decision(dec: Decision) -> int:
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO decisions (scope, topic, decision, reason, date, is_superseded)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (dec.scope, dec.topic, dec.decision, dec.reason, dec.date, dec.is_superseded))
        return cur.lastrowid


def get_decisions(scope: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if scope and scope != "ALL":
            rows = conn.execute("""
                SELECT * FROM decisions
                WHERE (scope='ALL' OR scope=?) AND is_superseded=0
                ORDER BY date DESC
            """, (scope,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM decisions WHERE is_superseded=0
                ORDER BY scope, date DESC
            """).fetchall()
        return [dict(r) for r in rows]


# ── Pending tasks ─────────────────────────────────────────────────────────────

def save_pending(pending: Pending) -> int:
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO pending (project, task, priority, created_at, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (pending.project, pending.task, pending.priority,
              pending.created_at, pending.session_id))
        return cur.lastrowid


def get_pending(project: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if project:
            rows = conn.execute("""
                SELECT * FROM pending
                WHERE project=? AND resolved_at IS NULL
                ORDER BY priority, created_at
            """, (project,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM pending
                WHERE resolved_at IS NULL
                ORDER BY priority, project, created_at
            """).fetchall()
        return [dict(r) for r in rows]


def resolve_pending(pending_id: int) -> None:
    from datetime import date
    with db() as conn:
        conn.execute("""
            UPDATE pending SET resolved_at=? WHERE id=?
        """, (date.today().isoformat(), pending_id))


# ── Patterns ──────────────────────────────────────────────────────────────────

def save_pattern(pattern: Pattern) -> int:
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO patterns (topic, title, solution, seen_in, seen_count, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pattern.topic, pattern.title, pattern.solution,
              pattern.seen_in, pattern.seen_count, pattern.date))
        return cur.lastrowid


def get_patterns(topic: Optional[str] = None, min_seen: int = 1) -> list[dict]:
    with db() as conn:
        if topic:
            rows = conn.execute("""
                SELECT * FROM patterns
                WHERE topic LIKE ? AND seen_count >= ?
                ORDER BY seen_count DESC
            """, (f"%{topic}%", min_seen)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM patterns WHERE seen_count >= ?
                ORDER BY seen_count DESC
            """, (min_seen,)).fetchall()
        return [dict(r) for r in rows]


# ── Errors ────────────────────────────────────────────────────────────────────

def save_error(project: str, error_text: str, root_cause: str = "",
               fix: str = "", session_id: str = "") -> int:
    from datetime import date as _date
    today = _date.today().isoformat()
    with db() as conn:
        # Check if same error already exists — increment recurred if so
        existing = conn.execute(
            "SELECT id FROM errors WHERE project=? AND error_text=? AND is_resolved=0",
            (project, error_text[:500])
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE errors SET recurred=recurred+1, last_seen=? WHERE id=?",
                (today, existing["id"])
            )
            return existing["id"]
        cur = conn.execute("""
            INSERT INTO errors (project, error_text, root_cause, fix, first_seen, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project, error_text[:500], root_cause, fix, today, session_id))
        return cur.lastrowid


def get_unresolved_errors(project: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if project:
            rows = conn.execute("""
                SELECT * FROM errors WHERE project=? AND is_resolved=0
                ORDER BY recurred DESC, first_seen DESC
            """, (project,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM errors WHERE is_resolved=0
                ORDER BY project, recurred DESC
            """).fetchall()
        return [dict(r) for r in rows]


def resolve_error(error_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE errors SET is_resolved=1 WHERE id=?", (error_id,))


# ── Conflicts ─────────────────────────────────────────────────────────────────

def get_conflicts(project: Optional[str] = None) -> list[dict]:
    """Return pairs of conflicting observations."""
    with db() as conn:
        if project:
            rows = conn.execute("""
                SELECT * FROM observations
                WHERE conflict_id IS NOT NULL AND project=? AND is_archived=0
                ORDER BY conflict_id, date DESC
            """, (project,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM observations
                WHERE conflict_id IS NOT NULL AND is_archived=0
                ORDER BY conflict_id, date DESC
            """).fetchall()
        return [dict(r) for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats(project: Optional[str] = None) -> dict:
    with db() as conn:
        if project:
            obs = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE project=? AND is_archived=0",
                (project,)).fetchone()[0]
            sessions = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE project=?",
                (project,)).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM pending WHERE project=? AND resolved_at IS NULL",
                (project,)).fetchone()[0]
            return {"project": project, "observations": obs,
                    "sessions": sessions, "pending": pending}
        else:
            obs = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE is_archived=0").fetchone()[0]
            sessions = conn.execute(
                "SELECT COUNT(*) FROM sessions").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM pending WHERE resolved_at IS NULL").fetchone()[0]
            decisions = conn.execute(
                "SELECT COUNT(*) FROM decisions WHERE is_superseded=0").fetchone()[0]
            projects = conn.execute(
                "SELECT DISTINCT project FROM observations WHERE is_archived=0").fetchall()
            db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
            return {
                "observations": obs,
                "sessions": sessions,
                "pending": pending,
                "decisions": decisions,
                "projects": [r[0] for r in projects],
                "db_size_kb": round(db_size / 1024, 1),
            }
