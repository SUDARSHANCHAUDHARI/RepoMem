"""
RepoMem Obsidian sync — exports project memory to Obsidian markdown.
Target: set via REPOMEM_OBSIDIAN_VAULT env var, or defaults to ~/obsidian-vault/RepoMem/

Improvements over v1:
- Dynamic topic tags in frontmatter (collected from observations)
- type/status/source/processed fields in frontmatter
- Vault-aware wikilinks: scans real vault .md files, code-block-safe,
  first-occurrence-only, longest-match-first, double-link prevention
- Wikilinks applied to decisions, errors, and pending text (not just obs)
- Patterns, releases, open branches sections added
- --no-wikilinks support via parameter
"""
from __future__ import annotations
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from . import db

DEFAULT_VAULT = Path.home() / "obsidian-vault" / "RepoMem"


def _get_vault_path() -> Path:
    vault = os.environ.get("REPOMEM_OBSIDIAN_VAULT", str(DEFAULT_VAULT))
    return Path(vault)


def _type_emoji(obs_type: str) -> str:
    return {
        "bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️",
        "warning": "⚠️", "learning": "💡", "pending": "📋",
        "pattern": "🔁", "error": "❌",
    }.get(obs_type, "•")


# ── Vault-aware wikilinks ─────────────────────────────────────────────────────

def collect_vault_notes(vault_path: Path) -> list[str]:
    """
    Scan vault for existing .md note names (without extension).
    Sorted longest-first so longer names match before shorter prefixes.
    Skips hidden directories and notes shorter than 4 chars.
    """
    if not vault_path.exists():
        return []
    notes: list[str] = []
    for md in vault_path.rglob("*.md"):
        try:
            rel = md.relative_to(vault_path)
        except ValueError:
            continue
        if any(p.startswith(".") for p in rel.parts):
            continue
        name = md.stem
        if len(name) >= 4:
            notes.append(name)
    notes.sort(key=lambda n: -len(n))
    return notes


def _insert_vault_wikilinks(text: str, vault_notes: list[str]) -> str:
    """
    Insert [[wikilinks]] for vault notes on first occurrence.
    - Skips content inside code fences and inline code
    - Case-insensitive word-boundary matching
    - First-occurrence-only per note
    - Prevents double-linking already-wikilinked text
    """
    if not vault_notes:
        return text
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`)", text)
    linked: set[str] = set()
    for i, part in enumerate(parts):
        if part.startswith("`"):
            continue
        for note in vault_notes:
            if note.lower() in linked:
                continue
            pattern = rf"(?<!\[\[)\b({re.escape(note)})\b(?!\]\])"
            match = re.search(pattern, part, re.IGNORECASE)
            if match:
                parts[i] = part[: match.start()] + f"[[{note}]]" + part[match.end():]
                part = parts[i]
                linked.add(note.lower())
    return "".join(parts)


