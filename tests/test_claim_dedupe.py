"""Tests for pending-task claim / release / handoff and write-time duplicate checks (schema v4)."""
from __future__ import annotations
import sqlite3
import sys
from io import StringIO

import pytest


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "TestApp")
    monkeypatch.delenv("REPOMEM_AGENT", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    from repomem.db import init_db
    from repomem.cli import _ensure_manual_session
    init_db()
    _ensure_manual_session("TestApp")  # observations reference a session row
    yield tmp_path


def run_cli(*args, expect_exit=0):
    from repomem.cli import main
    old_argv, old_stdout = sys.argv, sys.stdout
    sys.argv = ["repomem"] + list(args)
    sys.stdout = out = StringIO()
    try:
        try:
            main()
        except SystemExit as e:
            if e.code != expect_exit:
                raise
    finally:
        sys.argv, sys.stdout = old_argv, old_stdout
    return out.getvalue()


def new_task(text="Ship the release", project="TestApp"):
    from repomem import db
    from repomem.models import Pending
    return db.add_pending(Pending(project=project, task=text))


def obs(summary, project="TestApp", obs_type="learning"):
    from repomem.models import Observation
    return Observation(session_id="manual", project=project, folder="", type=obs_type,
                       topic="", summary=summary, detail="", date="2026-11-08", created_at=1)


# ── duplicate checks ──────────────────────────────────────────────────────────

def test_pending_duplicate_returns_existing_id():
    first, created = new_task("Ship the release")
    again, created_again = new_task("  ship   the RELEASE. ")
    assert created and not created_again
    assert again == first


def test_pending_same_text_other_project_or_after_resolve_is_new():
    from repomem import db
    first, _ = new_task("Ship the release")
    other, created = new_task("Ship the release", project="OtherApp")
    assert created and other != first
    db.resolve_pending(first)
    reopened, created = new_task("Ship the release")
    assert created and reopened != first


def test_observation_duplicate_raises_seen_count():
    from repomem import db
    first, created = db.add_observation(obs("Room migration needs a fallback"))
    again, created_again = db.add_observation(obs("room migration needs a fallback!"))
    assert created and not created_again and again == first
    with db.db() as conn:
        assert conn.execute("SELECT seen_count FROM observations WHERE id=?", (first,)).fetchone()[0] == 2
    other_type, created = db.add_observation(obs("Room migration needs a fallback", obs_type="bugfix"))
    assert created and other_type != first


def test_save_wrappers_still_return_ids():
    from repomem import db
    from repomem.models import Pending
    pid = db.save_pending(Pending(project="TestApp", task="Wrapper task"))
    assert db.save_pending(Pending(project="TestApp", task="wrapper task")) == pid
    oid = db.save_observation(obs("Wrapper obs"))
    assert db.save_observation(obs("Wrapper obs")) == oid


def test_cli_add_pending_reports_duplicate():
    assert "Added pending task" in run_cli("add-pending", "Write tests", "--project", "TestApp")
    assert "Already pending as #" in run_cli("add-pending", "write tests", "--project", "TestApp")


# ── claim / release / handoff ─────────────────────────────────────────────────

def test_claim_release_cycle():
    from repomem import db
    pid, _ = new_task()
    assert db.claim_pending(pid, "session-a") == (True, "session-a")
    assert db.claim_pending(pid, "session-b") == (False, "session-a")
    assert db.claim_pending(pid, "session-a") == (True, "session-a")  # re-claim by holder is fine
    assert db.release_pending(pid, "session-b") is False
    assert db.release_pending(pid, "session-a") is True
    assert db.claim_pending(pid, "session-b") == (True, "session-b")


def test_stale_claim_can_be_taken_over():
    from repomem import db
    pid, _ = new_task()
    db.claim_pending(pid, "session-a")
    with db.db() as conn:
        conn.execute("UPDATE pending SET claimed_at='2000-01-01T00:00:00+00:00' WHERE id=?", (pid,))
    assert db.claim_pending(pid, "session-b") == (True, "session-b")


def test_claim_missing_or_resolved_raises():
    from repomem import db
    with pytest.raises(KeyError):
        db.claim_pending(9999, "x")
    pid, _ = new_task()
    db.resolve_pending(pid)
    with pytest.raises(ValueError):
        db.claim_pending(pid, "x")


def test_force_release_and_handoff():
    from repomem import db
    pid, _ = new_task()
    db.claim_pending(pid, "session-a")
    assert db.release_pending(pid) is True  # no holder given: any claim is dropped
    db.claim_pending(pid, "session-a")
    db.handoff_pending(pid, "Build passes; upload is left", to="session-b")
    row = [p for p in db.get_pending() if p["id"] == pid][0]
    assert (row["claimed_by"], row["handoff_note"]) == ("session-b", "Build passes; upload is left")
    db.handoff_pending(pid, "Parked")
    row = [p for p in db.get_pending() if p["id"] == pid][0]
    assert row["claimed_by"] is None and row["claimed_at"] is None and row["handoff_note"] == "Parked"
    with pytest.raises(KeyError):
        db.handoff_pending(9999, "x")


def test_cli_claim_flow_and_listing():
    pid, _ = new_task("Upload bundle")
    assert f"Claimed #{pid} as alpha" in run_cli("claim", str(pid), "--as", "alpha")
    assert "is claimed by alpha" in run_cli("claim", str(pid), "--as", "beta", expect_exit=1)
    listing = run_cli("pending")
    assert f"#{pid}" in listing and "claimed by alpha" in listing
    assert "Nothing to release" in run_cli("release", str(pid), "--as", "beta")
    run_cli("handoff", str(pid), "Signed AAB in build/outputs", "--to", "beta")
    listing = run_cli("pending")
    assert "claimed by beta" in listing and "handoff: Signed AAB in build/outputs" in listing
    assert f"Released #{pid}" in run_cli("release", str(pid), "--force")


def test_cli_claim_uses_environment_name(monkeypatch):
    monkeypatch.setenv("REPOMEM_AGENT", "env-agent")
    pid, _ = new_task("Env claim")
    assert "as env-agent" in run_cli("claim", str(pid))


# ── migration ─────────────────────────────────────────────────────────────────

def test_v3_database_migrates_and_keeps_rows(temp_db):
    from repomem import db
    path = temp_db / "memory.db"
    conn = sqlite3.connect(path)
    conn.execute("DROP TABLE pending")
    conn.execute("""CREATE TABLE pending (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL,
                    task TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'P2', created_at TEXT NOT NULL,
                    resolved_at TEXT, session_id TEXT NOT NULL DEFAULT '')""")
    conn.execute("INSERT INTO pending (project, task, created_at) VALUES ('TestApp', 'Old task', '2026-01-01')")
    conn.execute("UPDATE schema_version SET version=3")
    conn.commit()
    conn.close()
    db.init_db()
    with db.db() as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(pending)")}
        version = c.execute("SELECT version FROM schema_version").fetchone()[0]
    assert {"claimed_by", "claimed_at", "handoff_note"} <= cols and version == db.SCHEMA_VERSION == 4
    old = [p for p in db.get_pending() if p["task"] == "Old task"][0]
    assert db.claim_pending(old["id"], "after-migration") == (True, "after-migration")


# ── MCP ───────────────────────────────────────────────────────────────────────

def test_mcp_tools_listed_and_handlers_work():
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "server"))
    import mcp_server as m
    names = {t["name"] for t in m.TOOLS} if hasattr(m, "TOOLS") else set(m.HANDLERS)
    assert {"repomem_claim", "repomem_release", "repomem_handoff"} <= set(m.HANDLERS) and names
    pid, _ = new_task("MCP task")
    text = lambda r: r["content"][0]["text"]
    assert "Claimed" in text(m.handle_repomem_claim({"id": pid, "as": "mcp-a"}))
    assert "claimed by mcp-a" in text(m.handle_repomem_claim({"id": pid, "as": "mcp-b"}))
    assert "claim passed to mcp-b" in text(m.handle_repomem_handoff({"id": pid, "note": "n", "to": "mcp-b"}))
    assert "Released" in text(m.handle_repomem_release({"id": pid, "as": "mcp-b"}))
    assert "Already pending as" in text(m.handle_repomem_add_pending({"task": "mcp task", "project": "TestApp"}))
