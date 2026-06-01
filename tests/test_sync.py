"""Tests for git sync (T22)."""
import os
import sys
import json
import time
import pytest
from pathlib import Path
from datetime import date

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


def make_obs(session_id, project="TestApp", summary="test obs"):
    from repomem.db import save_observation
    from repomem.models import Observation
    obs = Observation(
        session_id=session_id, project=project,
        type="bugfix", summary=summary, created_at=int(time.time()),
    )
    return save_observation(obs)


from repomem.sync import export_sync, import_sync, sync_status, _machine_id


def test_export_creates_chunk(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()

    s = make_session()
    make_obs(s.id, summary="Fixed crash in UserRepository")

    stats = export_sync(commit=False)
    assert stats["observations"] == 1
    chunk_file = Path(stats["chunk_file"])
    assert chunk_file.exists()

    chunk = json.loads(chunk_file.read_text())
    assert chunk["machine"] == _machine_id()
    assert len(chunk["observations"]) == 1
    assert chunk["observations"][0]["summary"] == "Fixed crash in UserRepository"


def test_export_watermark_increments(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()

    s = make_session()
    make_obs(s.id, summary="First obs")
    stats1 = export_sync(commit=False)
    assert stats1["observations"] == 1

    make_obs(s.id, summary="Second obs")
    stats2 = export_sync(commit=False)
    assert stats2["observations"] == 1  # only the new one


def test_import_from_peer_chunk(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db, get_observations
    init_db()

    # Write a fake peer chunk
    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    peer_chunk = {
        "machine": "peer-machine-user",
        "exported_at": date.today().isoformat(),
        "watermark": 0,
        "observations": [{
            "session_id": "peer-session",
            "project": "PeerApp",
            "folder": "",
            "type": "learning",
            "topic": "kotlin",
            "summary": "Learned that StateFlow needs lifecycle awareness",
            "detail": "",
            "date": date.today().isoformat(),
            "created_at": int(time.time()),
            "confidence": 1.0,
            "seen_count": 1,
            "is_stale": 0,
            "is_resolved": 0,
            "is_archived": 0,
            "related_ids": "",
        }],
        "decisions": [{
            "scope": "ALL",
            "topic": "state",
            "decision": "Use StateFlow over LiveData",
            "reason": "Modern, lifecycle-safe",
            "date": date.today().isoformat(),
            "is_superseded": 0,
        }],
        "pending": [],
    }
    (sync_dir / "peer-machine-user.json").write_text(json.dumps(peer_chunk))

    stats = import_sync()
    assert stats["observations"] == 1
    assert stats["decisions"] == 1

    obs = get_observations(project="PeerApp", limit=5)
    assert any("StateFlow" in o["summary"] for o in obs)


def test_import_skips_own_machine(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db, get_observations
    init_db()

    s = make_session()
    make_obs(s.id, summary="My own observation")
    export_sync(commit=False)

    stats = import_sync()
    assert stats["skipped_own_machine"] == 1
    assert stats["observations"] == 0


def test_import_no_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db, get_observations
    init_db()

    sync_dir = tmp_path / "sync"
    sync_dir.mkdir()
    obs_data = {
        "session_id": "peer-session",
        "project": "PeerApp",
        "folder": "",
        "type": "bugfix",
        "topic": "",
        "summary": "Same observation twice",
        "detail": "",
        "date": date.today().isoformat(),
        "created_at": int(time.time()),
        "confidence": 1.0,
        "seen_count": 1,
        "is_stale": 0,
        "is_resolved": 0,
        "is_archived": 0,
        "related_ids": "",
    }
    peer_chunk = {
        "machine": "other-machine",
        "exported_at": date.today().isoformat(),
        "watermark": 0,
        "observations": [obs_data],
        "decisions": [],
        "pending": [],
    }
    (sync_dir / "other-machine.json").write_text(json.dumps(peer_chunk))

    import_sync()
    import_sync()  # second import should not duplicate

    obs = get_observations(project="PeerApp", limit=10)
    count = sum(1 for o in obs if o["summary"] == "Same observation twice")
    assert count == 1


def test_sync_status_returns_info(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()

    status = sync_status()
    assert status["machine"] == _machine_id()
    assert "last_exported_id" in status
    assert "peer_chunks" in status
