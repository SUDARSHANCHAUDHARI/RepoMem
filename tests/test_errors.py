"""Tests for error tracking (T16)."""
import os
import sys
import time
import pytest

src = os.path.join(os.path.dirname(__file__), "..")
if src not in sys.path:
    sys.path.insert(0, src)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    yield


from repomem.db import save_error, get_unresolved_errors, resolve_error
from repomem.capture import _capture_errors


def test_save_error_basic():
    eid = save_error("TestApp", "NullPointerException in HomeViewModel")
    assert eid > 0
    errors = get_unresolved_errors(project="TestApp")
    assert len(errors) == 1
    assert "NullPointerException" in errors[0]["error_text"]


def test_same_error_increments_recurred():
    save_error("TestApp", "NullPointerException in HomeViewModel")
    save_error("TestApp", "NullPointerException in HomeViewModel")
    errors = get_unresolved_errors(project="TestApp")
    assert len(errors) == 1
    assert errors[0]["recurred"] == 1


def test_resolve_error():
    eid = save_error("TestApp", "CrashException in onCreate")
    resolve_error(eid)
    errors = get_unresolved_errors(project="TestApp")
    assert len(errors) == 0


def test_capture_errors_from_text():
    text = """
    Session summary:
    We encountered an Exception: FOREIGN KEY constraint failed during migration.
    The root cause was because the session row was not created before observations.
    Fixed by adding _ensure_mcp_session helper.
    """
    _capture_errors(text, "RepoMem", "test-session")
    errors = get_unresolved_errors(project="RepoMem")
    assert len(errors) >= 1
    assert any("FOREIGN KEY" in e["error_text"] for e in errors)


def test_capture_errors_extracts_fix():
    text = "Error: build failed. Fixed by running gradle clean."
    _capture_errors(text, "TestApp", "sess1")
    errors = get_unresolved_errors(project="TestApp")
    assert any(e["fix"] for e in errors)


def test_capture_errors_strips_private():
    text = "Exception: <private>secret token abc123</private> caused auth failure"
    _capture_errors(text, "TestApp", "sess1")
    errors = get_unresolved_errors(project="TestApp")
    for e in errors:
        assert "secret token" not in e["error_text"]
        assert "abc123" not in e["error_text"]


def test_inject_shows_unresolved_errors():
    save_error("MyApp", "NullPointerException in onResume", fix="Added null check")
    from repomem.inject import build_context
    # Need a session to exist for inject to show project context
    from repomem.db import save_session, save_observation
    from repomem.models import Session, Observation
    s = Session(project="MyApp", repo_path="/tmp")
    save_session(s)
    obs = Observation(session_id=s.id, project="MyApp", type="bugfix",
                      summary="some obs", created_at=int(time.time()))
    save_observation(obs)

    ctx = build_context(project="MyApp")
    assert "UNRESOLVED ERRORS" in ctx
    assert "NullPointerException" in ctx
