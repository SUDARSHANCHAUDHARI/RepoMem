"""
RepoMem CLI — command-line interface.
Usage: python -m repomem <command> [args]
"""
from __future__ import annotations
import os
import sys
import argparse
from typing import Optional

from . import db
from .capture import detect_project
from .search import search, format_results
from .models import Decision, Pending, Pattern, Observation
from .config import OBS_TYPES


def cmd_search(args) -> None:
    """Search observations."""
    db.init_db()
    results = search(
        args.query,
        project=args.project or None,
        obs_type=args.type or None,
        limit=args.limit
    )
    print(format_results(results, verbose=args.verbose))


# MCP clients that speak the standard stdio transport RepoMem's server implements.
# All wrap the same server entry under an "mcpServers" object; only the config
# file location differs.
MCP_CLIENTS = {
    "claude":   "~/.claude/settings.json  (or <project>/.mcp.json)",
    "cursor":   "~/.cursor/mcp.json  (or <project>/.cursor/mcp.json)",
    "windsurf": "~/.codeium/windsurf/mcp_config.json",
    "cline":    "VS Code → Cline → MCP Servers → Configure (cline_mcp_settings.json)",
    "codex":    "~/.codex/config.toml  (see Codex MCP docs; same command/args)",
}


def cmd_mcp_config(args) -> None:
    """Print the MCP server config snippet for a given client."""
    import json
    lib = os.environ.get("REPOMEM_INSTALL", os.path.expanduser("~/.repomem/lib"))
    server_entry = {
        "command": sys.executable,
        "args": [os.path.join(lib, "server", "mcp_server.py")],
        "env": {"REPOMEM_INSTALL": lib},
    }
    location = MCP_CLIENTS[args.client]
    print(f"# {args.client}: add this under \"mcpServers\" in {location}\n")
    print(json.dumps({"repomem": server_entry}, indent=2))


def cmd_answer(args) -> None:
    """Build a grounded, #id-cited memory block for a question."""
    from .answer import answer
    project = args.project or detect_project()[0]
    print(answer(args.question, project=project, limit=args.limit))


def _ensure_manual_session(project: str) -> None:
    """Ensure a 'manual' sentinel session exists for CLI-sourced observations."""
    import time as _t
    with db.db() as conn:
        if not conn.execute("SELECT id FROM sessions WHERE id='manual'").fetchone():
            conn.execute(
                "INSERT INTO sessions (id, project, folder, repo_path, started_at) VALUES ('manual',?,?,?,?)",
                (project, "", "", int(_t.time()))
            )


def cmd_add(args) -> None:
    """Manually add an observation."""
    import time
    from datetime import date

    db.init_db()
    project, folder, _ = detect_project()
    if args.project:
        project = args.project

    _ensure_manual_session(project)

    obs = Observation(
        session_id="manual",
        project=project,
        folder=folder,
        type=args.type,
        topic=args.topic or "",
        summary=args.summary,
        detail=args.detail or "",
        date=date.today().isoformat(),
        created_at=int(time.time()),
    )
    obs_id = db.save_observation(obs)
    print(f"✅ Saved observation #{obs_id}: [{args.type}] {args.summary}")


def cmd_pending(args) -> None:
    """List open pending tasks."""
    db.init_db()
    project = args.project or None
    items = db.get_pending(project=project)

    if not items:
        print("No pending tasks." + (f" (project: {project})" if project else ""))
        return

    print(f"{'Project':<20} {'Pri':<4} {'Task'}")
    print("-" * 70)
    for p in items:
        print(f"{p['project']:<20} {p['priority']:<4} {p['task']}")


def cmd_add_pending(args) -> None:
    """Add a pending task."""
    db.init_db()
    project, _, _ = detect_project()
    if args.project:
        project = args.project

    _ensure_manual_session(project)

    p = Pending(
        project=project,
        task=args.task,
        priority=args.priority,
        session_id="manual"
    )
    pid = db.save_pending(p)
    print(f"✅ Added pending task #{pid}: [{args.priority}] {args.task}")


def cmd_resolve(args) -> None:
    """Resolve a pending task or mark observation resolved."""
    db.init_db()
    db.resolve_pending(args.id)
    print(f"✅ Resolved #{args.id}")


def cmd_decisions(args) -> None:
    """List architectural decisions."""
    db.init_db()
    project = args.project or None
    decisions = db.get_decisions(scope=project)

    if not decisions:
        print("No decisions recorded.")
        return

    print(f"{'Scope':<20} {'Topic':<15} {'Decision'}")
    print("-" * 80)
    for d in decisions:
        print(f"{d['scope']:<20} {d['topic']:<15} {d['decision']}")


