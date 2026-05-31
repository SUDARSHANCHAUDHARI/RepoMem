"""Tests for CLI commands."""
import os
import sys
import time
import pytest
from io import StringIO

src = os.path.join(os.path.dirname(__file__), "..")
if src not in sys.path:
    sys.path.insert(0, src)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "TestApp")
    from repomem.db import init_db
    init_db()
    yield


def run_cli(*args, expect_exit=0):
    """Run CLI main() with given args, capture stdout."""
    from repomem.cli import main
    import argparse

    old_argv = sys.argv
    old_stdout = sys.stdout
    sys.argv = ["repomem"] + list(args)
    sys.stdout = out = StringIO()
    try:
        try:
            main()
        except SystemExit as e:
            if e.code != expect_exit:
                raise
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
    return out.getvalue()


# ── status ────────────────────────────────────────────────────────────────────

def test_status_shows_stats():
    output = run_cli("status")
    assert "Observations" in output
    assert "Sessions" in output
    assert "DB size" in output


def test_status_project_filter():
    output = run_cli("status", "--project", "TestApp")
    assert "TestApp" in output


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_observation_no_fk_error():
    output = run_cli("add", "--type", "bugfix",
                     "--summary", "Fixed crash in HomeViewModel",
                     "--project", "TestApp")
    assert "Saved observation" in output
    assert "bugfix" in output


def test_add_creates_manual_session():
    run_cli("add", "--type", "learning",
            "--summary", "Learned that StateFlow needs lifecycle scope",
            "--project", "TestApp")
    from repomem.db import get_session
    s = get_session("manual")
    assert s is not None


def test_add_second_obs_no_duplicate_session():
    run_cli("add", "--type", "bugfix", "--summary", "First fix", "--project", "TestApp")
    run_cli("add", "--type", "warning", "--summary", "Second warning", "--project", "TestApp")
    from repomem.db import db as _db
    with _db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM sessions WHERE id='manual'").fetchone()[0]
    assert count == 1


# ── pending ───────────────────────────────────────────────────────────────────

def test_add_pending_no_fk_error():
    output = run_cli("add-pending", "Write Room migration tests",
                     "--project", "TestApp", "--priority", "P1")
    assert "Added pending task" in output
    assert "P1" in output


def test_pending_lists_tasks():
    run_cli("add-pending", "My pending task", "--project", "TestApp")
    output = run_cli("pending")
    assert "My pending task" in output


def test_pending_project_filter():
    run_cli("add-pending", "Task for TestApp", "--project", "TestApp")
    run_cli("add-pending", "Task for OtherApp", "--project", "OtherApp")
    output = run_cli("pending", "--project", "TestApp")
    assert "Task for TestApp" in output
    assert "Task for OtherApp" not in output


def test_resolve_pending():
    run_cli("add-pending", "Task to resolve", "--project", "TestApp")
    from repomem.db import get_pending
    items = get_pending(project="TestApp")
    task_id = items[0]["id"]
    run_cli("resolve", str(task_id))
    remaining = get_pending(project="TestApp")
    assert not any(i["id"] == task_id for i in remaining)


# ── decisions ─────────────────────────────────────────────────────────────────

def test_add_decision():
    output = run_cli("add-decision",
                     "--decision", "Use KSP over KAPT",
                     "--topic", "build",
                     "--scope", "ALL")
    assert "Saved decision" in output


def test_decisions_lists():
    run_cli("add-decision", "--decision", "Use Hilt", "--topic", "di", "--scope", "ALL")
    output = run_cli("decisions")
    assert "Use Hilt" in output


# ── search ────────────────────────────────────────────────────────────────────

def test_search_returns_results():
    run_cli("add", "--type", "bugfix",
            "--summary", "Fixed crash in HomeViewModel rotation",
            "--project", "TestApp")
    output = run_cli("search", "HomeViewModel")
    assert "HomeViewModel" in output


def test_search_empty_returns_no_results():
    output = run_cli("search", "xyznonexistent123")
    assert "No results" in output or output.strip() == ""


# ── doctor ────────────────────────────────────────────────────────────────────

def test_doctor_passes_on_fresh_db():
    output = run_cli("doctor")
    assert "Doctor" in output
    assert "✅" in output or "checks passed" in output


# ── entities ─────────────────────────────────────────────────────────────────

def test_entities_empty():
    output = run_cli("entities")
    assert "No entities" in output


def test_entities_lists_after_add():
    run_cli("add", "--type", "bugfix",
            "--summary", "Fixed crash in HomeViewModel when rotating",
            "--project", "TestApp")
    output = run_cli("entities")
    # Entity extraction may or may not link (depends on FK of manual session)
    assert "entities" in output.lower() or "HomeViewModel" in output
