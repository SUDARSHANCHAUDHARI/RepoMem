"""
RepoMem data models — dataclasses for every table.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Session:
    project: str
    repo_path: str
    folder: str = ""
    summary: str = ""
    obs_count: int = 0
    id: str = ""
    started_at: int = field(default_factory=lambda: int(time.time()))
    ended_at: Optional[int] = None

    def __post_init__(self):
        if not self.id:
            from datetime import datetime
            self.id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class Observation:
    project: str
    type: str
    summary: str
    session_id: str
    folder: str = ""
    topic: str = ""
    detail: str = ""
    confidence: float = 1.0
    seen_count: int = 1
    is_stale: int = 0
    is_resolved: int = 0
    is_archived: int = 0
    related_ids: str = ""
    id: Optional[int] = None
    date: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))

    def __post_init__(self):
        if not self.date:
            from datetime import date
            self.date = date.today().isoformat()


@dataclass
class Decision:
    scope: str          # "ALL" or project name
    topic: str
    decision: str
    reason: str = ""
    is_superseded: int = 0
    id: Optional[int] = None
    date: str = ""

    def __post_init__(self):
        if not self.date:
            from datetime import date
            self.date = date.today().isoformat()


@dataclass
class Pending:
    project: str
    task: str
    priority: str = "P2"
    session_id: str = ""
    resolved_at: Optional[str] = None
    id: Optional[int] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            from datetime import date
            self.created_at = date.today().isoformat()


@dataclass
class Pattern:
    topic: str
    title: str
    solution: str
    seen_in: str = ""
    seen_count: int = 1
    id: Optional[int] = None
    date: str = ""

    def __post_init__(self):
        if not self.date:
            from datetime import date
            self.date = date.today().isoformat()


@dataclass
class SearchResult:
    id: int
    project: str
    type: str
    topic: str
    summary: str
    date: str
    confidence: float
    rank: float = 0.0
    detail: str = ""
