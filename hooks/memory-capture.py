#!/usr/bin/env python3
"""
RepoMem Stop hook — captures session observations into memory.db.
Wired as a Stop hook in ~/.claude/settings.json.
Never blocks — exits 0 always.
"""
from __future__ import annotations
import sys
import json
import os

# Add RepoMem to path
REPOMEM_INSTALL = os.environ.get(
    "REPOMEM_INSTALL",
    os.path.expanduser("~/.repomem/lib")
)
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)

        # Extract session summary from Stop hook data
        # Claude Code Stop hook provides: stop_reason, session_id, etc.
        session_id = data.get("session_id") or data.get("sessionId") or ""
        stop_reason = data.get("stop_reason", "")

        # Get any summary from the data
        summary = data.get("summary") or data.get("message", {}).get("content", "")
        if isinstance(summary, list):
            # Extract text from content blocks
            summary = " ".join(
                block.get("text", "") for block in summary
                if isinstance(block, dict) and block.get("type") == "text"
            )

        if not summary:
            summary = f"Session ended. Reason: {stop_reason}"

        from repomem.capture import capture_session
        count = capture_session(
            session_summary=summary,
            session_id=session_id or None,
        )

        if count > 0:
            from repomem.capture import detect_project
            project, _, _ = detect_project()
            print(f"\033[90m[RepoMem] {count} observation(s) captured → {project}\033[0m")

    except ImportError:
        # RepoMem not installed — silent skip
        pass
    except Exception:
        # Never block the session stop
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
