"""Tests for RepoMem database layer."""
from __future__ import annotations
import os
import tempfile
import pytest

# Use temp DB for tests
os.environ["REPOMEM_DIR"] = tempfile.mkdtemp()

from repomem import db
from repomem.models import Session, Observation, Decision, Pending, Pattern


@pytest.fixture(autouse=True)
def fresh_db():
    """Fresh DB for each test."""
    db.init_db()
    yield
    # Cleanup handled by tempdir


def test_init_db_creates_tables():
    import sqlite3
    conn = sqlite3.connect(str(db.DB_PATH))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "sessions" in tables
    assert "observations" in tables
    assert "decisions" in tables
    assert "pending" in tables
    assert "patterns" in tables


def test_save_and_get_session():
    s = Session(project="TestApp", repo_path="/tmp/TestApp", folder="AndroidApps")
    sid = db.save_session(s)
    assert sid == s.id
    result = db.get_session(sid)
    assert result["project"] == "TestApp"


def test_save_and_search_observation():
    import time
    s = Session(project="DreamWeave", repo_path="/tmp/DreamWeave")
    db.save_session(s)

    obs = Observation(
        session_id=s.id,
        project="DreamWeave",
        type="bugfix",
        topic="viewmodel",
        summary="Fixed null pointer in HomeViewModel",
        created_at=int(time.time()),
    )
    obs_id = db.save_observation(obs)
    assert obs_id > 0

    results = db.search_observations("HomeViewModel", project="DreamWeave")
    assert len(results) > 0
    assert results[0].summary == "Fixed null pointer in HomeViewModel"


def test_get_observations_filters():
    import time
    s = Session(project="HydraTrack", repo_path="/tmp/HydraTrack")
    db.save_session(s)

    for obs_type in ["bugfix", "decision", "upgrade"]:
        obs = Observation(
            session_id=s.id, project="HydraTrack",
            type=obs_type, summary=f"Test {obs_type}",
            created_at=int(time.time()),
        )
        db.save_observation(obs)

    bugfixes = db.get_observations("HydraTrack", obs_type="bugfix")
    assert all(o["type"] == "bugfix" for o in bugfixes)


def test_save_and_get_decision():
    dec = Decision(scope="ALL", topic="build", decision="Use KSP over KAPT")
    did = db.save_decision(dec)
    assert did > 0

    decisions = db.get_decisions()
    assert any(d["decision"] == "Use KSP over KAPT" for d in decisions)


def test_save_and_resolve_pending():
    p = Pending(project="DreamWeave", task="Add dark mode", priority="P1")
    pid = db.save_pending(p)
    assert pid > 0

    items = db.get_pending(project="DreamWeave")
    assert any(i["task"] == "Add dark mode" for i in items)

    db.resolve_pending(pid)
    items_after = db.get_pending(project="DreamWeave")
    assert not any(i["task"] == "Add dark mode" for i in items_after)


def test_stats():
    stats = db.get_stats()
    assert "observations" in stats
    assert "sessions" in stats
    assert "projects" in stats
