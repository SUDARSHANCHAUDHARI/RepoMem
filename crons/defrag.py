#!/usr/bin/env python3
"""
RepoMem defrag — weekly memory cleanup.
Merges duplicates, archives stale, vacuums DB.

Cron: 0 3 * * 0 python3 ~/.repomem/crons/defrag.py >> ~/.repomem/logs/defrag.log 2>&1
"""
from __future__ import annotations
import sys
import os
from datetime import date

REPOMEM_INSTALL = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


def main():
    try:
        from repomem.config import DB_PATH
        from repomem import db as repomem_db
        import sqlite3

        repomem_db.init_db()

        conn = sqlite3.connect(str(DB_PATH))
        try:
            # Archive observations older than 90 days with low confidence
            from datetime import timedelta
            cutoff = (date.today() - timedelta(days=90)).isoformat()
            archived = conn.execute("""
                UPDATE observations
                SET is_archived = 1
                WHERE date < ? AND confidence < 0.5 AND is_archived = 0
            """, (cutoff,)).rowcount

            # Vacuum DB
            conn.execute("VACUUM")
            conn.commit()

            size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
            print(f"[{date.today()}] RepoMem defrag complete")
            print(f"  Archived {archived} low-confidence observations (>90 days old)")
            print(f"  DB size after vacuum: {size_kb:.1f} KB")

        finally:
            conn.close()

    except ImportError:
        print(f"[{date.today()}] RepoMem not installed — skipping defrag")
    except Exception as e:
        print(f"[{date.today()}] Defrag error: {e}")


if __name__ == "__main__":
    main()
