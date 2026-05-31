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

    # Update session with obs count
    db.end_session(session_id, session_summary[:500], count)

    return count
