#!/usr/bin/env python3
"""
RepoMem MCP server — stdio JSON-RPC 2.0, stdlib only.
Claude Code wires this as an MCP server in settings.json.

Protocol: Content-Length framed JSON-RPC over stdin/stdout (same as LSP).
"""
from __future__ import annotations
import sys
import json
import os
import logging
from typing import Any

# Add RepoMem lib to path
REPOMEM_INSTALL = os.environ.get(
    "REPOMEM_INSTALL",
    os.path.expanduser("~/.repomem/lib")
)
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)

LOG_PATH = os.path.expanduser("~/.repomem/logs/mcp_server.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("repomem.mcp")


# ── Protocol I/O ──────────────────────────────────────────────────────────────

def read_message() -> dict | None:
    """Read one JSON-RPC message from stdin.

    Supports two transports:
    - Content-Length framed (LSP-style, older MCP)
    - Newline-delimited JSON (newer MCP stdio transport)
    """
    try:
        first_line = sys.stdin.buffer.readline()
        if not first_line:
            return None  # EOF

        decoded = first_line.decode("utf-8").strip()

        # Newline-delimited JSON: first line IS the JSON object
        if decoded.startswith("{"):
            global _transport
            _transport = "ndjson"
            return json.loads(decoded)

        # Content-Length framing: first line is a header
        header = decoded
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            part = line.decode("utf-8")
            if part == "\r\n" or part == "\n":
                break
            header += part

        content_length = 0
        for part in header.strip().split("\r\n"):
            if part.lower().startswith("content-length:"):
                content_length = int(part.split(":", 1)[1].strip())

        if content_length == 0:
            return None

        body = sys.stdin.buffer.read(content_length)
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        log.error(f"read_message error: {e}")
        return None


_transport: str = "ndjson"  # detected on first message: "ndjson" or "content-length"


def write_message(msg: dict) -> None:
    """Write one JSON-RPC message to stdout, matching the detected transport."""
    body = json.dumps(msg).encode("utf-8")
    if _transport == "content-length":
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        sys.stdout.buffer.write(header + body)
    else:
        sys.stdout.buffer.write(body + b"\n")
    sys.stdout.buffer.flush()


def ok(req_id: Any, result: Any) -> None:
    write_message({"jsonrpc": "2.0", "id": req_id, "result": result})


def err(req_id: Any, code: int, message: str) -> None:
    write_message({"jsonrpc": "2.0", "id": req_id,
                   "error": {"code": code, "message": message}})


# ── Tool definitions ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "repomem_search",
        "description": "Search RepoMem observations using full-text search. Returns matching observations across all projects or filtered by project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query":   {"type": "string", "description": "Search query"},
                "project": {"type": "string", "description": "Filter by project name (optional)"},
                "type":    {"type": "string", "description": "Filter by observation type: bugfix|decision|upgrade|pending|pattern|warning|learning|error"},
                "limit":   {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "repomem_answer",
        "description": "Answer a question from RepoMem memory. Returns a compact, #id-cited grounding block (observations, decisions, unresolved errors) to answer from — no LLM call, no API key. Use when the user asks 'did we…', 'why did we…', 'what's the decision on…'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ground in memory"},
                "project":  {"type": "string", "description": "Project name (optional, auto-detected)"},
                "limit":    {"type": "integer", "description": "Max observations to include (default 8)"},
            },
            "required": ["question"],
        },
    },
    {
        "name": "repomem_save",
        "description": "Save an observation to RepoMem memory. Use this to persist important facts, decisions, bugs, or learnings from the current session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type":    {"type": "string", "description": "bugfix|decision|upgrade|pending|pattern|warning|learning|error"},
                "summary": {"type": "string", "description": "One-line summary (max 200 chars)"},
                "detail":  {"type": "string", "description": "Full context (optional)"},
                "topic":   {"type": "string", "description": "Topic tag: room|hilt|compose|agp|kotlin|networking|build|release (optional, auto-detected if omitted)"},
                "project": {"type": "string", "description": "Project name (optional, auto-detected from cwd)"},
            },
            "required": ["type", "summary"],
        },
    },
    {
        "name": "repomem_context",
        "description": "Get full RepoMem context for a project — decisions, pending tasks, recent observations. Use at session start or when switching projects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name (optional, auto-detected)"},
            },
        },
    },
    {
        "name": "repomem_pending",
        "description": "List open pending tasks from RepoMem.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project (optional)"},
            },
        },
    },
    {
        "name": "repomem_decisions",
        "description": "List architectural decisions from RepoMem. Global decisions apply to all projects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "description": "Filter by scope: 'ALL' for global, or project name"},
            },
        },
    },
    {
        "name": "repomem_add_pending",
        "description": "Add a pending task to RepoMem.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task":     {"type": "string", "description": "Task description"},
                "project":  {"type": "string", "description": "Project name (optional, auto-detected)"},
                "priority": {"type": "string", "description": "P1|P2|P3 (default P2)"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "repomem_resolve",
        "description": "Mark a pending task as resolved by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Pending task ID"},
            },
            "required": ["id"],
        },
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────────

def handle_repomem_search(args: dict) -> dict:
    from repomem.search import search, format_results
    results = search(
        args["query"],
        project=args.get("project"),
        obs_type=args.get("type"),
        limit=args.get("limit", 10),
    )
    if not results:
        return {"content": [{"type": "text", "text": "No results found."}]}

    lines = []
    for r in results:
        lines.append(f"[{r.type}] {r.summary}")
        lines.append(f"  Project: {r.project} | Date: {r.date} | Topic: {r.topic}")
        if r.detail:
            lines.append(f"  {r.detail[:150]}")
        lines.append("")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def handle_repomem_answer(args: dict) -> dict:
    from repomem.answer import answer
    from repomem.capture import detect_project
    project = args.get("project")
    if not project:
        project, _, _ = detect_project()
    block = answer(args["question"], project=project, limit=args.get("limit", 8))
    return {"content": [{"type": "text", "text": block}]}


