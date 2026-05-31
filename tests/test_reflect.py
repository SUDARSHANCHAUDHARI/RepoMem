"""Tests for sleep-time reflection cron."""
import os
import sys
import time
import pytest
from datetime import date, timedelta

src = os.path.join(os.path.dirname(__file__), "..")
if src not in sys.path:
    sys.path.insert(0, src)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    yield


def make_session(project="TestApp"):
    from repomem.db import save_session
    from repomem.models import Session
    s = Session(project=project, repo_path="/tmp")
    save_session(s)
    return s


def make_obs(session_id, project="TestApp", obs_type="bugfix",
             summary="test obs", topic="build", confidence=1.0, days_ago=0):
    from repomem.db import save_observation
    from repomem.models import Observation
    obs_date = (date.today() - timedelta(days=days_ago)).isoformat()
    obs = Observation(
        session_id=session_id,
        project=project,
        type=obs_type,
        summary=summary,
        topic=topic,
        confidence=confidence,
        date=obs_date,
        created_at=int(time.time()),
    )
    return save_observation(obs)


def get_reflect_steps():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "reflect",
        os.path.join(src, "crons", "reflect.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dedup_marks_similar_stale():
    from repomem.db import get_connection
    s = make_session()
    make_obs(s.id, summary="Fixed crash in HomeViewModel when state is null on rotation")
    make_obs(s.id, summary="Fixed crash in HomeViewModel when state is null after rotation")

    mod = get_reflect_steps()
    conn = get_connection()
    stats = {}
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    mod.step_dedup(conn, week_ago, stats)
    conn.commit()
    conn.close()

    assert stats["deduped"] >= 1


def test_dedup_keeps_distinct_observations():
    from repomem.db import get_connection
    s = make_session()
    make_obs(s.id, summary="Fixed crash in HomeViewModel")
    make_obs(s.id, summary="Upgraded Room to 2.8.4")

    mod = get_reflect_steps()
    conn = get_connection()
    stats = {}
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    mod.step_dedup(conn, week_ago, stats)
    conn.commit()
    conn.close()

    assert stats["deduped"] == 0


def test_pattern_promotion():
    from repomem.db import get_connection, get_patterns
    for proj in ("AppA", "AppB", "AppC"):
        s = make_session(project=proj)
        make_obs(s.id, project=proj, obs_type="bugfix",
                 summary="Use fake repository pattern for testing", topic="kotlin")

    mod = get_reflect_steps()
    conn = get_connection()
    stats = {}
    mod.step_promote_patterns(conn, stats)
    conn.commit()
    conn.close()

    assert stats["patterns_promoted"] >= 1
    patterns = get_patterns()
    assert any("fake repository" in p["title"].lower() for p in patterns)


def test_temporal_decay_stales_old_low_confidence():
    from repomem.db import get_connection
    import sqlite3

    s = make_session()
    obs_id = make_obs(s.id, confidence=0.3, days_ago=100)

    mod = get_reflect_steps()
    conn = get_connection()
    stats = {}
    mod.step_temporal_decay(conn, "irrelevant", stats)
    conn.commit()

    row = conn.execute("SELECT is_stale FROM observations WHERE id=?", (obs_id,)).fetchone()
    conn.close()

    assert row["is_stale"] == 1
    assert stats["decayed"] >= 1


def test_temporal_decay_keeps_recent():
    from repomem.db import get_connection

    s = make_session()
    obs_id = make_obs(s.id, confidence=0.3, days_ago=0)

    mod = get_reflect_steps()
    conn = get_connection()
    stats = {}
    mod.step_temporal_decay(conn, "irrelevant", stats)
    conn.commit()

    row = conn.execute("SELECT is_stale FROM observations WHERE id=?", (obs_id,)).fetchone()
    conn.close()

    assert row["is_stale"] == 0


def test_full_reflect_runs_without_error(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    s = make_session()
    make_obs(s.id, summary="Fixed build failure after AGP upgrade")

    mod = get_reflect_steps()
    mod.main()  # should not raise
