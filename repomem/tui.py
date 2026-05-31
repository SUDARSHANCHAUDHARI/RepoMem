"""
RepoMem TUI — full-screen terminal UI using curses (stdlib).

Usage: repomem tui

Keys:
  j/↓   move down          k/↑   move up
  /     search mode        Esc   exit search
  Enter open detail        q     quit
  p     switch to pending  o     switch to observations
  d     switch to decisions e     switch to errors
  r     refresh
"""
from __future__ import annotations
import curses
import os
import sys
import textwrap
from typing import Optional

REPOMEM_INSTALL = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_observations(query: str = "", project: str = "") -> list[dict]:
    from repomem.db import db as _db, init_db
    init_db()
    if query:
        from repomem.search import search
        results = search(query, project=project or None, limit=100)
        return [{"type": r.type, "project": r.project, "topic": r.topic,
                 "summary": r.summary, "date": r.date, "detail": r.detail} for r in results]
    with _db() as conn:
        if project:
            rows = conn.execute("""
                SELECT type, project, topic, summary, date, detail
                FROM observations WHERE project=? AND is_archived=0
                ORDER BY created_at DESC LIMIT 200
            """, (project,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT type, project, topic, summary, date, detail
                FROM observations WHERE is_archived=0
                ORDER BY created_at DESC LIMIT 200
            """).fetchall()
    return [dict(r) for r in rows]


def _load_pending() -> list[dict]:
    from repomem.db import get_pending, init_db
    init_db()
    return get_pending()


def _load_decisions() -> list[dict]:
    from repomem.db import get_decisions, init_db
    init_db()
    return get_decisions()


def _load_errors() -> list[dict]:
    from repomem.db import get_unresolved_errors, init_db
    init_db()
    return get_unresolved_errors()


# ── Color pairs ───────────────────────────────────────────────────────────────

def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # header
    curses.init_pair(2, curses.COLOR_GREEN, -1)    # selected / ok
    curses.init_pair(3, curses.COLOR_YELLOW, -1)   # warning / pending
    curses.init_pair(4, curses.COLOR_RED, -1)      # error
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # decision
    curses.init_pair(6, curses.COLOR_WHITE, -1)    # normal
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_CYAN)  # status bar


TYPE_COLOR = {
    "bugfix": 2, "learning": 2, "upgrade": 2, "pattern": 2,
    "warning": 3, "pending": 3,
    "error": 4,
    "decision": 5,
}


# ── TUI state ─────────────────────────────────────────────────────────────────

class TUI:
    MODES = ["observations", "pending", "decisions", "errors"]
    MODE_KEYS = {"o": "observations", "p": "pending", "d": "decisions", "e": "errors"}

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.mode = "observations"
        self.cursor = 0
        self.scroll = 0
        self.search_mode = False
        self.search_query = ""
        self.detail_mode = False
        self.items: list[dict] = []
        self._refresh_data()

    def _refresh_data(self):
        self.cursor = 0
        self.scroll = 0
        if self.mode == "observations":
            self.items = _load_observations(query=self.search_query)
        elif self.mode == "pending":
            self.items = _load_pending()
        elif self.mode == "decisions":
            self.items = _load_decisions()
        elif self.mode == "errors":
            self.items = _load_errors()

    def _item_line(self, item: dict) -> str:
        if self.mode == "observations":
            icon = {"bugfix": "🐛", "decision": "⚡", "upgrade": "⬆",
                    "warning": "⚠", "learning": "💡", "pending": "📋",
                    "pattern": "↺", "error": "✗"}.get(item.get("type", ""), "·")
            return f"{icon} [{item.get('type','?'):8s}] {item.get('project',''):16s} {item.get('summary','')[:60]}"
        elif self.mode == "pending":
            return f"[{item.get('priority','P2'):2s}] {item.get('project',''):16s} {item.get('task','')[:60]}"
        elif self.mode == "decisions":
            return f"[{item.get('scope','ALL'):12s}] [{item.get('topic',''):10s}] {item.get('decision','')[:50]}"
        elif self.mode == "errors":
            recurred = f" ×{item['recurred']}" if item.get("recurred") else ""
            return f"{'✗':2s} {item.get('project',''):16s} {item.get('error_text','')[:55]}{recurred}"
        return str(item)

    def _item_color(self, item: dict) -> int:
        if self.mode == "observations":
            return TYPE_COLOR.get(item.get("type", ""), 6)
        elif self.mode == "pending":
            return 4 if item.get("priority") == "P1" else 3 if item.get("priority") == "P2" else 6
        elif self.mode == "decisions":
            return 5
        elif self.mode == "errors":
            return 4
        return 6

    def _draw_header(self, max_y, max_x):
        title = " 🧠 RepoMem TUI "
        mode_tabs = "  ".join(
            f"[{m[0].upper()}]{m[1:]}" if m != self.mode else f"[{m.upper()}]"
            for m in self.MODES
        )
        header = f"{title} | {mode_tabs}"
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, header[:max_x - 1])
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    def _draw_status(self, max_y, max_x):
        if self.search_mode:
            status = f" / {self.search_query}_"
        else:
            count = len(self.items)
            pos = f"{self.cursor + 1}/{count}" if count else "0/0"
            status = f" {pos} | q:quit  /:search  Enter:detail  o/p/d/e:mode  r:refresh"
        self.stdscr.attron(curses.color_pair(7))
        self.stdscr.addstr(max_y - 1, 0, status[:max_x - 1].ljust(max_x - 1))
        self.stdscr.attroff(curses.color_pair(7))

    def _draw_list(self, max_y, max_x):
        list_height = max_y - 2  # header + status
        visible = self.items[self.scroll:self.scroll + list_height]

        for i, item in enumerate(visible):
            y = i + 1
            line = self._item_line(item)
            color = self._item_color(item)
            is_selected = (self.scroll + i) == self.cursor

            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_REVERSE)
            else:
                self.stdscr.attron(curses.color_pair(color))

            try:
                self.stdscr.addstr(y, 0, line[:max_x - 1].ljust(max_x - 1))
            except curses.error:
                pass

            if is_selected:
                self.stdscr.attroff(curses.color_pair(2) | curses.A_REVERSE)
            else:
                self.stdscr.attroff(curses.color_pair(color))

        if not self.items:
            msg = "  No items."
            self.stdscr.attron(curses.color_pair(6))
            try:
                self.stdscr.addstr(1, 0, msg)
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(6))

    def _draw_detail(self, max_y, max_x):
        if not self.items or self.cursor >= len(self.items):
            return
        item = self.items[self.cursor]
        self.stdscr.clear()

        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        try:
            self.stdscr.addstr(0, 0, " Detail — press any key to return ".center(max_x - 1, "─"))
        except curses.error:
            pass
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        lines = []
        for key, val in item.items():
            if val and str(val).strip():
                lines.append(f"{key}: {val}")

        row = 1
        for line in lines:
            wrapped = textwrap.wrap(line, max_x - 2) or [line]
            for wl in wrapped:
                if row >= max_y - 1:
                    break
                try:
                    self.stdscr.addstr(row, 1, wl[:max_x - 2])
                except curses.error:
                    pass
                row += 1
            if row >= max_y - 1:
                break

        self.stdscr.refresh()
        self.stdscr.getch()
        self.detail_mode = False

    def draw(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        if self.detail_mode:
            self._draw_detail(max_y, max_x)
            return
        self._draw_header(max_y, max_x)
        self._draw_list(max_y, max_x)
        self._draw_status(max_y, max_x)
        self.stdscr.refresh()

    def handle_key(self, key) -> bool:
        max_y, _ = self.stdscr.getmaxyx()
        list_height = max_y - 2

        if self.search_mode:
            if key == 27:  # ESC
                self.search_mode = False
                self.search_query = ""
                self._refresh_data()
            elif key in (10, 13, curses.KEY_ENTER):
                self.search_mode = False
                self._refresh_data()
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.search_query = self.search_query[:-1]
            elif 32 <= key <= 126:
                self.search_query += chr(key)
            return True

        if key in (ord("q"), ord("Q")):
            return False
        elif key in (ord("j"), curses.KEY_DOWN):
            if self.cursor < len(self.items) - 1:
                self.cursor += 1
                if self.cursor >= self.scroll + list_height:
                    self.scroll += 1
        elif key in (ord("k"), curses.KEY_UP):
            if self.cursor > 0:
                self.cursor -= 1
                if self.cursor < self.scroll:
                    self.scroll -= 1
        elif key in (10, 13, curses.KEY_ENTER):
            if self.items:
                self.detail_mode = True
        elif key == ord("/"):
            self.search_mode = True
            self.search_query = ""
        elif key == ord("r"):
            self._refresh_data()
        elif chr(key) in self.MODE_KEYS if 0 <= key <= 127 else False:
            new_mode = self.MODE_KEYS[chr(key)]
            if new_mode != self.mode:
                self.mode = new_mode
                self.search_query = ""
                self._refresh_data()
        return True


def run(stdscr):
    curses.curs_set(0)
    _init_colors()
    stdscr.keypad(True)
    stdscr.timeout(2000)  # refresh every 2s

    tui = TUI(stdscr)
    while True:
        tui.draw()
        key = stdscr.getch()
        if key == -1:
            continue
        if not tui.handle_key(key):
            break


def main():
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"TUI error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
