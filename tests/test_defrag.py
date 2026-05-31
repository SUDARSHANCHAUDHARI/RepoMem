"""Tests for defrag cron (T17) and conflict detection (T18)."""
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
             summary="test obs", topic="build", confidence=1.0, days_ago=0, detail=""):
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
        detail=detail,
        created_at=int(time.time()),
    )
    return save_observation(obs)


def get_defrag():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "defrag", os.path.join(src, "crons", "defrag.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── T17 defrag tests ──────────────────────────────────────────────────────────

def test_defrag_merges_duplicates():
    from repomem.db import get_connection
    s = make_session()
    make_obs(s.id, summary="Fixed crash in HomeViewModel when state is null on rotation")
    make_obs(s.id, summary="Fixed crash in HomeViewModel when state is null after rotation")

    mod = get_defrag()
    conn = get_connection()
    stats = {}
    mod.step_merge_duplicates(conn, stats)
    conn.commit()
    conn.close()

    assert stats["merged"] >= 1


def test_defrag_archives_stale_old_low_confidence():
    from repomem.db import get_connection
    s = make_session()
    obs_id = make_obs(s.id, confidence=0.3, days_ago=100, summary="old low confidence obs")

    mod = get_defrag()
    conn = get_connection()
    stats = {}
    mod.step_archive_stale(conn, stats)
    conn.commit()

    row = conn.execute("SELECT is_archived FROM observations WHERE id=?", (obs_id,)).fetchone()
    conn.close()
    assert row["is_archived"] == 1
    assert stats["archived"] >= 1


def test_defrag_keeps_recent_low_confidence():
    from repomem.db import get_connection
    s = make_session()
    obs_id = make_obs(s.id, confidence=0.3, days_ago=0)

    mod = get_defrag()
    conn = get_connection()
    stats = {}
    mod.step_archive_stale(conn, stats)
    conn.commit()

    row = conn.execute("SELECT is_archived FROM observations WHERE id=?", (obs_id,)).fetchone()
    conn.close()
    assert row["is_archived"] == 0


def test_defrag_trims_oversized_detail():
    from repomem.db import get_connection
    s = make_session()
    obs_id = make_obs(s.id, detail="x" * 3000)

    mod = get_defrag()
    conn = get_connection()
    stats = {}
    mod.step_split_oversized(conn, stats)
    conn.commit()

    row = conn.execute("SELECT detail FROM observations WHERE id=?", (obs_id,)).fetchone()
    conn.close()
    assert len(row["detail"]) <= 2000
    assert "truncated" in row["detail"]
    assert stats["trimmed"] == 1


def test_defrag_full_run():
    s = make_session()
    make_obs(s.id, summary="some observation to defrag")
    mod = get_defrag()
    mod.main()  # should not raise


# ── T18 conflict detection tests ──────────────────────────────────────────────

def test_conflict_flagged_in_reflect():
    from repomem.db import get_connection, get_conflicts
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "reflect", os.path.join(src, "crons", "reflect.py")
    )
    reflect = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reflect)

    s = make_session()
    make_obs(s.id, obs_type="decision", topic="networking",
             summary="Using Ktor for all network calls")
    make_obs(s.id, obs_type="decision", topic="networking",
             summary="Removed Ktor, switched away to Retrofit")

    conn = get_connection()
    stats = {}
    reflect.step_flag_contradictions(conn, stats)
    conn.commit()
    conn.close()

    assert stats["contradictions_flagged"] >= 1
    conflicts = get_conflicts(project="TestApp")
    assert len(conflicts) >= 1


def test_get_conflicts_returns_linked_pairs():
    from repomem.db import get_connection, get_conflicts
    s = make_session()
    make_obs(s.id, obs_type="decision", topic="build", summary="Use KSP always")
    make_obs(s.id, obs_type="decision", topic="build", summary="Avoid KSP, deprecated")

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "reflect", os.path.join(src, "crons", "reflect.py")
    )
    reflect = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reflect)

    conn = get_connection()
    reflect.step_flag_contradictions(conn, {"contradictions_flagged": 0})
    conn.commit()
    conn.close()

    conflicts = get_conflicts()
    conflict_ids = {c["conflict_id"] for c in conflicts if c["conflict_id"]}
    assert len(conflict_ids) >= 1
