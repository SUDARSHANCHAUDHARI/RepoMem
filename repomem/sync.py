"""
RepoMem git sync — cross-machine memory sharing via git.
Export observations as JSON chunks to SYNC_DIR, commit via git.
Import chunks from another machine and merge (last-write-wins by id).

Usage:
  repomem sync --export     # export new obs to sync/ and commit
  repomem sync --import     # import chunks from sync/ into local DB
  repomem sync --status     # show sync state
"""
from __future__ import annotations
import json
import os
import subprocess
import time
from datetime import date
from pathlib import Path
from typing import Optional

from .config import SYNC_DIR, REPOMEM_DIR
from . import db


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_sync_dir() -> Path:
    sync = Path(os.environ.get("REPOMEM_DIR", str(REPOMEM_DIR))) / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    return sync


def _machine_id() -> str:
    """Stable machine identifier — hostname + username."""
    import socket
    return f"{socket.gethostname()}-{os.environ.get('USER', 'user')}"


def _chunk_path(sync_dir: Path) -> Path:
    machine = _machine_id().replace("/", "_").replace(" ", "_")
    return sync_dir / f"{machine}.json"


def _watermark_path() -> Path:
    return Path(os.environ.get("REPOMEM_DIR", str(REPOMEM_DIR))) / "sync_watermark.json"


def _load_watermark() -> dict:
    p = _watermark_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"last_exported_id": 0, "last_export_ts": 0}


def _save_watermark(data: dict) -> None:
    _watermark_path().write_text(json.dumps(data, indent=2))


# ── Export ────────────────────────────────────────────────────────────────────

def export_sync(commit: bool = True) -> dict:
    """
    Export observations newer than last watermark to sync/<machine>.json.
    Optionally commits the sync file via git.
    Returns stats dict.
    """
    db.init_db()
    watermark = _load_watermark()
    last_id = watermark.get("last_exported_id", 0)

    sync_dir = _get_sync_dir()

    with db.db() as conn:
        rows = conn.execute("""
            SELECT id, session_id, project, folder, type, topic,
                   summary, detail, date, created_at, confidence,
                   seen_count, is_stale, is_resolved, is_archived, related_ids
            FROM observations
            WHERE id > ? AND is_archived=0
            ORDER BY id ASC
        """, (last_id,)).fetchall()

        decisions = conn.execute("""
            SELECT id, scope, topic, decision, reason, date, is_superseded
            FROM decisions WHERE is_superseded=0
        """).fetchall()

        pending_rows = conn.execute("""
            SELECT id, project, task, priority, created_at, resolved_at, session_id
            FROM pending WHERE resolved_at IS NULL
        """).fetchall()

    observations = [dict(r) for r in rows]
    max_id = max((o["id"] for o in observations), default=last_id)

    chunk = {
        "machine": _machine_id(),
        "exported_at": date.today().isoformat(),
        "watermark": last_id,
        "observations": observations,
        "decisions": [dict(r) for r in decisions],
        "pending": [dict(r) for r in pending_rows],
    }

    chunk_file = _chunk_path(sync_dir)
    chunk_file.write_text(json.dumps(chunk, indent=2))

    _save_watermark({
        "last_exported_id": max_id,
        "last_export_ts": int(time.time()),
    })

    stats = {
        "observations": len(observations),
        "decisions": len(decisions),
        "pending": len(pending_rows),
        "chunk_file": str(chunk_file),
        "committed": False,
    }

    if commit:
        stats["committed"] = _git_commit_sync(sync_dir)

    return stats


def _git_commit_sync(sync_dir: Path) -> bool:
    """Add sync file and commit via git. Returns True if commit succeeded."""
    try:
        repomem_dir = Path(os.environ.get("REPOMEM_DIR", str(REPOMEM_DIR)))
        subprocess.check_output(
            ["git", "add", str(sync_dir)],
            stderr=subprocess.DEVNULL,
            cwd=str(repomem_dir)
        )
        msg = f"repomem sync export {date.today().isoformat()} [{_machine_id()}]"
        subprocess.check_output(
            ["git", "commit", "-m", msg],
            stderr=subprocess.DEVNULL,
            cwd=str(repomem_dir)
        )
        return True
    except subprocess.CalledProcessError:
        return False  # nothing to commit or not a git repo
    except Exception:
        return False


