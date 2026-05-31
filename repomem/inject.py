"""
RepoMem inject — builds context string for SessionStart hook.
Queries DB for relevant observations and formats for Claude injection.
Token-conscious: hard cap at MAX_INJECT_CHARS.
"""
from __future__ import annotations
from typing import Optional

from .config import (
    MAX_INJECT_CHARS, MAX_OBS_PER_PROJECT,
    MAX_DECISIONS, MAX_PENDING
)
from . import db


def build_context(project: Optional[str] = None) -> str:
    """
    Build context injection string for current project.
    Priority order:
      1. Global decisions (always)
      2. Open pending tasks (this project)
      3. Recent observations (this project)
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

    # 3. Recent observations
    obs = db.get_observations(project=project, limit=MAX_OBS_PER_PROJECT)
    if obs:
        lines = ["║ RECENT\n"]
        for o in obs:
            type_icon = {
                "bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️",
                "warning": "⚠️", "learning": "💡", "pending": "📋",
                "pattern": "🔁", "error": "❌"
            }.get(o["type"], "•")
            lines.append(f"║  {type_icon} [{o['type']}] {o['summary']} ({o['date']})\n")
        add_section("".join(lines))

    # 4. Cross-project patterns
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
