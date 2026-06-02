#!/usr/bin/env python3
"""
RepoMem web viewer — stdlib http.server, no Flask, no npm.
Dark mode, responsive, pure HTML+CSS+JS.

Usage: repomem server [--port 39000]
       python3 server/web_viewer.py
"""
from __future__ import annotations
import json
import os
import sys
import urllib.parse
from html import escape as _esc
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPOMEM_INSTALL = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)

PORT = int(os.environ.get("REPOMEM_PORT", 39000))

# ── CSS / JS (inlined) ────────────────────────────────────────────────────────

CSS = """
:root {
  --bg: #0f1117; --surface: #1a1d27; --border: #2d3148;
  --accent: #7c6cfc; --text: #e8e9f0; --muted: #8a8fa8;
  --green: #4ade80; --yellow: #facc15; --red: #f87171; --blue: #60a5fa;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
nav { background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 20px; display: flex; gap: 24px; align-items: center; position: sticky; top: 0; z-index: 10; }
nav h1 { color: var(--accent); font-size: 16px; margin-right: auto; }
nav a { color: var(--muted); font-size: 12px; }
nav a:hover, nav a.active { color: var(--text); }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 28px; }
.stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }
.stat-card .num { font-size: 28px; font-weight: bold; color: var(--accent); }
.stat-card .label { color: var(--muted); font-size: 11px; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; }
th { background: var(--surface); color: var(--muted); font-size: 11px; text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:hover td { background: var(--surface); }
.badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: bold; }
.badge-bugfix { background: #1a3a2a; color: var(--green); }
.badge-decision { background: #2a1a3a; color: #c084fc; }
.badge-warning { background: #3a2a1a; color: var(--yellow); }
.badge-error { background: #3a1a1a; color: var(--red); }
.badge-learning { background: #1a2a3a; color: var(--blue); }
.badge-upgrade { background: #1a3a3a; color: #34d399; }
.badge-pending { background: #2a2a1a; color: #fbbf24; }
.badge-pattern { background: #1a2a1a; color: #a3e635; }
.badge-p1 { background: #3a1a1a; color: var(--red); }
.badge-p2 { background: #3a2a1a; color: var(--yellow); }
.badge-p3 { background: #1a2a1a; color: var(--green); }
.search-bar { display: flex; gap: 10px; margin-bottom: 20px; }
.search-bar input { flex: 1; background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 6px; font-family: inherit; font-size: 13px; }
.search-bar input:focus { outline: none; border-color: var(--accent); }
.search-bar button { background: var(--accent); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-family: inherit; }
.muted { color: var(--muted); }
.section-title { font-size: 14px; color: var(--text); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.empty { color: var(--muted); padding: 24px; text-align: center; }
"""

