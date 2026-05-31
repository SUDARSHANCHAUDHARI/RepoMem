"""Tests for TUI data loading and key handling logic (no curses terminal needed)."""
import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch

src = os.path.join(os.path.dirname(__file__), "..")
if src not in sys.path:
    sys.path.insert(0, src)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    from repomem.db import init_db
    init_db()
    yield


def seed():
    from repomem.db import save_session, save_observation, save_pending, save_decision
    from repomem.models import Session, Observation, Pending, Decision

    s = Session(project="DreamWeave", repo_path="/tmp")
    save_session(s)
    save_observation(Observation(
        session_id=s.id, project="DreamWeave", type="bugfix",
        summary="Fixed crash in HomeViewModel on rotation",
        created_at=int(time.time()),
    ))
    save_observation(Observation(
        session_id=s.id, project="DreamWeave", type="warning",
        summary="Never use force unwrap",
        created_at=int(time.time()),
    ))
    save_pending(Pending(project="DreamWeave", task="Write migration tests", priority="P1",
                         session_id=s.id))
    save_decision(Decision(scope="ALL", topic="di", decision="Use Hilt for DI"))
    return s


from repomem.tui import _load_observations, _load_pending, _load_decisions, _load_errors


def test_load_observations_returns_list():
    seed()
    obs = _load_observations()
    assert len(obs) >= 2
    assert all("summary" in o for o in obs)


def test_load_observations_query_filter():
    seed()
    obs = _load_observations(query="HomeViewModel")
    assert any("HomeViewModel" in o["summary"] for o in obs)


def test_load_pending_returns_tasks():
    seed()
    items = _load_pending()
    assert any("migration" in i["task"] for i in items)


def test_load_decisions_returns_decisions():
    seed()
    items = _load_decisions()
    assert any("Hilt" in i["decision"] for i in items)


def test_load_errors_empty():
    items = _load_errors()
    assert items == []


def test_tui_item_line_observations():
    seed()
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (40, 120)

    with patch("curses.start_color"), patch("curses.use_default_colors"), \
         patch("curses.init_pair"), patch("curses.color_pair", return_value=0), \
         patch("curses.curs_set"):
        from repomem.tui import TUI
        tui = TUI(stdscr)
        tui.mode = "observations"
        tui._refresh_data()

        assert len(tui.items) >= 2
        line = tui._item_line(tui.items[0])
        assert len(line) > 0


def test_tui_mode_switching():
    seed()
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (40, 120)

    with patch("curses.start_color"), patch("curses.use_default_colors"), \
         patch("curses.init_pair"), patch("curses.color_pair", return_value=0), \
         patch("curses.curs_set"):
        from repomem.tui import TUI
        tui = TUI(stdscr)
        assert tui.mode == "observations"

        tui.handle_key(ord("p"))
        assert tui.mode == "pending"

        tui.handle_key(ord("d"))
        assert tui.mode == "decisions"

        tui.handle_key(ord("e"))
        assert tui.mode == "errors"

        tui.handle_key(ord("o"))
        assert tui.mode == "observations"


def test_tui_navigation():
    seed()
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (40, 120)

    with patch("curses.start_color"), patch("curses.use_default_colors"), \
         patch("curses.init_pair"), patch("curses.color_pair", return_value=0), \
         patch("curses.curs_set"), patch("curses.KEY_DOWN", 258), \
         patch("curses.KEY_UP", 259):
        from repomem.tui import TUI
        import curses
        tui = TUI(stdscr)

        assert tui.cursor == 0
        tui.handle_key(curses.KEY_DOWN)
        assert tui.cursor == 1
        tui.handle_key(curses.KEY_UP)
        assert tui.cursor == 0


def test_tui_quit_returns_false():
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (40, 120)

    with patch("curses.start_color"), patch("curses.use_default_colors"), \
         patch("curses.init_pair"), patch("curses.color_pair", return_value=0), \
         patch("curses.curs_set"):
        from repomem.tui import TUI
        tui = TUI(stdscr)
        result = tui.handle_key(ord("q"))
        assert result is False


def test_tui_search_mode():
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (40, 120)

    with patch("curses.start_color"), patch("curses.use_default_colors"), \
         patch("curses.init_pair"), patch("curses.color_pair", return_value=0), \
         patch("curses.curs_set"):
        from repomem.tui import TUI
        tui = TUI(stdscr)

        tui.handle_key(ord("/"))
        assert tui.search_mode is True

        tui.handle_key(ord("H"))
        tui.handle_key(ord("i"))
        assert tui.search_query == "Hi"

        tui.handle_key(27)  # ESC
        assert tui.search_mode is False
        assert tui.search_query == ""
