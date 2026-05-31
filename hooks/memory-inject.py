#!/usr/bin/env python3
"""
RepoMem SessionStart hook — injects project memory as system message.
Wired as a SessionStart hook in ~/.claude/settings.json.
Never blocks — exits 0 always, returns empty {} on any error.
"""
from __future__ import annotations
import sys
import json
import os

REPOMEM_INSTALL = os.environ.get(
    "REPOMEM_INSTALL",
    os.path.expanduser("~/.repomem/lib")
)
if REPOMEM_INSTALL not in sys.path:
    sys.path.insert(0, REPOMEM_INSTALL)


def main():
    try:
        raw = sys.stdin.read()

        from repomem.inject import build_system_message
        result = build_system_message()

        if result:
            print(json.dumps(result))

    except ImportError:
        pass
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