def _ensure_mcp_session(session_id: str, project: str, folder: str) -> None:
    """Create a sentinel session row if missing (MCP observations need a parent session)."""
    import time as _t
    from repomem.db import db as _db
    with _db() as conn:
        exists = conn.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO sessions (id, project, folder, repo_path, started_at) VALUES (?,?,?,?,?)",
                (session_id, project, folder, "", int(_t.time()))
            )


def handle_repomem_save(args: dict) -> dict:
    import time
    from datetime import date as _date
    from repomem.db import save_observation, init_db
    from repomem.models import Observation
    from repomem.capture import detect_project, detect_topic

    init_db()
    project = args.get("project")
    folder = ""
    if not project:
        project, folder, _ = detect_project()

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "mcp")
    _ensure_mcp_session(session_id, project, folder)

    topic = args.get("topic") or detect_topic(args.get("summary", ""))

    obs = Observation(
        session_id=session_id,
        project=project,
        folder=folder,
        type=args["type"],
        topic=topic,
        summary=args["summary"][:200],
        detail=args.get("detail", "")[:5000],
        date=_date.today().isoformat(),
        created_at=int(time.time()),
    )
    obs_id = save_observation(obs)
    from repomem.entity import link_observation
    link_observation(obs_id, project, obs.summary + " " + obs.detail)
    return {"content": [{"type": "text", "text": f"Saved observation #{obs_id}: [{args['type']}] {args['summary'][:80]}"}]}


def handle_repomem_context(args: dict) -> dict:
    from repomem.inject import build_context
    project = args.get("project")
    ctx = build_context(project=project)
    if not ctx:
        return {"content": [{"type": "text", "text": "No memory found for this project yet."}]}
    return {"content": [{"type": "text", "text": ctx}]}


def handle_repomem_pending(args: dict) -> dict:
    from repomem.db import get_pending, init_db
    init_db()
    items = get_pending(project=args.get("project"))
    if not items:
        return {"content": [{"type": "text", "text": "No pending tasks."}]}
    lines = [f"[#{p['id']}] [{p['priority']}] {p['project']}: {p['task']}" for p in items]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def handle_repomem_decisions(args: dict) -> dict:
    from repomem.db import get_decisions, init_db
    init_db()
    decisions = get_decisions(scope=args.get("scope"))
    if not decisions:
        return {"content": [{"type": "text", "text": "No decisions recorded."}]}
    lines = [f"[{d['scope']}] [{d['topic']}] {d['decision']}" for d in decisions]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def handle_repomem_add_pending(args: dict) -> dict:
    from repomem.db import save_pending, init_db
    from repomem.models import Pending
    from repomem.capture import detect_project
    init_db()
    project = args.get("project")
    if not project:
        project, _, _ = detect_project()
    p = Pending(
        project=project,
        task=args["task"],
        priority=args.get("priority", "P2"),
        session_id=os.environ.get("CLAUDE_CODE_SESSION_ID", "mcp"),
    )
    pid = save_pending(p)
    return {"content": [{"type": "text", "text": f"Added pending task #{pid}: [{p.priority}] {args['task']}"}]}


def handle_repomem_resolve(args: dict) -> dict:
    from repomem.db import resolve_pending, init_db
    init_db()
    resolve_pending(args["id"])
    return {"content": [{"type": "text", "text": f"Resolved task #{args['id']}"}]}


HANDLERS = {
    "repomem_search":      handle_repomem_search,
    "repomem_answer":      handle_repomem_answer,
    "repomem_save":        handle_repomem_save,
    "repomem_context":     handle_repomem_context,
    "repomem_pending":     handle_repomem_pending,
    "repomem_decisions":   handle_repomem_decisions,
    "repomem_add_pending": handle_repomem_add_pending,
    "repomem_resolve":     handle_repomem_resolve,
}


# ── Main loop ─────────────────────────────────────────────────────────────────

def handle_request(req: dict) -> None:
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    log.debug(f"→ {method} id={req_id}")

    # Notifications (no id) — log and return silently
    if req_id is None:
        log.debug(f"notification: {method}")
        return

    if method == "initialize":
        # Echo back the client's requested protocol version if we support it
        client_version = params.get("protocolVersion", "2024-11-05")
        supported = {"2024-11-05", "2025-03-26"}
        proto = client_version if client_version in supported else "2024-11-05"
        ok(req_id, {
            "protocolVersion": proto,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "repomem", "version": "0.2.2"},
        })

    elif method == "tools/list":
        ok(req_id, {"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)
        if not handler:
            err(req_id, -32601, f"Unknown tool: {tool_name}")
            return
        try:
            result = handler(tool_args)
            ok(req_id, result)
        except Exception as e:
            log.error(f"Tool {tool_name} error: {e}", exc_info=True)
            err(req_id, -32603, f"Internal error in {tool_name}")

    elif method == "ping":
        ok(req_id, {})

    elif method in ("resources/list", "prompts/list"):
        key = method.split("/")[0]
        ok(req_id, {key: []})

    else:
        err(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    log.info("RepoMem MCP server starting")
    while True:
        msg = read_message()
        if msg is None:
            log.info("EOF — shutting down")
            break
        try:
            handle_request(msg)
        except Exception as e:
            log.error(f"Unhandled error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
