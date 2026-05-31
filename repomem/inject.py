"""
RepoMem inject — builds context string for SessionStart hook.
Queries DB for relevant observations and formats for Claude injection.
Token-conscious: hard cap at MAX_INJECT_CHARS.
Temporal reasoning: recency × confidence ranking, age labels on old obs.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional

from .config import (
    MAX_INJECT_CHARS, MAX_OBS_PER_PROJECT,
    MAX_DECISIONS, MAX_PENDING
)
from . import db


# ── Temporal helpers ──────────────────────────────────────────────────────────

def _age_label(obs_date: str) -> str:
    """Return human-readable age label for an observation date string."""
    try:
        d = date.fromisoformat(obs_date)
        delta = (date.today() - d).days
        if delta <= 1:
            return "today"
        if delta <= 7:
            return f"{delta}d ago"
        if delta <= 30:
            weeks = delta // 7
            return f"{weeks}w ago"
        if delta <= 365:
            months = delta // 30
            return f"{months}mo ago"
        years = delta // 365
        return f"{years}y ago"
    except Exception:
        return obs_date


def _recency_score(obs_date: str, confidence: float) -> float:
    """
    Score = recency_weight × confidence.
    Observations in the last 7 days get full recency weight (1.0).
    Older observations decay linearly to 0.1 over 365 days.
    """
    try:
        d = date.fromisoformat(obs_date)
        days_old = (date.today() - d).days
        if days_old <= 7:
            recency = 1.0
        else:
            recency = max(0.1, 1.0 - (days_old - 7) / 365)
        return recency * confidence
    except Exception:
        return confidence


def _sort_by_recency(observations: list[dict]) -> list[dict]:
    """Sort observations by recency×confidence descending."""
    return sorted(
        observations,
        key=lambda o: _recency_score(o["date"], o.get("confidence", 1.0)),
        reverse=True
    )


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(project: Optional[str] = None) -> str:
    """
    Build context injection string for current project.
    Priority order:
      1. Global decisions (always)
      2. Open pending tasks (this project)
      3. Recent observations — ranked by recency × confidence
      4. Patterns relevant to this project
    Returns empty string if DB missing or project unknown.
    """
    try:
        db.init_db()
    except Exception:
        return ""

    if not project:
        from .capture import detect_project
        try:
            project, _, _ = detect_project()
        except Exception:
            return ""

    sections: list[str] = []
    total_chars = 0

    def add_section(text: str) -> bool:
        nonlocal total_chars
        if total_chars + len(text) > MAX_INJECT_CHARS:
            return False
        sections.append(text)
        total_chars += len(text)
        return True

    header = f"\n╔══ RepoMem: {project} ══\n"
    add_section(header)

    # 1. Global + project decisions
    decisions = db.get_decisions(scope=project)[:MAX_DECISIONS]
    if decisions:
        lines = ["║ DECISIONS\n"]
        for d in decisions:
            scope_label = "(global)" if d["scope"] == "ALL" else f"({d['scope']})"
            lines.append(f"║  • {d['decision']} {scope_label}\n")
        add_section("".join(lines))

    # 2. Open pending tasks
    pending = db.get_pending(project=project)[:MAX_PENDING]
    if pending:
        lines = ["║ PENDING\n"]
        for p in pending:
            lines.append(f"║  • [{p['priority']}] {p['task']}\n")
        add_section("".join(lines))

    # 3. Observations — ranked by recency × confidence, age-labelled
    raw_obs = db.get_observations(project=project, limit=MAX_OBS_PER_PROJECT * 3)
    obs = _sort_by_recency(raw_obs)[:MAX_OBS_PER_PROJECT]

    week_ago = (date.today() - timedelta(days=7)).isoformat()

    if obs:
        lines = ["║ RECENT\n"]
        for o in obs:
            type_icon = {
                "bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️",
                "warning": "⚠️", "learning": "💡", "pending": "📋",
                "pattern": "🔁", "error": "❌"
            }.get(o["type"], "•")
            age = _age_label(o["date"])
            # Prefix stale-ish obs (older than 7d) with age so Claude can judge relevance
            age_str = f" ({age})" if o["date"] < week_ago else ""
            lines.append(f"║  {type_icon} [{o['type']}] {o['summary']}{age_str}\n")
        add_section("".join(lines))

    # 4. Unresolved errors
    errors = db.get_unresolved_errors(project=project)
    if errors:
        lines = ["║ UNRESOLVED ERRORS\n"]
        for e in errors[:3]:
            recurred = f" (recurred {e['recurred']}×)" if e["recurred"] else ""
            lines.append(f"║  ❌ {e['error_text'][:100]}{recurred}\n")
            if e["fix"]:
                lines.append(f"║     fix: {e['fix'][:80]}\n")
        add_section("".join(lines))

    # 5. Cross-project patterns
    patterns = db.get_patterns(min_seen=2)[:3]
    if patterns:
        lines = ["║ PATTERNS (seen across projects)\n"]
        for p in patterns:
            lines.append(f"║  🔁 {p['title']} — seen in {p['seen_count']} projects\n")
        add_section("".join(lines))

    footer = "╚══\n"
    add_section(footer)

    result = "".join(sections)
    return result if len(result) > len(header) + len(footer) + 10 else ""


def build_system_message(project: Optional[str] = None) -> dict:
    """Return JSON for SessionStart hook systemMessage."""
    context = build_context(project)
    if not context:
        return {}
    return {"systemMessage": context}
