"""Tests for release + branch tracking (T21)."""
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


from repomem.db import (
    save_release, get_releases, get_last_release,
    save_branch, merge_branch, get_open_branches,
)
from repomem.capture import _capture_releases


def test_save_and_get_release():
    save_release("DreamWeave", "1.2.1", version_code=5)
    releases = get_releases(project="DreamWeave")
    assert len(releases) == 1
    assert releases[0]["version_name"] == "1.2.1"
    assert releases[0]["version_code"] == 5


def test_get_last_release_returns_newest():
    save_release("DreamWeave", "1.0.0")
    save_release("DreamWeave", "1.2.1")
    last = get_last_release("DreamWeave")
    assert last["version_name"] == "1.2.1"


def test_get_last_release_none_when_empty():
    assert get_last_release("NoReleaseApp") is None


def test_save_branch_no_duplicate():
    save_branch("TestApp", "feat/new-screen")
    save_branch("TestApp", "feat/new-screen")
    branches = get_open_branches(project="TestApp")
    assert len(branches) == 1


def test_merge_branch():
    save_branch("TestApp", "feat/new-screen")
    merge_branch("TestApp", "feat/new-screen", pr_number=42)
    branches = get_open_branches(project="TestApp")
    assert len(branches) == 0


def test_capture_releases_detects_version():
    text = "Released v1.3.0 to Play Store successfully."
    _capture_releases(text, "RainLock", "sess1")
    releases = get_releases(project="RainLock")
    assert any(r["version_name"] == "1.3.0" for r in releases)


def test_capture_releases_ignores_no_version():
    text = "Fixed a crash in HomeViewModel."
    _capture_releases(text, "TestApp", "sess1")
    releases = get_releases(project="TestApp")
    assert len(releases) == 0


def test_capture_releases_strips_private():
    text = "Released <private>secret internal build</private> v2.0.0"
    _capture_releases(text, "TestApp", "sess1")
    releases = get_releases(project="TestApp")
    # Should capture version but not secret content
    assert all("secret" not in r["notes"] for r in releases)


def test_inject_warns_on_old_release():
    from repomem.db import save_session, save_observation, db as _db
    from repomem.models import Session, Observation
    from repomem.inject import build_context

    s = Session(project="OldApp", repo_path="/tmp")
    save_session(s)
    save_observation(Observation(
        session_id=s.id, project="OldApp", type="bugfix",
        summary="some fix", created_at=int(time.time())
    ))

    # Save a release from 100 days ago
    old_date = (date.today() - timedelta(days=100)).isoformat()
    with _db() as conn:
        conn.execute(
            "INSERT INTO releases (project, version_name, released_at, store, notes, session_id) VALUES (?,?,?,?,?,?)",
            ("OldApp", "1.0.0", old_date, "playstore", "", "sess")
        )

    ctx = build_context(project="OldApp")
    assert "Last release" in ctx
    assert "1.0.0" in ctx
