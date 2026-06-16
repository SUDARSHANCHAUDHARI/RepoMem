"""Tests for the `answer` grounded-retrieval primitive and mcp-config command."""
import json
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


def run_cli(*args):
    from repomem.cli import main
    old_argv, old_stdout = sys.argv, sys.stdout
    sys.argv = ["repomem"] + list(args)
    sys.stdout = out = StringIO()
    try:
        try:
            main()
        except SystemExit:
            pass
    finally:
        sys.argv, sys.stdout = old_argv, old_stdout
    return out.getvalue()


def test_answer_no_memory_returns_notice():
    from repomem.answer import answer
    assert "No memory found" in answer("anything at all?")


def test_answer_cites_observation_id():
    run_cli("add", "--type", "decision",
            "--summary", "stdlib only, no external dependencies",
            "--detail", "AGPL complicates forks so we stay pure Python")
    out = run_cli("answer", "why stdlib only?")
    assert "stdlib" in out
    assert "#" in out                      # an #id citation is present
    assert "Cite #id" in out               # grounding instruction present


def test_answer_respects_char_cap():
    from repomem.answer import answer
    long_detail = "x" * 5000
    run_cli("add", "--type", "learning",
            "--summary", "performance tuning notes for the cache layer",
            "--detail", long_detail)
    block = answer("cache performance", max_chars=300)
    assert len(block) <= 320               # cap + truncation marker slack


def test_mcp_config_emits_valid_entry():
    out = run_cli("mcp-config", "--client", "cursor")
    assert "mcpServers" in out             # tells user where to put it
    # Strip leading comment lines, parse the JSON body.
    body = "\n".join(l for l in out.splitlines() if not l.startswith("#"))
    parsed = json.loads(body)
    assert "repomem" in parsed
    assert parsed["repomem"]["args"][0].endswith("mcp_server.py")


def test_mcp_config_supports_multiple_clients():
    for client in ("claude", "cursor", "windsurf", "cline", "codex"):
        out = run_cli("mcp-config", "--client", client)
        assert "mcp_server.py" in out
