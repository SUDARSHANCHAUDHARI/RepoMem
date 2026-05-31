"""Tests for Obsidian sync (T19)."""
import os
import sys
import time
import pytest
from pathlib import Path

src = os.path.join(os.path.dirname(__file__), "..")
if src not in sys.path:
    sys.path.insert(0, src)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    yield


def make_project(name="DreamWeave"):
    from repomem.db import save_session, save_observation, save_decision, save_pending
    from repomem.models import Session, Observation, Decision, Pending

    s = Session(project=name, repo_path="/tmp")
    save_session(s)

    save_observation(Observation(
        session_id=s.id, project=name, type="bugfix",
        summary=f"Fixed crash in HomeViewModel on rotation",
        topic="viewmodel", created_at=int(time.time()),
    ))
    save_observation(Observation(
        session_id=s.id, project=name, type="warning",
        summary="Never use force unwrap in production code",
        topic="kotlin", created_at=int(time.time()),
    ))
    save_decision(Decision(scope=name, topic="di", decision="Use Hilt for injection"))
    save_pending(Pending(project=name, task="Add unit tests for ViewModel", priority="P1"))
    return s


from repomem.obsidian import export_project, export_all, _add_wikilinks, _render_project


def test_add_wikilinks_wraps_pascal():
    result = _add_wikilinks("Fixed crash in HomeViewModel and SpendWise")
    assert "[[HomeViewModel]]" in result
    assert "[[SpendWise]]" in result


def test_add_wikilinks_leaves_normal_words():
    result = _add_wikilinks("the fix was simple")
    assert "[[" not in result


def test_render_project_contains_sections():
    make_project("DreamWeave")
    content = _render_project("DreamWeave")
    assert "# DreamWeave" in content
    assert "## ⚡ Decisions" in content
    assert "Use Hilt for injection" in content
    assert "## 📋 Pending" in content
    assert "Add unit tests for ViewModel" in content
    assert "## 📝 Observations" in content
    assert "HomeViewModel" in content


def test_render_project_has_frontmatter():
    make_project("DreamWeave")
    content = _render_project("DreamWeave")
    assert content.startswith("---")
    assert "project: DreamWeave" in content
    assert "tags: [repomem, project-memory]" in content


def test_render_project_has_wikilinks():
    make_project("DreamWeave")
    content = _render_project("DreamWeave")
    assert "[[HomeViewModel]]" in content


def test_export_project_writes_file(tmp_path):
    make_project("RainLock")
    vault = tmp_path / "obsidian"
    path = export_project("RainLock", vault=vault)
    assert path.exists()
    assert path.name == "RainLock.md"
    text = path.read_text()
    assert "# RainLock" in text


def test_export_all_writes_multiple(tmp_path):
    make_project("AppA")
    make_project("AppB")
    vault = tmp_path / "obsidian"
    paths = export_all(vault=vault)
    names = [p.name for p in paths]
    assert "AppA.md" in names
    assert "AppB.md" in names
    # Index file
    assert (vault / "_index.md").exists()
    index = (vault / "_index.md").read_text()
    assert "[[AppA]]" in index
    assert "[[AppB]]" in index
