"""
RepoMem capture — extracts observations from Claude Code session context.
Called by the Stop hook at end of every session.
"""
from __future__ import annotations
import re
import subprocess
import os
from pathlib import Path
from datetime import date
from typing import Optional

from .config import (
    PRIVATE_TAG_START, PRIVATE_TAG_END,
    OBS_TYPES, TOPIC_KEYWORDS, KNOWN_FOLDERS
)
from .models import Session, Observation, Decision, Pending, Pattern
from . import db


def strip_private(text: str) -> str:
    """Remove content between <private>...</private> tags."""
    return re.sub(
        re.escape(PRIVATE_TAG_START) + r".*?" + re.escape(PRIVATE_TAG_END),
        "[PRIVATE]",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )


def detect_project() -> tuple[str, str, str]:
    """
    Detect current project, folder, and repo path.
    Returns (project_name, folder_name, repo_path)
    Fallback chain: git remote → dir name → REPOMEM_PROJECT env var
    """
    # Env override
    if os.environ.get("REPOMEM_PROJECT"):
        project = os.environ["REPOMEM_PROJECT"]
        cwd = os.getcwd()
        return project, _detect_folder(cwd), cwd

    cwd = os.getcwd()

    # Try git remote URL
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL, cwd=cwd
        ).decode().strip()
        # Extract repo name from URL
        # https://github.com/user/RepoName.git → RepoName
        # git@github.com:user/RepoName.git → RepoName
        match = re.search(r"/([^/]+?)(?:\.git)?$", remote)
        if match:
            project = match.group(1)
            return project, _detect_folder(cwd), cwd
    except Exception:
        pass

    # Fallback: directory name
    project = Path(cwd).name
    return project, _detect_folder(cwd), cwd


def _detect_folder(path: str) -> str:
    """Detect which known folder this path is under."""
    p = Path(path)
    for part in p.parts:
        if part in KNOWN_FOLDERS:
            return part
    return ""


