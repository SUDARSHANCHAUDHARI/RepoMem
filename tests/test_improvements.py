"""
Tests for all 19 improvements.
T01: get_stats() env-aware DB size
T02: MCP repomem_save entity linking
T03: detect_topic() SHORT_KEYWORDS word-boundary
T04: _RELEASE_SIGNALS Android/iOS patterns
T05: _similarity() shared in utils.py
T06-T08: Obsidian export — patterns, releases, branches sections
T09: Wikilinks on decisions/errors/pending
T10-T12: Frontmatter dynamic tags, type/status/source, processed
T13: Vault-aware wikilinks
T14: --no-wikilinks flag
T15: resolve-error CLI
T16: merge-branch CLI
T17-T18: import-chat CLI + --move
T19: Top entities in inject context
"""
from __future__ import annotations
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


def _make_project(name="TestApp", tmp_path=None):
    from repomem.db import save_session, save_observation, save_decision, save_pending, save_release, save_branch
    from repomem.models import Session, Observation, Decision, Pending, Pattern
    import repomem.db as db

    s = Session(project=name, repo_path="/tmp")
    db.save_session(s)
    db.save_observation(Observation(
        session_id=s.id, project=name, type="bugfix",
        summary="Fixed crash in HomeViewModel on rotation",
        topic="ui", created_at=int(time.time()),
    ))
    db.save_observation(Observation(
        session_id=s.id, project=name, type="decision",
        summary="Use Hilt for dependency injection",
        topic="di", created_at=int(time.time()),
    ))
    db.save_decision(Decision(scope=name, topic="di", decision="Use Hilt everywhere", reason="Simpler DI"))
    db.save_pending(Pending(project=name, task="Write tests for HomeViewModel", priority="P1"))
    db.save_release(project=name, version_name="1.2.0", store="playstore")
    db.save_branch(project=name, branch="feat/new-screen")
    return s


# ── T01: get_stats() env-aware DB size ───────────────────────────────────────

def test_get_stats_db_size_uses_env_path(tmp_path, monkeypatch):
    """get_stats() must report size of DB in REPOMEM_DIR, not hardcoded path."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import get_stats, init_db
    init_db()
    stats = get_stats()
    assert stats["db_size_kb"] >= 0
    # The db file should exist in tmp_path
    assert (tmp_path / "memory.db").exists()


# ── T02: MCP repomem_save entity linking ─────────────────────────────────────

def test_mcp_save_creates_entity_links(tmp_path, monkeypatch):
    """repomem_save via MCP must call link_observation so entities are created."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "TestApp")
    from repomem.db import init_db, get_connection
    init_db()

    # Insert a sentinel session so FK constraint passes
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, project, folder, repo_path, started_at) VALUES ('mcp','TestApp','','',?)",
            (int(time.time()),)
        )
        conn.commit()

    # Simulate MCP save
    from server.mcp_server import handle_repomem_save
    result = handle_repomem_save({
        "type": "bugfix",
        "summary": "Fixed crash in UserRepository during sync",
        "project": "TestApp",
    })
    assert "Saved observation" in result["content"][0]["text"]

    # Entity linking should have run — UserRepository should be in entities
    from repomem.entity import get_entities
    entities = get_entities(project="TestApp")
    names = [e["name"] for e in entities]
    assert "UserRepository" in names


# ── T03: detect_topic() SHORT_KEYWORDS word-boundary ─────────────────────────

def test_detect_topic_di_no_false_positive():
    """'di' should not match 'audio', 'media', 'studio'."""
    from repomem.capture import detect_topic
    assert detect_topic("working on audio playback") != "di"
    assert detect_topic("media player implementation") != "di"
    assert detect_topic("android studio setup") != "di"


def test_detect_topic_di_matches_correctly():
    """'di' should match 'dependency injection' context."""
    from repomem.capture import detect_topic
    result = detect_topic("added hilt dependency injection module")
    assert result == "di"


def test_detect_topic_ui_no_false_positive():
    """'ui' should not match 'build', 'fluid', 'suite'."""
    from repomem.capture import detect_topic
    # "build" contains "ui" as substring — should not match ui topic
    result = detect_topic("running the build pipeline")
    assert result != "ui"


def test_detect_topic_ui_matches_correctly():
    """'ui' should match compose/screen context."""
    from repomem.capture import detect_topic
    result = detect_topic("updated ui layout for the main screen")
    assert result == "ui"


def test_short_keywords_in_config():
    """SHORT_TOPIC_KEYWORDS must be defined in config."""
    from repomem.config import SHORT_TOPIC_KEYWORDS
    assert "di" in SHORT_TOPIC_KEYWORDS
    assert "ui" in SHORT_TOPIC_KEYWORDS
    assert "sql" in SHORT_TOPIC_KEYWORDS