def cmd_add_decision(args) -> None:
    """Add an architectural decision."""
    db.init_db()
    dec = Decision(
        scope=args.scope or "ALL",
        topic=args.topic,
        decision=args.decision,
        reason=args.reason or "",
    )
    did = db.save_decision(dec)
    print(f"✅ Saved decision #{did}: [{args.scope}] {args.decision}")


def cmd_status(args) -> None:
    """Show DB stats."""
    db.init_db()
    project = args.project or None

    if project:
        stats = db.get_stats(project=project)
        print(f"\n📊 RepoMem — {project}")
        print(f"  Observations: {stats['observations']}")
        print(f"  Sessions:     {stats['sessions']}")
        print(f"  Pending:      {stats['pending']}")
    else:
        stats = db.get_stats()
        print(f"\n📊 RepoMem — Global")
        print(f"  Observations: {stats['observations']}")
        print(f"  Sessions:     {stats['sessions']}")
        print(f"  Pending:      {stats['pending']}")
        print(f"  Decisions:    {stats['decisions']}")
        print(f"  Projects:     {len(stats['projects'])}")
        print(f"  DB size:      {stats['db_size_kb']} KB")
        if stats["projects"]:
            print(f"\n  Projects tracked:")
            for p in sorted(stats["projects"]):
                print(f"    • {p}")
    print()


def cmd_tui(args) -> None:
    """Launch full-screen TUI."""
    from .tui import main as tui_main
    tui_main()


