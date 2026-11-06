"""Tests for install.sh pieces, run in isolation on temp files (never the real ~/.claude).

The crontab block has its own suite in test_install_crontab.py.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

INSTALL = Path(__file__).parent.parent / "install.sh"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")


def _snippet(start: str, end: str) -> str:
    """Lines of install.sh from the first line matching `start` to the next matching `end`."""
    lines = INSTALL.read_text().splitlines()
    i = next(n for n, l in enumerate(lines) if re.match(start, l))
    j = next(n for n in range(i + 1, len(lines)) if re.match(end, lines[n]))
    return "\n".join(lines[i:j + 1]) + "\n"


def _run_bash(script: str, env: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    path = tmp_path / "snippet.sh"
    path.write_text("set -euo pipefail\n" + script)
    return subprocess.run(["bash", str(path)], env=env, capture_output=True, text=True, timeout=30)


def test_install_sh_syntax():
    subprocess.run(["bash", "-n", str(INSTALL)], check=True)


def _wiring_script():
    text = INSTALL.read_text()
    return text.split("<<'PYTHON'\n", 1)[1].split("\nPYTHON\n", 1)[0]


def test_settings_wiring_backup_atomic_and_no_mcp(tmp_path):
    script = tmp_path / "wire.py"
    script.write_text(_wiring_script())
    real = tmp_path / "real"
    real.mkdir()
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    settings = real / "settings.json"
    original = {"model": "x", "hooks": {"Stop": [
        {"hooks": [{"type": "command", "command":
                    "REPOMEM_INSTALL=/old/lib /usr/bin/python3 ~/.claude/hooks/memory-capture.py"}]},
        {"hooks": [{"type": "command", "command": "/mine/memory-capture.py --custom"}]},
    ]}}
    settings.write_text(json.dumps(original))
    link = cfg / "settings.json"
    link.symlink_to(settings)
    hooks_dir = cfg / "hooks"

    for _ in range(2):
        subprocess.run([sys.executable, str(script), "/usr/bin/python3", "/lib", str(link),
                        str(hooks_dir)], check=True, capture_output=True, text=True)

    assert link.is_symlink()
    assert json.loads((real / "settings.json.bak").read_text())["model"] == "x"
    data = json.loads(settings.read_text())
    assert "mcpServers" not in data
    stop = [h["command"] for e in data["hooks"]["Stop"] for h in e["hooks"]]
    assert stop == [f"REPOMEM_INSTALL=/lib /usr/bin/python3 {hooks_dir}/memory-capture.py",
                    "/mine/memory-capture.py --custom"]
    start = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert start == [f"REPOMEM_INSTALL=/lib /usr/bin/python3 {hooks_dir}/memory-inject.py"]
    assert not list(real.glob(".settings.*.tmp"))


def _mcp_snippet():
    return "GREEN= YELLOW= NC=\n" + _snippet(r"^MCP_ADD=", r"^fi$")


def test_mcp_uses_claude_cli_when_present(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$ARGS_OUT"\n')
    fake.chmod(0o755)
    env = {"PATH": f"{bindir}:/usr/bin:/bin", "ARGS_OUT": str(tmp_path / "args"),
           "REPOMEM_DIR": "/rm", "PYTHON3_PATH": "/usr/bin/python3"}
    r = _run_bash(_mcp_snippet(), env, tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "args").read_text().splitlines() == [
        "mcp", "add", "--scope", "user", "repomem", "-e", "REPOMEM_INSTALL=/rm/lib",
        "--", "/usr/bin/python3", "/rm/lib/server/mcp_server.py"]
    assert "MCP server wired" in r.stdout


def test_mcp_prints_command_when_claude_missing(tmp_path):
    env = {"PATH": "/usr/bin:/bin", "REPOMEM_DIR": "/rm", "PYTHON3_PATH": "/usr/bin/python3"}
    if shutil.which("claude", path=env["PATH"]):
        pytest.skip("claude on system PATH")
    r = _run_bash(_mcp_snippet(), env, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "claude mcp add --scope user repomem" in r.stdout