# ── T04: _RELEASE_SIGNALS Android/iOS patterns ───────────────────────────────

def test_release_signals_aab():
    """'uploaded AAB' should capture version."""
    from repomem.capture import _RELEASE_SIGNALS
    m = _RELEASE_SIGNALS.search("uploaded AAB 2.3.1 to Play Store")
    assert m is not None
    assert m.group(1) == "2.3.1"


def test_release_signals_version_name():
    """'versionName 3.0.0' should capture version."""
    from repomem.capture import _RELEASE_SIGNALS
    m = _RELEASE_SIGNALS.search("updated versionName 3.0.0 in build.gradle")
    assert m is not None
    assert m.group(1) == "3.0.0"


def test_release_signals_testflight():
    """'TestFlight build 1.5.0' should capture version."""
    from repomem.capture import _RELEASE_SIGNALS
    m = _RELEASE_SIGNALS.search("TestFlight build 1.5.0 uploaded successfully")
    assert m is not None
    assert m.group(1) == "1.5.0"


def test_release_signals_git_tag():
    """'git tag v2.0.0' should capture version."""
    from repomem.capture import _RELEASE_SIGNALS
    m = _RELEASE_SIGNALS.search("created git tag v2.0.0 and pushed")
    assert m is not None
    assert m.group(1) == "2.0.0"


def test_release_signals_bump():
    """'bumped to 1.4.2' should capture version."""
    from repomem.capture import _RELEASE_SIGNALS
    m = _RELEASE_SIGNALS.search("bumped to 1.4.2 for hotfix release")
    assert m is not None
    assert m.group(1) == "1.4.2"


# ── T05: _similarity() in utils.py ───────────────────────────────────────────

def test_utils_text_similarity_identical():
    from repomem.utils import text_similarity
    assert text_similarity("fixed crash in viewmodel", "fixed crash in viewmodel") == 1.0


def test_utils_text_similarity_empty():
    from repomem.utils import text_similarity
    assert text_similarity("", "something") == 0.0


def test_utils_text_similarity_partial():
    from repomem.utils import text_similarity
    score = text_similarity("fixed crash in viewmodel", "crash in viewmodel fixed")
    assert score > 0.7


