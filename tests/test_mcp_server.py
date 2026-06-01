"""Tests for MCP server protocol handling."""
import json
import os
import sys
import tempfile
import pytest

# Point at temp DB
@pytest.fixture(autouse=True)
def temp_repomem(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    # Ensure repomem package resolves correctly
    src = os.path.join(os.path.dirname(__file__), "..")
    if src not in sys.path:
        sys.path.insert(0, src)
    from repomem.db import init_db
    init_db()
    yield


def make_request(method: str, params: dict = None, req_id: int = 1) -> bytes:
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    body = json.dumps(msg).encode()
    return f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def parse_response(data: bytes) -> dict:
    # Skip header
    parts = data.split(b"\r\n\r\n", 1)
    return json.loads(parts[1])


# ── Import server module ───────────────────────────────────────────────────────

def get_server():
    src = os.path.join(os.path.dirname(__file__), "..")
    if src not in sys.path:
        sys.path.insert(0, src)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mcp_server",
        os.path.join(src, "server", "mcp_server.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_initialize():
    server = get_server()
    responses = []

    def capture_ok(req_id, result):
        responses.append({"id": req_id, "result": result})

    server.ok = capture_ok
    server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert len(responses) == 1
    result = responses[0]["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["name"] == "repomem"


def test_tools_list():
    server = get_server()
    responses = []

    def capture_ok(req_id, result):
        responses.append(result)

    server.ok = capture_ok
    server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = responses[0]["tools"]
    names = [t["name"] for t in tools]
    assert "repomem_search" in names
    assert "repomem_save" in names
    assert "repomem_context" in names
    assert "repomem_pending" in names
    assert "repomem_decisions" in names
    assert "repomem_add_pending" in names
    assert "repomem_resolve" in names


def test_save_and_search():
    server = get_server()
    responses = []

    def capture_ok(req_id, result):
        responses.append(result)

    server.ok = capture_ok

    # Save
    server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "repomem_save", "arguments": {
            "type": "bugfix",
            "summary": "Fixed crash in UserRepository when state is null",
            "project": "TestApp",
        }}
    })
    assert "Saved observation" in responses[0]["content"][0]["text"]

    # Search
    server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "repomem_search", "arguments": {
            "query": "UserRepository",
            "project": "TestApp",
        }}
    })
    text = responses[1]["content"][0]["text"]
    assert "UserRepository" in text


def test_add_and_list_pending():
    server = get_server()
    responses = []

    def capture_ok(req_id, result):
        responses.append(result)

    server.ok = capture_ok

    server.handle_request({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "repomem_add_pending", "arguments": {
            "task": "Write migration tests",
            "project": "TestApp",
            "priority": "P1",
        }}
    })
    assert "Added pending task" in responses[0]["content"][0]["text"]

    server.handle_request({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {"name": "repomem_pending", "arguments": {"project": "TestApp"}}
    })
    text = responses[1]["content"][0]["text"]
    assert "Write migration tests" in text


def test_unknown_tool_returns_error():
    server = get_server()
    errors = []

    def capture_err(req_id, code, message):
        errors.append({"code": code, "message": message})

    server.err = capture_err
    server.handle_request({
        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}}
    })
    assert len(errors) == 1
    assert errors[0]["code"] == -32601


def test_notification_no_response():
    server = get_server()
    responses = []

    def capture_ok(req_id, result):
        responses.append(result)

    server.ok = capture_ok
    # Notifications have no id
    server.handle_request({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    assert len(responses) == 0
