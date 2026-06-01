"""Smoke tests for web viewer (T23) — tests page renderers directly."""
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


def seed_db():
    from repomem.db import save_session, save_observation, save_decision, save_pending
    from repomem.models import Session, Observation, Decision, Pending

    s = Session(project="MyApp", repo_path="/tmp")
    save_session(s)
    save_observation(Observation(
        session_id=s.id, project="MyApp", type="bugfix",
        summary="Fixed crash in UserRepository on rotation",
        topic="viewmodel", created_at=int(time.time()),
    ))
    save_observation(Observation(
        session_id=s.id, project="MyApp", type="warning",
        summary="Never use force unwrap in production",
        topic="kotlin", created_at=int(time.time()),
    ))
    save_decision(Decision(scope="ALL", topic="di", decision="Use Hilt for DI"))
    save_pending(Pending(project="MyApp", task="Add Room migration tests", priority="P1"))
    return s


import importlib.util

def get_viewer():
    spec = importlib.util.spec_from_file_location(
        "web_viewer",
        os.path.join(src, "server", "web_viewer.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dashboard_renders(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    seed_db()
    viewer = get_viewer()
    html = viewer.page_dashboard()
    assert "RepoMem" in html
    assert "MyApp" in html
    assert "Observations" in html


def test_dashboard_empty_db():
    viewer = get_viewer()
    html = viewer.page_dashboard()
    assert "RepoMem" in html
    assert "0" in html


def test_observations_page():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_observations()
    assert "UserRepository" in html
    assert "bugfix" in html


def test_observations_project_filter():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_observations(project="MyApp")
    assert "MyApp" in html
    assert "UserRepository" in html


def test_decisions_page():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_decisions()
    assert "Use Hilt for DI" in html
    assert "ALL" in html


def test_pending_page():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_pending()
    assert "Add Room migration tests" in html
    assert "P1" in html


def test_errors_page_empty():
    viewer = get_viewer()
    html = viewer.page_errors()
    assert "Errors" in html
    assert "No unresolved errors" in html


def test_projects_page():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_projects()
    assert "MyApp" in html


def test_search_page():
    seed_db()
    viewer = get_viewer()
    html = viewer.page_observations(query="UserRepository")
    assert "UserRepository" in html


def test_page_has_nav_links():
    viewer = get_viewer()
    html = viewer.page_dashboard()
    for link in ["/observations", "/decisions", "/pending", "/errors", "/projects"]:
        assert link in html


def test_badge_helper():
    viewer = get_viewer()
    badge = viewer._badge("bugfix")
    assert "bugfix" in badge
    assert "badge" in badge
