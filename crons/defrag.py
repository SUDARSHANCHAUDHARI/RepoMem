#!/usr/bin/env python3
"""
RepoMem defrag — weekly memory cleanup (Sunday 3am).
Steps: merge near-duplicate obs, archive stale low-confidence obs,
       split oversized obs, rebuild FTS5 index, vacuum DB.

Cron: 0 3 * * 0 python3 ~/.repomem/crons/defrag.py >> ~/.repomem/logs/defrag.log 2>&1
"""
from __future__ import annotations
import sys
import os
from datetime import date, timedelta

REPOMEM_INSTALL = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


def _similarity(a: str, b: str) -> float:
    from repomem.utils import text_similarity
    return text_similarity(a, b)


def step_merge_duplicates(conn, stats: dict) -> None:
    """
    Merge near-duplicate observations (>85% similarity, same project+topic).
    Keep the one with highest confidence+seen_count, archive the rest.
    """
    rows = conn.execute("""
        SELECT id, project, topic, summary, confidence, seen_count
        FROM observations
        WHERE is_stale=0 AND is_archived=0
        ORDER BY project, topic, confidence DESC, seen_count DESC
    """).fetchall()

    groups: dict[str, list] = {}
    for r in rows:
        key = f"{r['project']}::{r['topic']}"
        groups.setdefault(key, []).append(r)

    merged = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        archive_ids: set[int] = set()
        for i, a in enumerate(group):
            if a["id"] in archive_ids:
                continue
            for b in group[i + 1:]:
                if b["id"] in archive_ids:
                    continue
                if _similarity(a["summary"], b["summary"]) >= 0.85:
                    # Merge b into a: boost seen_count, archive b
                    conn.execute(
                        "UPDATE observations SET seen_count=seen_count+? WHERE id=?",
                        (b["seen_count"], a["id"])
                    )
                    archive_ids.add(b["id"])
        for aid in archive_ids:
            conn.execute("UPDATE observations SET is_archived=1 WHERE id=?", (aid,))
            merged += 1

    stats["merged"] = merged


def step_archive_stale(conn, stats: dict) -> None:
    """
    Archive observations older than 90 days with low confidence (<0.5)
    that haven't been seen recently (seen_count=1).
    """
    cutoff = (date.today() - timedelta(days=90)).isoformat()
    result = conn.execute("""
        UPDATE observations
        SET is_archived=1
        WHERE date < ? AND confidence < 0.5 AND seen_count=1
          AND is_stale=0 AND is_archived=0
    """, (cutoff,))
    stats["archived"] = result.rowcount


def step_split_oversized(conn, stats: dict) -> None:
    """
    Observations with detail > 2000 chars: trim detail to 2000, append truncation note.
    Prevents token budget blowout on injection.
    """
    rows = conn.execute("""
        SELECT id, detail FROM observations
        WHERE length(detail) > 2000 AND is_archived=0
    """).fetchall()

    trimmed = 0
    for r in rows:
        short = r["detail"][:1950] + "… [truncated by defrag]"
        conn.execute("UPDATE observations SET detail=? WHERE id=?", (short, r["id"]))
        trimmed += 1

    stats["trimmed"] = trimmed


def step_rebuild_fts(conn, stats: dict) -> None:
    """Rebuild FTS5 index to fix any sync drift."""
    try:
        conn.execute("INSERT INTO observations_fts(observations_fts) VALUES('rebuild')")
        stats["fts_rebuilt"] = True
    except Exception:
        stats["fts_rebuilt"] = False


def step_vacuum(conn, stats: dict) -> None:
    """Vacuum the DB — reclaims space from archived rows."""
    conn.commit()  # must commit before VACUUM
    conn.execute("VACUUM")
    stats["vacuumed"] = True


def main() -> None:
    from repomem.db import get_connection, init_db, DB_PATH

    init_db()
    today = date.today().isoformat()
    print(f"[{today}] RepoMem defrag — starting")

    conn = get_connection()
    stats: dict = {}

    try:
        step_merge_duplicates(conn, stats)
        step_archive_stale(conn, stats)
        step_split_oversized(conn, stats)
        step_rebuild_fts(conn, stats)
        step_vacuum(conn, stats)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[{today}] defrag ERROR: {e}")
        raise
    finally:
        conn.close()

    import os as _os
    from pathlib import Path as _Path
    db_path = _Path(_os.environ.get("REPOMEM_DIR", str(DB_PATH.parent))) / "memory.db"
    size_kb = db_path.stat().st_size / 1024 if db_path.exists() else 0

    print(f"[{today}] defrag done:")
    print(f"  merged (archived dupes): {stats.get('merged', 0)}")
    print(f"  archived (stale old):    {stats.get('archived', 0)}")
    print(f"  trimmed (oversized):     {stats.get('trimmed', 0)}")
    print(f"  fts rebuilt:             {stats.get('fts_rebuilt', False)}")
    print(f"  DB size after vacuum:    {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