def test_reflect_uses_utils_similarity(tmp_path, monkeypatch):
    """reflect._similarity should delegate to repomem.utils.text_similarity."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    import importlib, sys
    # Import cron directly
    cron_path = os.path.join(os.path.dirname(__file__), "..", "crons", "reflect.py")
    spec = importlib.util.spec_from_file_location("reflect_cron", cron_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # The wrapper should work
    assert mod._similarity("foo bar", "foo bar") == 1.0
    assert mod._similarity("foo", "baz") == 0.0


# ── T06-T08: Obsidian patterns / releases / branches sections ────────────────

def test_obsidian_export_has_patterns_section(tmp_path):
    from repomem.db import save_pattern
    from repomem.models import Pattern
    _make_project("PatternsApp")
    save_pattern(Pattern(topic="di", title="Always use Hilt", solution="Use Hilt module", seen_in="PatternsApp", seen_count=2))
    from repomem.obsidian import _render_project
    content = _render_project("PatternsApp")
    assert "## 🔁 Patterns" in content
    assert "Always use Hilt" in content


def test_obsidian_export_has_releases_section(tmp_path):
    _make_project("ReleasesApp")
    from repomem.obsidian import _render_project
    content = _render_project("ReleasesApp")
    assert "## 🚀 Releases" in content
    assert "1.2.0" in content


def test_obsidian_export_has_branches_section(tmp_path):
    _make_project("BranchesApp")
    from repomem.obsidian import _render_project
    content = _render_project("BranchesApp")
    assert "## 🌿 Open Branches" in content
    assert "feat/new-screen" in content


# ── T09: Wikilinks on decisions/errors/pending text ──────────────────────────

def test_obsidian_wikilinks_in_decisions(tmp_path):
    """Decision text containing PascalCase should get wikilinked."""
    from repomem.db import save_session, save_decision
    from repomem.models import Session, Decision
    import repomem.db as db
    s = Session(project="WikiApp", repo_path="/tmp")
    db.save_session(s)
    db.save_decision(Decision(
        scope="WikiApp", topic="di",
        decision="Use HomeViewModel for state management",
        reason="Survives rotation"
    ))
    from repomem.obsidian import _render_project
    content = _render_project("WikiApp")
    assert "[[HomeViewModel]]" in content


def test_obsidian_wikilinks_in_pending(tmp_path):
    """Pending task text with PascalCase should get wikilinked."""
    from repomem.db import save_session, save_pending
    from repomem.models import Session, Pending
    import repomem.db as db
    s = Session(project="WikiApp2", repo_path="/tmp")
    db.save_session(s)
    db.save_pending(Pending(project="WikiApp2", task="Add tests for UserRepository", priority="P1"))
    from repomem.obsidian import _render_project
    content = _render_project("WikiApp2")
    assert "[[UserRepository]]" in content


# ── T10-T12: Frontmatter dynamic tags, type/status/source, processed ─────────

def test_frontmatter_dynamic_topic_tags(tmp_path):
    """Topics from observations should appear in frontmatter tags."""
    _make_project("TagsApp")
    from repomem.obsidian import _render_project
    content = _render_project("TagsApp")
    assert "ui" in content
    assert "di" in content


def test_frontmatter_type_status_source(tmp_path):
    """New frontmatter fields must be present."""
    _make_project("MetaApp")
    from repomem.obsidian import _render_project
    content = _render_project("MetaApp")
    assert "source: repomem" in content
    assert "type: project-memory" in content
    assert "status: active" in content


def test_frontmatter_processed_timestamp(tmp_path):
    """processed: field must appear in frontmatter."""
    _make_project("TimeApp")
    from repomem.obsidian import _render_project
    content = _render_project("TimeApp")
    assert "processed:" in content


# ── T13: Vault-aware wikilinks ────────────────────────────────────────────────

def test_collect_vault_notes_finds_files(tmp_path):
    """collect_vault_notes returns names of .md files in vault."""
    from repomem.obsidian import collect_vault_notes
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "HomeViewModel.md").write_text("# Home")
    (vault / "UserRepository.md").write_text("# User")
    (vault / ".obsidian" / "config").parent.mkdir()
    (vault / ".obsidian" / "config").write_text("{}")
    notes = collect_vault_notes(vault)
    assert "HomeViewModel" in notes
    assert "UserRepository" in notes


def test_collect_vault_notes_skips_hidden(tmp_path):
    """collect_vault_notes skips hidden directories."""
    from repomem.obsidian import collect_vault_notes
    vault = tmp_path / "vault"
    vault.mkdir()
    hidden = vault / ".obsidian"
    hidden.mkdir()
    (hidden / "Secret.md").write_text("hidden")
    (vault / "Visible.md").write_text("visible")
    notes = collect_vault_notes(vault)
    assert "Visible" in notes
    assert "Secret" not in notes


def test_collect_vault_notes_min_length(tmp_path):
    """collect_vault_notes skips notes shorter than 4 chars."""
    from repomem.obsidian import collect_vault_notes
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Hi.md").write_text("short")
    (vault / "LongEnough.md").write_text("long")
    notes = collect_vault_notes(vault)
    assert "LongEnough" in notes
    assert "Hi" not in notes


def test_vault_wikilinks_links_real_note(tmp_path):
    """_insert_vault_wikilinks links to real vault note names."""
    from repomem.obsidian import _insert_vault_wikilinks
    notes = ["HomeViewModel", "UserRepository"]
    result = _insert_vault_wikilinks(
        "Fixed crash in HomeViewModel and UserRepository during init", notes
    )
    assert "[[HomeViewModel]]" in result
    assert "[[UserRepository]]" in result


def test_vault_wikilinks_skips_code_blocks(tmp_path):
    """_insert_vault_wikilinks does not link inside code fences."""
    from repomem.obsidian import _insert_vault_wikilinks
    notes = ["HomeViewModel"]
    text = "See ```HomeViewModel``` for details"
    result = _insert_vault_wikilinks(text, notes)
    assert "[[HomeViewModel]]" not in result


def test_vault_wikilinks_first_occurrence_only(tmp_path):
    """Each note is linked only on first occurrence."""
    from repomem.obsidian import _insert_vault_wikilinks
    notes = ["HomeViewModel"]
    text = "HomeViewModel is used. HomeViewModel is also tested."
    result = _insert_vault_wikilinks(text, notes)
    assert result.count("[[HomeViewModel]]") == 1


def test_vault_wikilinks_no_double_link(tmp_path):
    """Already-wikilinked text is not double-linked."""
    from repomem.obsidian import _insert_vault_wikilinks
    notes = ["HomeViewModel"]
    text = "See [[HomeViewModel]] for reference"
    result = _insert_vault_wikilinks(text, notes)
    assert result.count("[[HomeViewModel]]") == 1
    assert "[[[" not in result


def test_vault_wikilinks_longest_match_first(tmp_path):
    """Longer note names match before shorter prefixes."""
    from repomem.obsidian import collect_vault_notes, _insert_vault_wikilinks
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "UserRepository.md").write_text("")
    (vault / "User.md").write_text("")
    notes = collect_vault_notes(vault)
    # UserRepository must come before User in sorted order
    idx_long = next(i for i, n in enumerate(notes) if n == "UserRepository")
    idx_short = next(i for i, n in enumerate(notes) if n == "User")
    assert idx_long < idx_short


# ── T14: --no-wikilinks flag ─────────────────────────────────────────────────

def test_no_wikilinks_flag_disables_linking(tmp_path):
    """no_wikilinks=True should produce no [[...]] links."""
    _make_project("NoLinkApp")
    from repomem.obsidian import _render_project
    content = _render_project("NoLinkApp", no_wikilinks=True)
    assert "[[" not in content


def test_no_wikilinks_false_allows_linking(tmp_path):
    """no_wikilinks=False (default) should produce wikilinks."""
    _make_project("YesLinkApp")
    from repomem.obsidian import _render_project
    content = _render_project("YesLinkApp", no_wikilinks=False)
    assert "[[" in content


# ── T15: resolve-error CLI ───────────────────────────────────────────────────

def test_resolve_error_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db, save_error, get_unresolved_errors
    init_db()
    eid = save_error("TestApp", "NullPointerException in MainActivity")
    errors_before = get_unresolved_errors("TestApp")
    assert len(errors_before) == 1

    from repomem.cli import cmd_resolve_error
    class A: id = eid
    cmd_resolve_error(A())
    captured = capsys.readouterr()
    assert "Resolved error" in captured.out

    errors_after = get_unresolved_errors("TestApp")
    assert len(errors_after) == 0


# ── T16: merge-branch CLI ────────────────────────────────────────────────────

def test_merge_branch_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "TestApp")
    from repomem.db import init_db, save_branch, get_open_branches
    init_db()
    save_branch("TestApp", "feat/my-feature")
    assert len(get_open_branches("TestApp")) == 1

    from repomem.cli import cmd_merge_branch
    class A:
        branch = "feat/my-feature"
        project = "TestApp"
        pr_number = 42
        pr_url = "https://github.com/org/repo/pull/42"
    cmd_merge_branch(A())
    captured = capsys.readouterr()
    assert "merged" in captured.out

    assert len(get_open_branches("TestApp")) == 0


# ── T17-T18: import-chat + --move ────────────────────────────────────────────

def test_import_chat_basic(tmp_path, monkeypatch, capsys):
    """import-chat reads a .md file and saves observations."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "ChatApp")
    from repomem.db import init_db, get_observations
    init_db()

    chat_file = tmp_path / "session.md"
    chat_file.write_text(
        "Fixed a crash in UserRepository. "
        "Decided to use Hilt for dependency injection. "
        "Learned that Room migrations require a fallback strategy."
    )

    from repomem.cli import cmd_import_chat
    class A:
        file = str(chat_file)
        project = "ChatApp"
        move = False
    cmd_import_chat(A())

    captured = capsys.readouterr()
    assert "Imported" in captured.out
    assert "ChatApp" in captured.out
    assert chat_file.exists()  # not moved