def cmd_server(args) -> None:
    """Start the web viewer."""
    import sys as _sys
    server_path = os.path.join(os.path.dirname(__file__), "..", "server", "web_viewer.py")
    # Also check installed location
    installed = os.path.join(os.path.expanduser("~/.repomem/lib"), "server", "web_viewer.py")
    if not os.path.exists(server_path) and os.path.exists(installed):
        server_path = installed

    import importlib.util
    spec = importlib.util.spec_from_file_location("web_viewer", server_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run(port=args.port)


def cmd_graphify(args) -> None:
    """Show graphify analysis for current project."""
    from .graphify import analyze
    from .capture import detect_project

    db.init_db()
    project = args.project or detect_project()[0]
    result = analyze(project, repo_path=args.repo or None, threshold=args.threshold)

    if "error" in result:
        print(f"⚠️  {result['error']}")
        return

    print(f"\n📊 Graphify: {project}")
    print(f"  Nodes: {result['nodes']}  Edges: {result['edges']}  Communities: {result['communities']}")
    print(f"  Graph: {result['graph_path']}")

    if result["god_nodes"]:
        print(f"\n  ⚡ God Nodes (≥{args.threshold} edges):")
        for n in result["god_nodes"][:10]:
            print(f"    {n['label']:40s} {n['edge_count']} edges")
    else:
        print(f"  No God Nodes found (threshold: {args.threshold} edges)")
    print()


def cmd_sync(args) -> None:
    """Export/import memory for cross-machine sync."""
    from .sync import export_sync, import_sync, sync_status

    if args.export:
        stats = export_sync(commit=not args.no_commit)
        print(f"✅ Exported: {stats['observations']} obs, {stats['decisions']} decisions, {stats['pending']} pending")
        print(f"   File: {stats['chunk_file']}")
        if stats["committed"]:
            print("   Committed to git ✅")
        else:
            print("   Not committed (use git push manually or run without --no-commit)")
    elif args.import_:
        stats = import_sync()
        print(f"✅ Imported: {stats['observations']} obs, {stats['decisions']} decisions, {stats['pending']} pending")
        print(f"   Skipped own machine chunks: {stats['skipped_own_machine']}")
    else:
        status = sync_status()
        print(f"\n🔄 RepoMem Sync Status")
        print(f"  Machine:          {status['machine']}")
        print(f"  Last export ID:   {status['last_exported_id']}")
        if status["last_export_ts"]:
            from .inject import _age_label
            from datetime import datetime
            age = _age_label(datetime.fromtimestamp(status["last_export_ts"]).date().isoformat())
            print(f"  Last exported:    {age}")
        print(f"  Chunk file:       {status['chunk_file']} ({'exists' if status['chunk_exists'] else 'missing'})")
        if status["peer_chunks"]:
            print(f"  Peer chunks:      {', '.join(status['peer_chunks'])}")
        else:
            print("  Peer chunks:      none")
        print()


def cmd_releases(args) -> None:
    """List releases."""
    db.init_db()
    releases = db.get_releases(project=args.project or None, limit=args.limit)
    if not releases:
        print("No releases recorded.")
        return
    print(f"\n{'Project':<20} {'Version':<12} {'Store':<12} {'Date'}")
    print("-" * 65)
    for r in releases:
        print(f"{r['project']:<20} v{r['version_name']:<11} {r['store']:<12} {r['released_at']}")
    print()


def cmd_branches(args) -> None:
    """List open branches."""
    db.init_db()
    branches = db.get_open_branches(project=args.project or None)
    if not branches:
        print("No open branches recorded.")
        return
    print(f"\n{'Project':<20} {'Branch':<35} {'Created'}")
    print("-" * 65)
    for b in branches:
        print(f"{b['project']:<20} {b['branch']:<35} {b['created_at']}")
    print()


def cmd_obsidian(args) -> None:
    """Export project memory to Obsidian vault."""
    from .obsidian import export_project, export_all
    from pathlib import Path

    vault = Path(args.vault) if args.vault else None
    no_wikilinks = getattr(args, "no_wikilinks", False)

    if args.project:
        path = export_project(args.project, vault=vault, no_wikilinks=no_wikilinks)
        print(f"✅ Exported {args.project} → {path}")
    else:
        paths = export_all(vault=vault, no_wikilinks=no_wikilinks)
        print(f"✅ Exported {len(paths)} projects to Obsidian")
        for p in paths:
            print(f"   {p}")


def cmd_entities(args) -> None:
    """List known entities."""
    from .entity import get_entities, get_observations_for_entity
    db.init_db()

    if args.name:
        obs = get_observations_for_entity(args.name)
        if not obs:
            print(f"No observations found for entity: {args.name}")
            return
        print(f"\nObservations mentioning '{args.name}':\n")
        for o in obs:
            print(f"  [{o['type']}] {o['summary']}  ({o['date']})")
        print()
        return

    entities = get_entities(project=args.project or None, min_mentions=args.min)
    if not entities:
        print("No entities recorded.")
        return
    print(f"\n{'Type':<10} {'Mentions':<9} {'Name'}")
    print("-" * 50)
    for e in entities:
        print(f"{e['type']:<10} {e['mention_count']:<9} {e['name']}")
    print()


def cmd_doctor(args) -> None:
    """Health check — diagnose DB issues."""
    db.init_db()
    print("\n🩺 RepoMem Doctor\n")

    issues = []
    recommendations = []

    conn = db.get_connection()
    try:
        # DB size
        import os as _os
        from pathlib import Path as _Path
        from .config import DB_PATH
        db_path = _Path(_os.environ.get("REPOMEM_DIR", str(DB_PATH.parent))) / "memory.db"
        if db_path.exists():
            size_mb = db_path.stat().st_size / 1024 / 1024
            print(f"  DB size:            {size_mb:.1f} MB")
            if size_mb > 100:
                issues.append("DB > 100MB — run `python3 ~/.repomem/crons/defrag.py`")

        # Observation counts
        total = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        stale = conn.execute("SELECT COUNT(*) FROM observations WHERE is_stale=1").fetchone()[0]
        archived = conn.execute("SELECT COUNT(*) FROM observations WHERE is_archived=1").fetchone()[0]
        conflicts = conn.execute("SELECT COUNT(DISTINCT conflict_id) FROM observations WHERE conflict_id IS NOT NULL").fetchone()[0]
        active = total - archived

        print(f"  Observations:       {active} active, {stale} stale, {archived} archived")
        if stale > active * 0.3:
            issues.append(f"{stale} stale observations (>{int(0.3*active)}) — run defrag")

        # Errors
        errors = conn.execute("SELECT COUNT(*) FROM errors WHERE is_resolved=0").fetchone()[0]
        print(f"  Unresolved errors:  {errors}")
        if errors > 0:
            issues.append(f"{errors} unresolved error(s) — run `repomem search error`")

        # Conflicts
        print(f"  Conflicts:          {conflicts}")
        if conflicts > 0:
            issues.append(f"{conflicts} conflicting decision pair(s) detected")
            recommendations.append("Run `repomem decisions` to review and resolve")

        # Entities
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        print(f"  Entities tracked:   {entities}")

        # Orphaned observations (session deleted)
        orphaned = conn.execute("""
            SELECT COUNT(*) FROM observations o
            WHERE NOT EXISTS (SELECT 1 FROM sessions s WHERE s.id = o.session_id)
        """).fetchone()[0]
        if orphaned > 0:
            issues.append(f"{orphaned} orphaned observations (missing session row)")

        # FTS5 sync check
        fts_count = conn.execute("SELECT COUNT(*) FROM observations_fts").fetchone()[0]
        if abs(fts_count - active) > 5:
            issues.append(f"FTS5 out of sync ({fts_count} indexed vs {active} active)")
            recommendations.append("Run `python3 ~/.repomem/crons/defrag.py` to rebuild FTS5")

        # Projects with no observations
        projects_with_obs = conn.execute(
            "SELECT COUNT(DISTINCT project) FROM observations WHERE is_archived=0"
        ).fetchone()[0]
        print(f"  Projects tracked:   {projects_with_obs}")

        # Decisions
        decisions = conn.execute("SELECT COUNT(*) FROM decisions WHERE is_superseded=0").fetchone()[0]
        print(f"  Decisions:          {decisions}")

        # Pending
        pending = conn.execute("SELECT COUNT(*) FROM pending WHERE resolved_at IS NULL").fetchone()[0]
        print(f"  Pending tasks:      {pending}")

    finally:
        conn.close()

    print()
    if not issues:
        print("  ✅ All checks passed — DB is healthy\n")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue}")
        print()
        for rec in recommendations:
            print(f"  💡 {rec}")
        print()


