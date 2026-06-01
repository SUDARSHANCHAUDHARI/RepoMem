"""Tests for graphify integration (T25)."""
import os
import sys
import json
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


def make_fake_graph(tmp_path: Path, god_node_edges: int = 15) -> Path:
    """Write a fake graphify-out/graph.json for testing."""
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    graph = {
        "nodes": [
            {"id": "UserRepository.kt", "label": "UserRepository", "type": "class", "community": "1"},
            {"id": "PaymentService.kt", "label": "PaymentServiceRepository", "type": "class", "community": "1"},
            {"id": "AppController.kt", "label": "MainActivity", "type": "class", "community": "2"},
            {"id": "build.gradle.kts", "label": "build.gradle.kts", "type": "file", "community": "3"},
        ],
        "edges": [
            # Make UserRepository a god node with many edges
            *[{"source": "UserRepository.kt", "target": f"dep_{i}.kt"} for i in range(god_node_edges)],
            {"source": "AppController.kt", "target": "UserRepository.kt"},
            {"source": "PaymentService.kt", "target": "UserRepository.kt"},
        ]
    }
    graph_path = graph_dir / "graph.json"
    graph_path.write_text(json.dumps(graph))
    return tmp_path


from repomem.graphify import (
    load_graph, get_god_nodes, get_communities,
    enrich_observation, build_graph_context, analyze
)


def test_load_graph_finds_json(tmp_path):
    make_fake_graph(tmp_path)
    graph = load_graph(repo_path=str(tmp_path))
    assert graph is not None
    assert "nodes" in graph
    assert "edges" in graph


def test_load_graph_returns_none_when_missing(tmp_path):
    graph = load_graph(repo_path=str(tmp_path))
    assert graph is None


def test_get_god_nodes_identifies_high_edge_nodes(tmp_path):
    make_fake_graph(tmp_path, god_node_edges=15)
    graph = load_graph(repo_path=str(tmp_path))
    god_nodes = get_god_nodes(graph, threshold=10)
    assert len(god_nodes) >= 1
    assert god_nodes[0]["label"] == "UserRepository"
    assert god_nodes[0]["edge_count"] >= 15


def test_get_god_nodes_threshold_filters(tmp_path):
    make_fake_graph(tmp_path, god_node_edges=5)
    graph = load_graph(repo_path=str(tmp_path))
    # With threshold=10, a node with 5 edges should not appear
    god_nodes = get_god_nodes(graph, threshold=10)
    assert all(n["edge_count"] >= 10 for n in god_nodes)


def test_get_communities_groups_nodes(tmp_path):
    make_fake_graph(tmp_path)
    graph = load_graph(repo_path=str(tmp_path))
    communities = get_communities(graph)
    assert len(communities) >= 2
    assert any("UserRepository.kt" in v for v in communities.values())


def test_enrich_observation_tags_god_node(tmp_path):
    make_fake_graph(tmp_path, god_node_edges=15)
    graph = load_graph(repo_path=str(tmp_path))

    from repomem.db import save_session, save_observation
    from repomem.models import Session, Observation

    s = Session(project="TestApp", repo_path="/tmp")
    save_session(s)
    obs = Observation(
        session_id=s.id, project="TestApp", type="bugfix",
        summary="Fixed crash in UserRepository when rotating",
        created_at=int(time.time()),
    )
    obs_id = save_observation(obs)

    found = enrich_observation(obs_id, "TestApp", obs.summary, graph)
    assert "UserRepository" in found


def test_build_graph_context_returns_god_nodes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_fake_graph(tmp_path, god_node_edges=15)
    ctx = build_graph_context("TestApp", repo_path=str(tmp_path))
    assert "GOD NODES" in ctx
    assert "UserRepository" in ctx


def test_build_graph_context_empty_when_no_graph(tmp_path):
    ctx = build_graph_context("TestApp", repo_path=str(tmp_path))
    assert ctx == ""


def test_analyze_returns_summary(tmp_path):
    make_fake_graph(tmp_path, god_node_edges=15)
    result = analyze("TestApp", repo_path=str(tmp_path), threshold=10)
    assert result["nodes"] == 4
    assert len(result["god_nodes"]) >= 1
    assert result["communities"] >= 2


def test_analyze_error_when_no_graph(tmp_path):
    result = analyze("TestApp", repo_path=str(tmp_path))
    assert "error" in result