# ── Import ────────────────────────────────────────────────────────────────────

def import_sync() -> dict:
    """
    Import all chunk files from sync_dir into local DB.
    Merge strategy: last-write-wins per observation id (higher id = newer).
    Skips chunks from this machine.
    """
    db.init_db()
    sync_dir = _get_sync_dir()
    my_machine = _machine_id()

    imported_obs = 0
    imported_dec = 0
    imported_pending = 0
    skipped_files = 0

    for chunk_file in sync_dir.glob("*.json"):
        try:
            chunk = json.loads(chunk_file.read_text())
        except Exception:
            continue

        if chunk.get("machine") == my_machine:
            skipped_files += 1
            continue

        # Import observations
        for o in chunk.get("observations", []):
            _upsert_observation(o)
            imported_obs += 1

        # Import decisions (by decision text — no duplicate)
        for d in chunk.get("decisions", []):
            _upsert_decision(d)
            imported_dec += 1

        # Import pending (by project+task — no duplicate)
        for p in chunk.get("pending", []):
            _upsert_pending(p)
            imported_pending += 1

    return {
        "observations": imported_obs,
        "decisions": imported_dec,
        "pending": imported_pending,
        "skipped_own_machine": skipped_files,
    }


def _upsert_observation(o: dict) -> None:
    """Insert observation if not already present (by original id is not reliable cross-machine — use summary+project+date)."""
    with db.db() as conn:
        # Use a sentinel session for imported observations
        session_id = o.get("session_id", "sync-import")
        _ensure_session(conn, session_id, o.get("project", "unknown"))

        exists = conn.execute(
            "SELECT id FROM observations WHERE project=? AND summary=? AND date=?",
            (o["project"], o["summary"], o["date"])
        ).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO observations
                (session_id, project, folder, type, topic, summary, detail,
                 date, created_at, confidence, seen_count, is_stale, is_resolved,
                 is_archived, related_ids)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id, o["project"], o.get("folder", ""),
                o["type"], o.get("topic", ""), o["summary"],
                o.get("detail", ""), o["date"],
                o.get("created_at", int(time.time())),
                o.get("confidence", 1.0), o.get("seen_count", 1),
                o.get("is_stale", 0), o.get("is_resolved", 0),
                o.get("is_archived", 0), o.get("related_ids", "")
            ))


def _ensure_session(conn, session_id: str, project: str) -> None:
    exists = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO sessions (id, project, folder, repo_path, started_at) VALUES (?,?,?,?,?)",
            (session_id, project, "", "", int(time.time()))
        )


def _upsert_decision(d: dict) -> None:
    with db.db() as conn:
        exists = conn.execute(
            "SELECT id FROM decisions WHERE decision=? AND scope=?",
            (d["decision"], d["scope"])
        ).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO decisions (scope, topic, decision, reason, date, is_superseded)
                VALUES (?,?,?,?,?,?)
            """, (d["scope"], d["topic"], d["decision"],
                  d.get("reason", ""), d["date"], d.get("is_superseded", 0)))


def _upsert_pending(p: dict) -> None:
    with db.db() as conn:
        exists = conn.execute(
            "SELECT id FROM pending WHERE project=? AND task=? AND resolved_at IS NULL",
            (p["project"], p["task"])
        ).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO pending (project, task, priority, created_at, session_id)
                VALUES (?,?,?,?,?)
            """, (p["project"], p["task"], p.get("priority", "P2"),
                  p.get("created_at", date.today().isoformat()),
                  p.get("session_id", "sync-import")))


# ── Status ────────────────────────────────────────────────────────────────────

def sync_status() -> dict:
    """Return current sync state."""
    watermark = _load_watermark()
    sync_dir = _get_sync_dir()
    chunks = list(sync_dir.glob("*.json"))
    my_chunk = _chunk_path(sync_dir)

    return {
        "machine": _machine_id(),
        "last_exported_id": watermark.get("last_exported_id", 0),
        "last_export_ts": watermark.get("last_export_ts", 0),
        "chunk_file": str(my_chunk),
        "chunk_exists": my_chunk.exists(),
        "peer_chunks": [c.name for c in chunks if c != my_chunk],
    }