def cmd_resolve_error(args) -> None:
    """Mark an error as resolved."""
    db.init_db()
    db.resolve_error(args.id)
    print(f"✅ Resolved error #{args.id}")


def cmd_merge_branch(args) -> None:
    """Mark a branch as merged."""
    db.init_db()
    project, _, _ = detect_project()
    if args.project:
        project = args.project
    db.merge_branch(project, args.branch,
                    pr_number=args.pr_number or None,
                    pr_url=args.pr_url or "")
    print(f"✅ Marked branch '{args.branch}' as merged in {project}")


def cmd_import_chat(args) -> None:
    """Import a raw exported Claude session .md file into memory."""
    import time
    from pathlib import Path as _Path
    from .capture import capture_session, detect_project

    db.init_db()
    chat_file = _Path(args.file)
    if not chat_file.exists():
        print(f"Error: file not found: {chat_file}", file=__import__("sys").stderr)
        return

    text = chat_file.read_text(encoding="utf-8", errors="replace")

    project, _, _ = detect_project()
    if args.project:
        project = args.project

    # Unique session id: filename stem + timestamp
    session_id = f"import-{chat_file.stem}-{int(time.time())}"

    import os as _os
    orig_project = _os.environ.get("REPOMEM_PROJECT")
    _os.environ["REPOMEM_PROJECT"] = project
    try:
        count = capture_session(session_summary=text, session_id=session_id)
    finally:
        if orig_project is None:
            _os.environ.pop("REPOMEM_PROJECT", None)
        else:
            _os.environ["REPOMEM_PROJECT"] = orig_project

    print(f"✅ Imported {count} observation(s) from {chat_file.name} → project '{project}'")

    if args.move:
        chat_file.unlink()
        print(f"   Deleted source file: {chat_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="repomem",
        description="RepoMem — persistent memory for AI coding agents"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search observations")
    p_search.add_argument("query")
    p_search.add_argument("--project", "-p")
    p_search.add_argument("--type", "-t", choices=OBS_TYPES)
    p_search.add_argument("--limit", "-l", type=int, default=20)
    p_search.add_argument("--verbose", "-v", action="store_true")

    # answer
    p_answer = sub.add_parser("answer", help="Grounded, #id-cited memory block for a question")
    p_answer.add_argument("question")
    p_answer.add_argument("--project", "-p")
    p_answer.add_argument("--limit", "-l", type=int, default=8)

    # mcp-config
    p_mcp = sub.add_parser("mcp-config", help="Print MCP server config snippet for an agent")
    p_mcp.add_argument("--client", "-c", required=True, choices=sorted(MCP_CLIENTS),
                       help="Target MCP client")

    # add
    p_add = sub.add_parser("add", help="Add an observation")
    p_add.add_argument("--type", "-t", required=True, choices=OBS_TYPES)
    p_add.add_argument("--summary", "-s", required=True)
    p_add.add_argument("--detail", "-d")
    p_add.add_argument("--topic")
    p_add.add_argument("--project", "-p")

    # pending
    p_pending = sub.add_parser("pending", help="List pending tasks")
    p_pending.add_argument("--project", "-p")

    # add-pending
    p_addp = sub.add_parser("add-pending", help="Add a pending task")
    p_addp.add_argument("task")
    p_addp.add_argument("--project", "-p")
    p_addp.add_argument("--priority", default="P2", choices=["P1", "P2", "P3"])

    # resolve
    p_resolve = sub.add_parser("resolve", help="Resolve a pending task")
    p_resolve.add_argument("id", type=int)

    # decisions
    p_dec = sub.add_parser("decisions", help="List decisions")
    p_dec.add_argument("--project", "-p")

    # add-decision
    p_addd = sub.add_parser("add-decision", help="Add an architectural decision")
    p_addd.add_argument("--decision", required=True)
    p_addd.add_argument("--topic", required=True)
    p_addd.add_argument("--scope", default="ALL")
    p_addd.add_argument("--reason")

    # tui
    sub.add_parser("tui", help="Full-screen terminal UI (vim keys: j/k//, Enter, q)")

    # server
    p_srv = sub.add_parser("server", help="Start web viewer (http://localhost:39000)")
    p_srv.add_argument("--port", type=int, default=39000)

    # graphify
    p_gfy = sub.add_parser("graphify", help="Graphify analysis for current project")
    p_gfy.add_argument("--project", "-p")
    p_gfy.add_argument("--repo", help="Path to repo root (default: cwd)")
    p_gfy.add_argument("--threshold", type=int, default=10, help="God node edge threshold")

    # sync
    p_sync = sub.add_parser("sync", help="Cross-machine memory sync via git")
    p_sync.add_argument("--export", action="store_true", help="Export to sync chunk")
    p_sync.add_argument("--import", dest="import_", action="store_true", help="Import peer chunks")
    p_sync.add_argument("--no-commit", action="store_true", help="Skip git commit after export")

    # releases
    p_rel = sub.add_parser("releases", help="List releases")
    p_rel.add_argument("--project", "-p")
    p_rel.add_argument("--limit", "-l", type=int, default=10)

    # branches
    p_br = sub.add_parser("branches", help="List open branches")
    p_br.add_argument("--project", "-p")

    # obsidian
    p_obs = sub.add_parser("obsidian", help="Export memory to Obsidian vault")
    p_obs.add_argument("--project", "-p", help="Export single project (default: all)")
    p_obs.add_argument("--vault", help="Override vault path")
    p_obs.add_argument("--no-wikilinks", action="store_true", dest="no_wikilinks",
                       help="Disable wikilink insertion in export")

    # resolve-error
    p_re = sub.add_parser("resolve-error", help="Mark an error as resolved")
    p_re.add_argument("id", type=int, help="Error ID")

    # merge-branch
    p_mb = sub.add_parser("merge-branch", help="Mark a branch as merged")
    p_mb.add_argument("branch", help="Branch name")
    p_mb.add_argument("--project", "-p")
    p_mb.add_argument("--pr-number", type=int)
    p_mb.add_argument("--pr-url", default="")

    # import-chat
    p_ic = sub.add_parser("import-chat", help="Import a raw Claude session .md export into memory")
    p_ic.add_argument("file", help="Path to exported .md file")
    p_ic.add_argument("--project", "-p", help="Override project name (default: auto-detect)")
    p_ic.add_argument("--move", action="store_true", help="Delete source file after import")

    # entities
    p_ent = sub.add_parser("entities", help="List known entities")
    p_ent.add_argument("--project", "-p")
    p_ent.add_argument("--name", "-n", help="Show observations for a specific entity")
    p_ent.add_argument("--min", type=int, default=1, help="Min mention count")

    # status
    p_status = sub.add_parser("status", help="Show DB stats")
    p_status.add_argument("--project", "-p")

    # doctor
    sub.add_parser("doctor", help="Health check")

    args = parser.parse_args()

    commands = {
        "search": cmd_search,
        "answer": cmd_answer,
        "mcp-config": cmd_mcp_config,
        "tui": cmd_tui,
        "server": cmd_server,
        "graphify": cmd_graphify,
        "sync": cmd_sync,
        "releases": cmd_releases,
        "branches": cmd_branches,
        "obsidian": cmd_obsidian,
        "entities": cmd_entities,
        "add": cmd_add,
        "pending": cmd_pending,
        "add-pending": cmd_add_pending,
        "resolve": cmd_resolve,
        "resolve-error": cmd_resolve_error,
        "merge-branch": cmd_merge_branch,
        "import-chat": cmd_import_chat,
        "decisions": cmd_decisions,
        "add-decision": cmd_add_decision,
        "status": cmd_status,
        "doctor": cmd_doctor,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