JS = """
function search() {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  window.location = '/search?q=' + encodeURIComponent(q);
}
document.addEventListener('keydown', function(e) {
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
    e.preventDefault();
    const q = document.getElementById('q');
    if (q) q.focus();
  }
});
"""


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _page(title: str, body: str, active: str = "") -> str:
    nav_links = [
        ("Dashboard", "/", "dashboard"),
        ("Observations", "/observations", "observations"),
        ("Decisions", "/decisions", "decisions"),
        ("Pending", "/pending", "pending"),
        ("Errors", "/errors", "errors"),
        ("Projects", "/projects", "projects"),
    ]
    nav_html = "".join(
        f'<a href="{href}" class="{"active" if active == key else ""}">{label}</a>'
        for label, href, key in nav_links
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — RepoMem</title>
<style>{CSS}</style>
</head>
<body>
<nav>
  <h1>🧠 RepoMem</h1>
  {nav_html}
  <div class="search-bar" style="margin:0">
    <input id="q" placeholder="Search… (press /)" onkeydown="if(event.key==='Enter')search()">
    <button onclick="search()">→</button>
  </div>
</nav>
<div class="container">
{body}
</div>
<script>{JS}</script>
</body>
</html>"""


def _badge(obs_type: str) -> str:
    return f'<span class="badge badge-{obs_type}">{obs_type}</span>'


def _priority_badge(priority: str) -> str:
    return f'<span class="badge badge-{priority.lower()}">{priority}</span>'


def _type_icon(obs_type: str) -> str:
    return {"bugfix": "🐛", "decision": "⚡", "upgrade": "⬆️", "warning": "⚠️",
            "learning": "💡", "pending": "📋", "pattern": "🔁", "error": "❌"}.get(obs_type, "•")


# ── Page renderers ────────────────────────────────────────────────────────────

def page_dashboard() -> str:
    from repomem.db import get_stats, get_observations, get_pending, get_unresolved_errors
    from repomem.db import init_db
    init_db()

    stats = get_stats()
    projects = stats.get("projects", [])

    cards = [
        (stats["observations"], "Observations"),
        (stats["sessions"], "Sessions"),
        (stats["decisions"], "Decisions"),
        (stats["pending"], "Pending"),
        (len(projects), "Projects"),
        (f"{stats['db_size_kb']} KB", "DB Size"),
    ]
    cards_html = "".join(
        f'<div class="stat-card"><div class="num">{n}</div><div class="label">{l}</div></div>'
        for n, l in cards
    )

    recent = get_observations(project=projects[0] if projects else "_none_", limit=10) if projects else []
    # Get cross-project recent
    from repomem.db import db as _db
    with _db() as conn:
        rows = conn.execute("""
            SELECT * FROM observations WHERE is_archived=0
            ORDER BY created_at DESC LIMIT 15
        """).fetchall()
    recent = [dict(r) for r in rows]

    rows_html = "".join(f"""
        <tr>
          <td>{_type_icon(o['type'])} {_badge(o['type'])}</td>
          <td><a href="/observations?project={urllib.parse.quote(o['project'])}">{_esc(o['project'])}</a></td>
          <td>{_esc(o['summary'][:80])}</td>
          <td class="muted">{_esc(o['date'])}</td>
        </tr>""" for o in recent)

    errors = get_unresolved_errors()
    err_html = ""
    if errors:
        err_rows = "".join(f"""
            <tr>
              <td><a href="/observations?project={urllib.parse.quote(e['project'])}">{_esc(e['project'])}</a></td>
              <td>{_esc(e['error_text'][:80])}</td>
              <td class="muted">{_esc(e['first_seen'])}</td>
            </tr>""" for e in errors[:5])
        err_html = f"""
        <h2 class="section-title" style="margin-top:28px">❌ Unresolved Errors</h2>
        <table><thead><tr><th>Project</th><th>Error</th><th>First Seen</th></tr></thead>
        <tbody>{err_rows}</tbody></table>"""

    body = f"""
    <div class="stats-grid">{cards_html}</div>
    <h2 class="section-title">Recent Observations</h2>
    <table>
      <thead><tr><th>Type</th><th>Project</th><th>Summary</th><th>Date</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="4" class="empty">No observations yet.</td></tr>'}</tbody>
    </table>
    {err_html}"""
    return _page("Dashboard", body, "dashboard")


def page_observations(project: str = "", query: str = "") -> str:
    from repomem.db import get_observations, init_db
    from repomem.search import search as fts_search
    init_db()

    if query:
        results = fts_search(query, project=project or None, limit=50)
        obs = [{"type": r.type, "project": r.project, "topic": r.topic,
                "summary": r.summary, "date": r.date, "detail": r.detail} for r in results]
        title = f"Search: {query}"
    else:
        from repomem.db import db as _db
        with _db() as conn:
            if project:
                rows = conn.execute("""
                    SELECT * FROM observations WHERE project=? AND is_archived=0
                    ORDER BY created_at DESC LIMIT 100
                """, (project,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM observations WHERE is_archived=0
                    ORDER BY created_at DESC LIMIT 100
                """).fetchall()
        obs = [dict(r) for r in rows]
        title = f"Observations — {project}" if project else "All Observations"

    rows_html = "".join(f"""
        <tr>
          <td>{_type_icon(o['type'])} {_badge(o['type'])}</td>
          <td><a href="/observations?project={urllib.parse.quote(o['project'])}">{_esc(o['project'])}</a></td>
          <td>{_esc(o.get('topic','')) or '<span class="muted">—</span>'}</td>
          <td>{_esc(o['summary'][:100])}</td>
          <td class="muted">{_esc(o['date'])}</td>
        </tr>""" for o in obs)

    body = f"""
    <h2 class="section-title">{title} ({len(obs)})</h2>
    <table>
      <thead><tr><th>Type</th><th>Project</th><th>Topic</th><th>Summary</th><th>Date</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="5" class="empty">No observations.</td></tr>'}</tbody>
    </table>"""
    return _page(title, body, "observations")


