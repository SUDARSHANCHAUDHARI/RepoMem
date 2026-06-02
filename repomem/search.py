"""
RepoMem search — FTS5 full-text search + filters.
"""
from __future__ import annotations
from typing import Optional
from . import db
from .models import SearchResult


def search(query: str, project: Optional[str] = None,
           obs_type: Optional[str] = None, limit: int = 20) -> list[SearchResult]:
    """
    Search observations using FTS5.
    Falls back to LIKE search if FTS5 fails.
    """
    try:
        results = db.search_observations(query, project=project, limit=limit)
        if obs_type:
            results = [r for r in results if r.type == obs_type]
        return results
    except Exception:
        # Fallback: basic LIKE search
        return _like_search(query, project, obs_type, limit)


def _like_search(query: str, project: Optional[str],
                  obs_type: Optional[str], limit: int) -> list[SearchResult]:
    """Fallback LIKE search when FTS5 unavailable."""
    from . import db as _db_module
    conn = _db_module.get_connection()
    try:
        filters = ["(summary LIKE ? OR detail LIKE ? OR topic LIKE ?)"]
        params: list = [f"%{query}%", f"%{query}%", f"%{query}%"]

        if project:
            filters.append("project = ?")
            params.append(project)
        if obs_type:
            filters.append("type = ?")
            params.append(obs_type)

        filters.extend(["is_stale = 0", "is_archived = 0"])
        params.append(limit)

        where = " AND ".join(filters)
        rows = conn.execute(f"""
            SELECT id, project, type, topic, summary, date, confidence, detail
            FROM observations WHERE {where}
            ORDER BY created_at DESC LIMIT ?
        """, params).fetchall()

        return [SearchResult(
            id=r["id"], project=r["project"], type=r["type"],
            topic=r["topic"], summary=r["summary"], date=r["date"],
            confidence=r["confidence"], detail=r["detail"]
        ) for r in rows]
    finally:
        conn.close()


def format_results(results: list[SearchResult], verbose: bool = False) -> str:
    """Format search results for terminal display."""
    if not results:
        return "No results found."

    lines = [f"Found {len(results)} result(s):\n"]
    for i, r in enumerate(results, 1):
        type_icon = {
            "bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️",
            "warning": "⚠️", "learning": "💡", "pending": "📋",
            "pattern": "🔁", "error": "❌"
        }.get(r.type, "•")

        lines.append(
            f"  #{r.id} {type_icon} [{r.type}] {r.project} — {r.summary} ({r.date})\n"
        )
        if verbose and r.detail:
            lines.append(f"      {r.detail[:200]}\n")

    return "".join(lines)
