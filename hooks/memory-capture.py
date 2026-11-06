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


MAX_PART = 1000  # chars kept from each of the first prompt and the last reply


def _text_of(content) -> str:
    """Text of a message content: a string, or a list of blocks with type "text"."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return ""


def summarize_transcript(path: str) -> str:
    """First user prompt + last assistant text from a Claude Code JSONL transcript.
    Returns "" when the file is missing, unreadable or has no text."""
    first_user = last_assistant = ""
    try:
        with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                msg = entry.get("message")
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role") or entry.get("type")
                text = _text_of(msg.get("content"))
                if not text:
                    continue
                if role == "user" and not first_user:
                    first_user = text
                elif role == "assistant":
                    last_assistant = text
    except (OSError, TypeError):
        return ""
    parts = []
    if first_user:
        parts.append(f"User: {first_user[:MAX_PART]}")
    if last_assistant:
        parts.append(f"Assistant: {last_assistant[:MAX_PART]}")
    return "\n".join(parts)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)

        # Claude Code Stop hook input: session_id, transcript_path, cwd,
        # hook_event_name, stop_hook_active. No summary — build it from the transcript.
        session_id = data.get("session_id") or ""
        transcript_path = data.get("transcript_path") or ""
        summary = summarize_transcript(transcript_path) if transcript_path else ""
        if not summary:
            # Keep recording the session even when the transcript is missing or empty
            summary = "Session ended (no transcript text)."

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
