"""Tests for entity extraction and linking."""
import os
import sys
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


from repomem.entity import extract_entities, link_observation, get_entities, get_observations_for_entity


def test_extract_pascal_class():
    entities = extract_entities("Fixed crash in HomeViewModel when state is null")
    names = [e[0] for e in entities]
    assert "HomeViewModel" in names
    types = {e[0]: e[1] for e in entities}
    assert types["HomeViewModel"] == "class"


def test_extract_known_library():
    entities = extract_entities("Using Hilt for dependency injection")
    names = [e[0].lower() for e in entities]
    assert "hilt" in names


def test_extract_file():
    entities = extract_entities("Fixed issue in build.gradle.kts configuration")
    names = [e[0] for e in entities]
    assert "build.gradle.kts" in names


def test_no_false_positives_on_short_words():
    entities = extract_entities("the db is ok")
    # Single-word non-pascal, no known lib match should not produce pascal entities
    pascal = [e for e in entities if e[1] == "class"]
    assert len(pascal) == 0


def test_link_observation_creates_entity():
    import time
    from repomem import db
    from repomem.models import Session, Observation

    session = Session(project="TestApp", repo_path="/tmp")
    db.save_session(session)

    obs = Observation(
        session_id=session.id,
        project="TestApp",
        type="bugfix",
        summary="Fixed crash in HomeViewModel when DreamWeave state null",
        created_at=int(time.time()),
    )
    obs_id = db.save_observation(obs)
    count = link_observation(obs_id, "TestApp", obs.summary)
    assert count > 0

    entities = get_entities(project="TestApp")
    names = [e["name"] for e in entities]
    assert "HomeViewModel" in names or "DreamWeave" in names


def test_get_observations_for_entity():
    import time
    from repomem import db
    from repomem.models import Session, Observation

    session = Session(project="TestApp", repo_path="/tmp")
    db.save_session(session)

    obs = Observation(
        session_id=session.id,
        project="TestApp",
        type="warning",
        summary="SpendWise ViewModel leaks memory on rotation",
        created_at=int(time.time()),
    )
    obs_id = db.save_observation(obs)
    link_observation(obs_id, "TestApp", obs.summary)

    results = get_observations_for_entity("SpendWise")
    assert len(results) >= 1
    assert any("SpendWise" in r["summary"] for r in results)


def test_mention_count_increments():
    import time
    from repomem import db
    from repomem.models import Session, Observation

    session = Session(project="TestApp", repo_path="/tmp")
    db.save_session(session)

    for _ in range(3):
        obs = Observation(
            session_id=session.id,
            project="TestApp",
            type="learning",
            summary="RainLock handles edge case in permission flow",
            created_at=int(time.time()),
        )
        obs_id = db.save_observation(obs)
        link_observation(obs_id, "TestApp", obs.summary)

    entities = get_entities()
    rainlock = next((e for e in entities if e["name"] == "RainLock"), None)
    assert rainlock is not None
    assert rainlock["mention_count"] == 3
