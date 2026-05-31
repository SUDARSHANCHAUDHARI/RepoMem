#!/usr/bin/env python3
"""
RepoMem sleep-time reflection — runs on cron 2am daily.
Reviews last 7 days: dedup, pattern promotion, contradiction flagging,
decision promotion, temporal confidence decay.

Cron: 0 2 * * * python3 ~/.repomem/crons/reflect.py >> ~/.repomem/logs/reflect.log 2>&1
"""
from __future__ import annotations
import sys
import os
import re
from datetime import date, timedelta

REPOMEM_INSTALL = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


def _similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity (0.0–1.0). No external deps."""
    wa = set(re.sub(r"[^a-z0-9 ]", "", a.lower()).split())
    wb = set(re.sub(r"[^a-z0-9 ]", "", b.lower()).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def step_dedup(conn, cutoff_date: str, stats: dict) -> None:
    """
    Find observations with >80% text similarity in same project+topic.
    Keep the highest-confidence one, mark the rest stale.
    Increment seen_count on the keeper.
    """
    rows = conn.execute("""
        SELECT id, project, topic, summary, confidence
        FROM observations
        WHERE date >= ? AND is_stale=0 AND is_archived=0
        ORDER BY project, topic, confidence DESC
    """, (cutoff_date,)).fetchall()

    # Group by project+topic
    groups: dict[str, list] = {}
    for r in rows:
        key = f"{r['project']}::{r['topic']}"
        groups.setdefault(key, []).append(r)

    merged = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        # Compare each pair — O(n²) but groups are small
        stale_ids: set[int] = set()
        for i, a in enumerate(group):
            if a["id"] in stale_ids:
                continue
            for b in group[i + 1:]:
                if b["id"] in stale_ids:
                    continue
                if _similarity(a["summary"], b["summary"]) >= 0.80:
                    # Keep a (higher confidence, comes first), stale b
                    stale_ids.add(b["id"])
                    conn.execute(
                        "UPDATE observations SET seen_count=seen_count+1 WHERE id=?",
                        (a["id"],)
                    )
        for sid in stale_ids:
            conn.execute("UPDATE observations SET is_stale=1 WHERE id=?", (sid,))
            merged += 1

    stats["deduped"] = merged


def step_promote_patterns(conn, stats: dict) -> None:
    """
    Find bugfix/learning observations seen across 3+ projects.
    Promote to patterns table if not already there.
    """
    rows = conn.execute("""
        SELECT topic, summary, COUNT(DISTINCT project) as proj_count,
               GROUP_CONCAT(DISTINCT project) as projects
        FROM observations
        WHERE type IN ('bugfix','learning','pattern') AND is_stale=0 AND is_archived=0
        GROUP BY topic, summary
        HAVING proj_count >= 3
    """).fetchall()

    promoted = 0
    for r in rows:
        exists = conn.execute(
            "SELECT id FROM patterns WHERE title=?", (r["summary"][:100],)
        ).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO patterns (topic, title, solution, seen_in, seen_count, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                r["topic"], r["summary"][:100], r["summary"],
                r["projects"], r["proj_count"], date.today().isoformat()
            ))
            promoted += 1
        else:
            conn.execute("""
                UPDATE patterns SET seen_count=?, seen_in=? WHERE id=?
            """, (r["proj_count"], r["projects"], exists["id"]))

    stats["patterns_promoted"] = promoted


def step_flag_contradictions(conn, stats: dict) -> None:
    """
    Find decision-type observations on the same topic+project where
    one says "use X" and a later one says "don't use X" / "switched from X".
    Flag the older one as stale.
    """
    rows = conn.execute("""
        SELECT id, project, topic, summary, date
        FROM observations
        WHERE type='decision' AND is_stale=0 AND is_archived=0
        ORDER BY project, topic, date DESC
    """).fetchall()

    groups: dict[str, list] = {}
    for r in rows:
        key = f"{r['project']}::{r['topic']}"
        groups.setdefault(key, []).append(r)

    flagged = 0
    contradiction_words = re.compile(
        r"\b(don'?t|never|avoid|switched? (from|away)|removed?|replaced?|deprecated?)\b",
        re.IGNORECASE
    )
    for group in groups.values():
        if len(group) < 2:
            continue
        # Newest first; if newest contradicts older, flag older as stale
        newest = group[0]
        if contradiction_words.search(newest["summary"]):
            for older in group[1:]:
                conn.execute(
                    "UPDATE observations SET is_stale=1 WHERE id=?", (older["id"],)
                )
                flagged += 1

    stats["contradictions_flagged"] = flagged


def step_promote_decisions(conn, stats: dict) -> None:
    """
    Observations of type='decision' with seen_count >= 2 and high confidence
    that don't already exist in the decisions table → promote them.
    """
    rows = conn.execute("""
        SELECT project, topic, summary, confidence
        FROM observations
        WHERE type='decision' AND is_stale=0 AND is_archived=0
          AND seen_count >= 2 AND confidence >= 0.8
    """).fetchall()

    promoted = 0
    for r in rows:
        exists = conn.execute(
            "SELECT id FROM decisions WHERE decision=?", (r["summary"][:200],)
        ).fetchone()
        if not exists:
            conn.execute("""
                INSERT INTO decisions (scope, topic, decision, reason, date, is_superseded)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (
                r["project"], r["topic"], r["summary"][:200],
                "Auto-promoted by reflect (seen 2+ times)", date.today().isoformat()
            ))
            promoted += 1

    stats["decisions_promoted"] = promoted


def step_temporal_decay(conn, cutoff_date: str, stats: dict) -> None:
    """
    Observations older than 90 days with confidence < 0.5 and no recent
    seen_count update → mark stale. Lets the DB self-prune over time.
    """
    old_cutoff = (date.today() - timedelta(days=90)).isoformat()
    result = conn.execute("""
        UPDATE observations
        SET is_stale=1
        WHERE date < ? AND confidence < 0.5 AND is_stale=0 AND is_archived=0
    """, (old_cutoff,))
    stats["decayed"] = result.rowcount


def main() -> None:
    from repomem.db import get_connection, init_db

    init_db()
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    print(f"[{today}] RepoMem reflect — starting")

    conn = get_connection()
    stats: dict = {}

    try:
        step_dedup(conn, week_ago, stats)
        step_promote_patterns(conn, stats)
        step_flag_contradictions(conn, stats)
        step_promote_decisions(conn, stats)
        step_temporal_decay(conn, week_ago, stats)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[{today}] reflect ERROR: {e}")
        raise
    finally:
        conn.close()

    print(f"[{today}] reflect done:")
    print(f"  deduped:              {stats.get('deduped', 0)}")
    print(f"  patterns promoted:    {stats.get('patterns_promoted', 0)}")
    print(f"  contradictions flagged: {stats.get('contradictions_flagged', 0)}")
    print(f"  decisions promoted:   {stats.get('decisions_promoted', 0)}")
    print(f"  decayed (staled):     {stats.get('decayed', 0)}")


if __name__ == "__main__":
    main()
