"""
RepoMem Obsidian sync — exports project memory to Obsidian markdown.
Target: ~/SUDARSHAN_CODE/sudarshan_repos/SudarshanObsidian/RepoMem/
Format: frontmatter + wikilinks + observations as bullet points.
"""
from __future__ import annotations
import os
from datetime import date
from pathlib import Path
from typing import Optional

from . import db

DEFAULT_VAULT = Path.home() / "SUDARSHAN_CODE/sudarshan_repos/SudarshanObsidian/RepoMem"


def _get_vault_path() -> Path:
    vault = os.environ.get("REPOMEM_OBSIDIAN_VAULT", str(DEFAULT_VAULT))
    return Path(vault)


def _type_emoji(obs_type: str) -> str:
    return {
        "bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️",
        "warning": "⚠️", "learning": "💡", "pending": "📋",
        "pattern": "🔁", "error": "❌",
    }.get(obs_type, "•")


def _render_project(project: str) -> str:
    """Render a single project's memory as Obsidian markdown."""
    today = date.today().isoformat()

    observations = db.get_observations(project=project, limit=50,
                                       include_stale=False, include_archived=False)
    pending = db.get_pending(project=project)
    decisions = db.get_decisions(scope=project)
    errors = db.get_unresolved_errors(project=project)

    # Stats
    stats = db.get_stats(project=project)

    lines: list[str] = []

    # Frontmatter
    lines += [
        "---",
        f"project: {project}",
        f"updated: {today}",
        f"observations: {stats['observations']}",
        f"sessions: {stats['sessions']}",
        f"pending: {stats['pending']}",
        "tags: [repomem, project-memory]",
        "---",
        "",
        f"# {project}",
        "",
        f"> Auto-exported by RepoMem on {today}. Edit source via Claude Code.",
        "",
    ]

    # Decisions
    if decisions:
        lines += ["## ⚡ Decisions", ""]
        for d in decisions:
            scope = "(global)" if d["scope"] == "ALL" else f"({d['scope']})"
            lines.append(f"- **{d['decision']}** {scope}")
            if d["reason"]:
                lines.append(f"  - _{d['reason']}_")
        lines.append("")

    # Pending tasks
    if pending:
        lines += ["## 📋 Pending", ""]
        for p in pending:
            lines.append(f"- [ ] [{p['priority']}] {p['task']}")
        lines.append("")

    # Unresolved errors
    if errors:
        lines += ["## ❌ Unresolved Errors", ""]
        for e in errors:
            recurred = f" _(recurred {e['recurred']}×)_" if e["recurred"] else ""
            lines.append(f"- {e['error_text'][:120]}{recurred}")
            if e["fix"]:
                lines.append(f"  - Fix: {e['fix'][:100]}")
        lines.append("")

    # Observations grouped by type
    if observations:
        by_type: dict[str, list] = {}
        for o in observations:
            by_type.setdefault(o["type"], []).append(o)

        lines += ["## 📝 Observations", ""]
        for obs_type, obs_list in sorted(by_type.items()):
            icon = _type_emoji(obs_type)
            lines.append(f"### {icon} {obs_type.title()}")
            lines.append("")
            for o in obs_list:
                # Wikilink any PascalCase entities
                summary = _add_wikilinks(o["summary"])
                topic = f" `{o['topic']}`" if o["topic"] else ""
                lines.append(f"- {summary}{topic} _({o['date']})_")
                if o["detail"]:
                    lines.append(f"  - {o['detail'][:200]}")
            lines.append("")

    return "\n".join(lines)


def _add_wikilinks(text: str) -> str:
    """Wrap PascalCase words in [[wikilinks]] for Obsidian graph."""
    import re
    return re.sub(
        r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b",
        r"[[\1]]",
        text
    )


def export_project(project: str, vault: Optional[Path] = None) -> Path:
    """Export one project's memory to Obsidian markdown. Returns output path."""
    db.init_db()
    vault_path = vault or _get_vault_path()
    vault_path.mkdir(parents=True, exist_ok=True)

    content = _render_project(project)
    out_path = vault_path / f"{project}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def export_all(vault: Optional[Path] = None) -> list[Path]:
    """Export all active projects. Returns list of written paths."""
    db.init_db()
    stats = db.get_stats()
    projects = stats.get("projects", [])

    written = []
    for project in sorted(projects):
        path = export_project(project, vault=vault)
        written.append(path)

    # Write index file
    vault_path = vault or _get_vault_path()
    _write_index(projects, vault_path)

    return written


def _write_index(projects: list[str], vault_path: Path) -> None:
    today = date.today().isoformat()
    lines = [
        "---",
        f"updated: {today}",
        "tags: [repomem, index]",
        "---",
        "",
        "# RepoMem — Project Index",
        "",
        f"> {len(projects)} projects tracked. Updated {today}.",
        "",
        "## Projects",
        "",
    ]
    for p in sorted(projects):
        lines.append(f"- [[{p}]]")
    lines.append("")

    index_path = vault_path / "_index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