def page_decisions() -> str:
    from repomem.db import get_decisions, init_db
    init_db()
    decisions = get_decisions()
    rows_html = "".join(f"""
        <tr>
          <td>{_esc(d['scope'])}</td>
          <td>{_esc(d['topic'])}</td>
          <td>{_esc(d['decision'])}</td>
          <td class="muted">{_esc(d.get('reason','')[:60])}</td>
          <td class="muted">{_esc(d['date'])}</td>
        </tr>""" for d in decisions)
    body = f"""
    <h2 class="section-title">Decisions ({len(decisions)})</h2>
    <table>
      <thead><tr><th>Scope</th><th>Topic</th><th>Decision</th><th>Reason</th><th>Date</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="5" class="empty">No decisions.</td></tr>'}</tbody>
    </table>"""
    return _page("Decisions", body, "decisions")


def page_pending() -> str:
    from repomem.db import get_pending, init_db
    init_db()
    items = get_pending()
    rows_html = "".join(f"""
        <tr>
          <td>{_priority_badge(p['priority'])}</td>
          <td><a href="/observations?project={urllib.parse.quote(p['project'])}">{_esc(p['project'])}</a></td>
          <td>{_esc(p['task'])}</td>
          <td class="muted">{_esc(str(p['created_at']))}</td>
        </tr>""" for p in items)
    body = f"""
    <h2 class="section-title">Pending Tasks ({len(items)})</h2>
    <table>
      <thead><tr><th>Priority</th><th>Project</th><th>Task</th><th>Created</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="4" class="empty">No pending tasks.</td></tr>'}</tbody>
    </table>"""
    return _page("Pending", body, "pending")


def page_errors() -> str:
    from repomem.db import get_unresolved_errors, init_db
    init_db()
    errors = get_unresolved_errors()
    rows_html = "".join(f"""
        <tr>
          <td><a href="/observations?project={urllib.parse.quote(e['project'])}">{_esc(e['project'])}</a></td>
          <td>{_esc(e['error_text'][:100])}</td>
          <td>{_esc(e.get('fix','')[:60]) or '<span class="muted">—</span>'}</td>
          <td class="muted">{e['recurred'] or 0}×</td>
          <td class="muted">{_esc(e['first_seen'])}</td>
        </tr>""" for e in errors)
    body = f"""
    <h2 class="section-title">Unresolved Errors ({len(errors)})</h2>
    <table>
      <thead><tr><th>Project</th><th>Error</th><th>Fix</th><th>Recurred</th><th>First Seen</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="5" class="empty">No unresolved errors.</td></tr>'}</tbody>
    </table>"""
    return _page("Errors", body, "errors")


def page_projects() -> str:
    from repomem.db import get_stats, init_db, db as _db
    init_db()
    stats = get_stats()
    projects = sorted(stats.get("projects", []))

    rows_html = ""
    with _db() as conn:
        for p in projects:
            obs = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE project=? AND is_archived=0", (p,)
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM pending WHERE project=? AND resolved_at IS NULL", (p,)
            ).fetchone()[0]
            last = conn.execute(
                "SELECT date FROM observations WHERE project=? AND is_archived=0 ORDER BY created_at DESC LIMIT 1", (p,)
            ).fetchone()
            last_date = last[0] if last else "—"
            rows_html += f"""
            <tr>
              <td><a href="/observations?project={urllib.parse.quote(p)}">{_esc(p)}</a></td>
              <td>{obs}</td>
              <td>{pending}</td>
              <td class="muted">{_esc(str(last_date))}</td>
            </tr>"""

    body = f"""
    <h2 class="section-title">Projects ({len(projects)})</h2>
    <table>
      <thead><tr><th>Project</th><th>Observations</th><th>Pending</th><th>Last Activity</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan="4" class="empty">No projects yet.</td></tr>'}</tbody>
    </table>"""
    return _page("Projects", body, "projects")


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class RepoMemHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silent

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        try:
            if path == "/" or path == "":
                self._send_html(page_dashboard())
            elif path == "/observations":
                self._send_html(page_observations(
                    project=params.get("project", ""),
                    query=params.get("q", "")
                ))
            elif path == "/search":
                self._send_html(page_observations(
                    project=params.get("project", ""),
                    query=params.get("q", "")
                ), 200)
            elif path == "/decisions":
                self._send_html(page_decisions())
            elif path == "/pending":
                self._send_html(page_pending())
            elif path == "/errors":
                self._send_html(page_errors())
            elif path == "/projects":
                self._send_html(page_projects())
            elif path == "/api/stats":
                from repomem.db import get_stats, init_db
                init_db()
                self._send_json(get_stats())
            else:
                self._send_html("<h1>404</h1>", 404)
        except Exception as e:
            self._send_html(f"<pre>Error: {_esc(str(e))}</pre>", 500)


def run(port: int = PORT) -> None:
    server = HTTPServer(("127.0.0.1", port), RepoMemHandler)
    print(f"RepoMem viewer → http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run(p)