def detect_topic(text: str) -> str:
    """Auto-detect topic from observation text using keyword matching."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[topic] = score
    if not scores:
        return ""
    return max(scores, key=scores.get)  # type: ignore


def extract_observations_from_text(text: str, project: str,
                                    folder: str, session_id: str) -> list[Observation]:
    """
    Extract structured observations from free-form session text.
    Looks for signal phrases that indicate observation types.
    """
    text = strip_private(text)
    observations = []
    today = date.today().isoformat()
    import time as _time

    # Pattern matchers — (regex, obs_type)
    patterns = [
        # Bug fixes
        (r"(?:fixed?|resolved?|repaired?)\s+(?:a\s+)?(?:bug|crash|error|issue|problem)[\s:]+([^\n.]{10,120})",
         "bugfix"),
        # Decisions
        (r"(?:decided?|chose?|using|switched? to|migrated? to)[\s:]+([^\n.]{10,120})",
         "decision"),
        # Upgrades
        (r"(?:upgraded?|updated?|bumped?|changed?)[\s:]+(?:to\s+)?(?:version\s+)?([^\n.]{10,100})",
         "upgrade"),
        # Warnings
        (r"(?:warning|caution|watch out|careful|don't|never|avoid)[\s:]+([^\n.]{10,120})",
         "warning"),
        # Learnings
        (r"(?:learned?|discovered?|found out|realized?|note:)[\s:]+([^\n.]{10,120})",
         "learning"),
        # Pending
        (r"(?:todo|next:?|pending:?|still need|needs? to)[\s:]+([^\n.]{10,120})",
         "pending"),
    ]

    seen_summaries: set[str] = set()

    for pattern, obs_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            summary = match.group(1).strip()
            summary = re.sub(r"\s+", " ", summary)  # normalize whitespace
            if len(summary) < 10:
                continue
            if summary.lower() in seen_summaries:
                continue
            seen_summaries.add(summary.lower())

            topic = detect_topic(summary)

            obs = Observation(
                session_id=session_id,
                project=project,
                folder=folder,
                type=obs_type,
                topic=topic,
                summary=summary[:200],  # cap summary length
                detail="",
                date=today,
                created_at=int(_time.time()),
            )
            observations.append(obs)

    return observations


def capture_session(session_summary: str, session_id: Optional[str] = None,
                    extra_obs: Optional[list[dict]] = None) -> int:
    """
    Main entry point. Called by Stop hook.
    Returns number of observations saved.
    """
    import time as _time

    db.init_db()

    project, folder, repo_path = detect_project()

    # Create/update session
    if not session_id:
        from datetime import datetime
        session_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    session = Session(
        id=session_id,
        project=project,
        folder=folder,
        repo_path=repo_path,
        started_at=int(_time.time()),
    )
    db.save_session(session)

    # Extract observations from summary
    observations = extract_observations_from_text(
        session_summary, project, folder, session_id
    )

    # Add any manually provided observations
    if extra_obs:
        today = date.today().isoformat()
        for o in extra_obs:
            obs = Observation(
                session_id=session_id,
                project=project,
                folder=folder,
                type=o.get("type", "learning"),
                topic=o.get("topic", detect_topic(o.get("summary", ""))),
                summary=o.get("summary", "")[:200],
                detail=o.get("detail", ""),
                date=today,
                created_at=int(_time.time()),
            )
            observations.append(obs)

    # Save all observations + link entities
    from .entity import link_observation
    count = 0
    for obs in observations:
        obs_id = db.save_observation(obs)
        link_observation(obs_id, project, obs.summary + " " + obs.detail)
        count += 1

    # Enrich observations with graphify god nodes (if graph exists)
    _enrich_with_graphify(project, repo_path, observations)

    # Detect and record errors, releases, branch activity
    _capture_errors(session_summary, project, session_id)
    _capture_releases(session_summary, project, session_id)
    _capture_branch(project, session_id)

    # Update session with obs count
    db.end_session(session_id, session_summary[:500], count)

    return count


def _enrich_with_graphify(project: str, repo_path: str,
                           observations: list) -> None:
    """Persist graphify god nodes as entities and link to relevant observations."""
    try:
        from .graphify import find_graph, get_god_nodes, enrich_observation
        graph = find_graph(repo_path=repo_path or os.getcwd())
        if not graph:
            return
        god_nodes = get_god_nodes(graph)
        if not god_nodes:
            return
        # Upsert all god nodes as entities (even without a matching observation)
        with db.db() as conn:
            for node in god_nodes:
                label = node["label"]
                existing = conn.execute(
                    "SELECT id FROM entities WHERE name=? AND type='god_node'",
                    (label,)
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO entities (name, type, project, first_seen, mention_count)"
                        " VALUES (?,?,?,date('now'),1)",
                        (label, "god_node", project)
                    )
        # Link observations that mention god nodes
        for obs in observations:
            if hasattr(obs, "id") and obs.id:
                enrich_observation(obs.id, project,
                                   obs.summary + " " + obs.detail, graph)
    except Exception:
        pass  # graphify enrichment is best-effort — never break capture


# ── Error detection ───────────────────────────────────────────────────────────

# Patterns that signal an error in session text
_ERROR_SIGNALS = re.compile(
    r"(?:Exception|Error|Crash|FAILED|fatal|stack\s*trace|caused\s*by)[:\s]+([^\n]{10,200})",
    re.IGNORECASE
)

# Patterns that signal a root cause
_CAUSE_SIGNALS = re.compile(
    r"(?:because|caused\s*by|root\s*cause|reason)[:\s]+([^\n]{10,200})",
    re.IGNORECASE
)

# Patterns that signal a fix was applied
_FIX_SIGNALS = re.compile(
    r"(?:fixed?\s*by|resolved?\s*by|solution[:\s]+|workaround[:\s]+)([^\n]{10,200})",
    re.IGNORECASE
)


def _capture_errors(text: str, project: str, session_id: str) -> None:
    """Extract error signals from session text and save to errors table."""
    text = strip_private(text)

    root_cause = ""
    fix = ""

    cause_m = _CAUSE_SIGNALS.search(text)
    if cause_m:
        root_cause = cause_m.group(1).strip()[:200]

    fix_m = _FIX_SIGNALS.search(text)
    if fix_m:
        fix = fix_m.group(1).strip()[:200]

    seen: set[str] = set()
    for m in _ERROR_SIGNALS.finditer(text):
        error_text = m.group(1).strip()
        error_text = re.sub(r"\s+", " ", error_text)
        key = error_text[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        db.save_error(project, error_text, root_cause, fix, session_id)


# ── Release detection ─────────────────────────────────────────────────────────

_RELEASE_SIGNALS = re.compile(
    r"(?:released?\s+v?|Play\s*Store\s+(?:upload|submitted?)|merged?\s+PR[:\s]+.*?v?)(\d+\.\d+[\.\d]*)",
    re.IGNORECASE
)


def _capture_releases(text: str, project: str, session_id: str) -> None:
    """Detect version release signals in session text."""
    text = strip_private(text)
    seen: set[str] = set()
    for m in _RELEASE_SIGNALS.finditer(text):
        version = m.group(1).strip()
        if version in seen:
            continue
        seen.add(version)
        db.save_release(project, version_name=version, session_id=session_id)


# ── Branch tracking ───────────────────────────────────────────────────────────

def _capture_branch(project: str, session_id: str) -> None:
    """Record the current git branch for this project."""
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL, cwd=os.getcwd()
        ).decode().strip()
        if branch and branch not in ("main", "master", ""):
            db.save_branch(project, branch, session_id=session_id)
    except Exception:
        pass