def _add_wikilinks(text: str, vault_notes: Optional[list[str]] = None) -> str:
    """
    Add wikilinks to text. If vault_notes provided, uses vault-aware linking.
    Falls back to PascalCase-only linking when vault is not available.
    """
    if vault_notes is not None:
        return _insert_vault_wikilinks(text, vault_notes)
    return re.sub(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", r"[[\1]]", text)


# ── Frontmatter ───────────────────────────────────────────────────────────────

def _collect_topics(observations: list[dict]) -> list[str]:
    """Collect unique non-empty topic values from observations."""
    seen: set[str] = set()
    topics: list[str] = []
    for o in observations:
        t = o.get("topic", "")
        if t and t not in seen:
            seen.add(t)
            topics.append(t)
    return sorted(topics)


def _build_frontmatter(project: str, stats: dict, topics: list[str]) -> list[str]:
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    base_tags = ["repomem", "project-memory"] + topics
    tags_yaml = ", ".join(base_tags)
    return [
        "---",
        f"project: {project}",
        f"updated: {today}",
        f"processed: {now}",
        f"observations: {stats['observations']}",
        f"sessions: {stats['sessions']}",
        f"pending: {stats['pending']}",
        f"tags: [{tags_yaml}]",
        "source: repomem",
        "type: project-memory",
        "status: active",
        "---",
        "",
        f"# {project}",
        "",
        f"> Auto-exported by RepoMem on {today}. Edit source via Claude Code.",
        "",
    ]


# ── Render ────────────────────────────────────────────────────────────────────

def _render_project(project: str, vault_notes: Optional[list[str]] = None,
                    no_wikilinks: bool = False) -> str:
    """Render a single project's memory as Obsidian markdown."""
    observations = db.get_observations(project=project, limit=50,
                                       include_stale=False, include_archived=False)
    pending = db.get_pending(project=project)
    decisions = db.get_decisions(scope=project)
    errors = db.get_unresolved_errors(project=project)
    patterns = db.get_patterns(min_seen=1)
    releases = db.get_releases(project=project, limit=5)
    branches = db.get_open_branches(project=project)
    stats = db.get_stats(project=project)

    topics = _collect_topics(observations)
    lines: list[str] = _build_frontmatter(project, stats, topics)

    def _wikilink(text: str) -> str:
        if no_wikilinks:
            return text
        return _add_wikilinks(text, vault_notes)

    # Decisions
    if decisions:
        lines += ["## ⚡ Decisions", ""]
        for d in decisions:
            scope = "(global)" if d["scope"] == "ALL" else f"({d['scope']})"
            lines.append(f"- **{_wikilink(d['decision'])}** {scope}")
            if d["reason"]:
                lines.append(f"  - _{_wikilink(d['reason'])}_")
        lines.append("")

    # Pending tasks
    if pending:
        lines += ["## 📋 Pending", ""]
        for p in pending:
            lines.append(f"- [ ] [{p['priority']}] {_wikilink(p['task'])}")
        lines.append("")

    # Unresolved errors
    if errors:
        lines += ["## ❌ Unresolved Errors", ""]
        for e in errors:
            recurred = f" _(recurred {e['recurred']}×)_" if e["recurred"] else ""
            lines.append(f"- {_wikilink(e['error_text'][:120])}{recurred}")
            if e["fix"]:
                lines.append(f"  - Fix: {_wikilink(e['fix'][:100])}")
        lines.append("")

    # Patterns
    if patterns:
        lines += ["## 🔁 Patterns", ""]
        for p in patterns:
            seen_label = f" _(seen in {p['seen_count']} projects)_" if p["seen_count"] > 1 else ""
            lines.append(f"- **{_wikilink(p['title'])}**{seen_label}")
            if p.get("solution") and p["solution"] != p["title"]:
                lines.append(f"  - {_wikilink(p['solution'][:200])}")
        lines.append("")

    # Releases
    if releases:
        lines += ["## 🚀 Releases", ""]
        for r in releases:
            store = f" `{r['store']}`" if r.get("store") else ""
            lines.append(f"- v{r['version_name']}{store} — {r['released_at']}")
        lines.append("")

    # Open branches
    if branches:
        lines += ["## 🌿 Open Branches", ""]
        for b in branches:
            pr = f" [PR #{b['pr_number']}]({b['pr_url']})" if b.get("pr_number") else ""
            lines.append(f"- `{b['branch']}`{pr} — {b['created_at']}")
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
                summary = _wikilink(o["summary"])
                topic = f" `{o['topic']}`" if o["topic"] else ""
                lines.append(f"- {summary}{topic} _({o['date']})_")
                if o["detail"]:
                    lines.append(f"  - {o['detail'][:200]}")
            lines.append("")

    return "\n".join(lines)


# ── Export ────────────────────────────────────────────────────────────────────

def export_project(project: str, vault: Optional[Path] = None,
                   no_wikilinks: bool = False) -> Path:
    """Export one project's memory to Obsidian markdown. Returns output path."""
    db.init_db()
    vault_path = vault or _get_vault_path()
    vault_path.mkdir(parents=True, exist_ok=True)

    vault_notes = None if no_wikilinks else collect_vault_notes(vault_path)
    content = _render_project(project, vault_notes=vault_notes, no_wikilinks=no_wikilinks)
    out_path = vault_path / f"{project}.md"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def export_all(vault: Optional[Path] = None, no_wikilinks: bool = False) -> list[Path]:
    """Export all active projects. Returns list of written paths."""
    db.init_db()
    stats = db.get_stats()
    projects = stats.get("projects", [])

    vault_path = vault or _get_vault_path()
    vault_path.mkdir(parents=True, exist_ok=True)
    vault_notes = None if no_wikilinks else collect_vault_notes(vault_path)

    written = []
    for project in sorted(projects):
        content = _render_project(project, vault_notes=vault_notes, no_wikilinks=no_wikilinks)
        out_path = vault_path / f"{project}.md"
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)

    _write_index(projects, vault_path)
    return written


def _write_index(projects: list[str], vault_path: Path) -> None:
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "---",
        f"updated: {today}",
        f"processed: {now}",
        "tags: [repomem, index]",
        "source: repomem",
        "type: index",
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