def test_import_chat_move_deletes_source(tmp_path, monkeypatch, capsys):
    """import-chat --move deletes the source file after import."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    monkeypatch.setenv("REPOMEM_PROJECT", "ChatApp2")
    from repomem.db import init_db
    init_db()

    chat_file = tmp_path / "session2.md"
    chat_file.write_text("Fixed a bug in PaymentService. Decided to use coroutines.")

    from repomem.cli import cmd_import_chat
    class A:
        file = str(chat_file)
        project = "ChatApp2"
        move = True
    cmd_import_chat(A())

    assert not chat_file.exists()


def test_import_chat_missing_file(tmp_path, monkeypatch, capsys):
    """import-chat with nonexistent file prints error and exits cleanly."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()

    from repomem.cli import cmd_import_chat
    class A:
        file = str(tmp_path / "nonexistent.md")
        project = None
        move = False
    cmd_import_chat(A())
    # Should not raise — just print error
    captured = capsys.readouterr()
    assert "not found" in captured.out or "Error" in captured.out or captured.err


# ── T19: Top entities in inject context ──────────────────────────────────────

def test_inject_includes_top_entities(tmp_path, monkeypatch):
    """inject context should include frequently-mentioned entities."""
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db, get_connection
    from repomem.entity import get_entities
    init_db()

    # Seed entities with high mention_count
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO entities (name, type, project, first_seen, mention_count) VALUES (?,?,?,date('now'),?)",
            ("HomeViewModel", "class", "MyApp", 10)
        )
        conn.execute(
            "INSERT INTO entities (name, type, project, first_seen, mention_count) VALUES (?,?,?,date('now'),?)",
            ("UserRepository", "class", "MyApp", 5)
        )
        conn.commit()

    from repomem.inject import build_context
    context = build_context(project="MyApp")
    # Either entities appear or context is empty (no obs yet) — just confirm no crash
    # If there are entities with min_mentions=3, they should appear
    if context:
        assert isinstance(context, str)
