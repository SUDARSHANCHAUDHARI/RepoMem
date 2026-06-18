"""
Tests for optional semantic search.

The real embedding path needs the `sentence-transformers` extra (+ a model
download), so it is guarded with importorskip. The routing and graceful-fallback
behaviour — the parts that protect the zero-dependency default — are tested
unconditionally via monkeypatching.
"""
import os
import sys
from io import StringIO

import pytest

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


def _seed(summary, detail=""):
    from repomem.cli import main
    old_argv = sys.argv
    sys.argv = ["repomem", "add", "--type", "learning", "--summary", summary, "--detail", detail]
    try:
        try:
            main()
        except SystemExit:
            pass
    finally:
        sys.argv = old_argv


def test_is_available_returns_bool():
    from repomem import semantic
    assert isinstance(semantic.is_available(), bool)


def test_unavailable_falls_back_to_fts(monkeypatch, capsys):
    """semantic=True with the extra missing must still return FTS5 results + a hint."""
    from repomem import semantic, search as search_mod
    monkeypatch.setattr(semantic, "is_available", lambda: False)
    _seed("token refresh bug in the auth layer")

    results = search_mod.search("auth", semantic=True)
    assert any("auth" in r.summary for r in results)        # FTS5 still worked
    assert "repomem[semantic]" in capsys.readouterr().err   # user was told why


def test_semantic_routing_when_available(monkeypatch):
    """When available, search() must delegate to semantic_search (no FTS5)."""
    from repomem import semantic, search as search_mod
    from repomem.models import SearchResult

    sentinel = [SearchResult(id=99, project="TestApp", type="learning", topic="",
                             summary="SEMANTIC HIT", date="2026-06-18",
                             confidence=1.0, detail="")]
    monkeypatch.setattr(semantic, "is_available", lambda: True)
    monkeypatch.setattr(semantic, "semantic_search",
                        lambda *a, **k: sentinel)

    results = search_mod.search("anything", semantic=True)
    assert results == sentinel


def test_semantic_errors_fall_back_to_fts(monkeypatch):
    """An embedding error must degrade to FTS5, never crash the search."""
    from repomem import semantic, search as search_mod
    monkeypatch.setattr(semantic, "is_available", lambda: True)
    monkeypatch.setattr(semantic, "semantic_search",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    _seed("database migration notes")

    results = search_mod.search("migration", semantic=True)
    assert any("migration" in r.summary for r in results)


def test_cosine_is_dot_product():
    from repomem import semantic
    assert semantic._cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert semantic._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_real_embedding_path():
    """Only runs where the optional extra (and model) are actually installed."""
    pytest.importorskip("sentence_transformers")
    from repomem import semantic
    _seed("Kotlin coroutine cancellation", "structured concurrency on Android")
    _seed("SwiftUI navigation stack", "type-safe routing on iOS")

    hits = semantic.semantic_search("how do I cancel async work?", limit=2)
    assert hits, "semantic search returned no results with the extra installed"
    assert hits[0].summary == "Kotlin coroutine cancellation"
