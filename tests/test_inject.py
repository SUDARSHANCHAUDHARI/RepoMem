"""Tests for inject temporal reasoning."""
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


from repomem.inject import _age_label, _recency_score, _sort_by_recency, build_context


def test_age_label_today():
    assert _age_label(date.today().isoformat()) == "today"


def test_age_label_days():
    d = (date.today() - timedelta(days=5)).isoformat()
    assert _age_label(d) == "5d ago"


def test_age_label_weeks():
    d = (date.today() - timedelta(days=14)).isoformat()
    assert _age_label(d) == "2w ago"


def test_age_label_months():
    d = (date.today() - timedelta(days=60)).isoformat()
    assert _age_label(d) == "2mo ago"


def test_recency_score_recent_beats_old():
    today = date.today().isoformat()
    old = (date.today() - timedelta(days=180)).isoformat()
    assert _recency_score(today, 1.0) > _recency_score(old, 1.0)


def test_recency_score_high_confidence_beats_low():
    today = date.today().isoformat()
    assert _recency_score(today, 0.9) > _recency_score(today, 0.5)


def test_sort_by_recency_orders_newest_first():
    obs = [
        {"date": (date.today() - timedelta(days=90)).isoformat(), "confidence": 1.0, "summary": "old"},
        {"date": date.today().isoformat(), "confidence": 1.0, "summary": "new"},
        {"date": (date.today() - timedelta(days=30)).isoformat(), "confidence": 1.0, "summary": "mid"},
    ]
    sorted_obs = _sort_by_recency(obs)
    assert sorted_obs[0]["summary"] == "new"
    assert sorted_obs[-1]["summary"] == "old"


def test_build_context_shows_age_for_old_obs():
    from repomem.db import save_session, save_observation
    from repomem.models import Session, Observation

    s = Session(project="TestApp", repo_path="/tmp")
    save_session(s)

    old_date = (date.today() - timedelta(days=30)).isoformat()
    obs = Observation(
        session_id=s.id, project="TestApp", type="bugfix",
        summary="Fixed Room migration crash",
        date=old_date, created_at=int(time.time()),
    )
    # Manually set date
    from repomem.db import db as _db
    obs_id = save_observation(obs)
    with _db() as conn:
        conn.execute("UPDATE observations SET date=? WHERE id=?", (old_date, obs_id))

    ctx = build_context(project="TestApp")
    assert "Fixed Room migration crash" in ctx
    assert "mo ago" in ctx or "w ago" in ctx


def test_build_context_no_age_label_for_recent():
    from repomem.db import save_session, save_observation
    from repomem.models import Session, Observation

    s = Session(project="TestApp", repo_path="/tmp")
    save_session(s)

    obs = Observation(
        session_id=s.id, project="TestApp", type="bugfix",
        summary="Just fixed something today",
        created_at=int(time.time()),
    )
    save_observation(obs)

    ctx = build_context(project="TestApp")
    # Recent obs should not have an age suffix like "(2mo ago)"
    assert "Just fixed something today" in ctx
    line = [l for l in ctx.splitlines() if "Just fixed" in l][0]
    assert "ago" not in line
