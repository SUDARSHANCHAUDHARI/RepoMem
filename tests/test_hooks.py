"""Tests for hooks/memory-capture.py and hooks/memory-inject.py."""
import json
import sys
import os
import importlib
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


HOOKS_DIR = Path(__file__).parent.parent / "hooks"


def load_hook(name: str):
    """Dynamically load a hook module by filename."""
    import importlib.util
    path = HOOKS_DIR / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── memory-capture.py ────────────────────────────────────────────────────────

class TestMemoryCapture:

    def test_exits_0_on_empty_stdin(self, monkeypatch):
        mod = load_hook("memory-capture.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: ""))
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0

    def test_exits_0_on_invalid_json(self, monkeypatch):
        mod = load_hook("memory-capture.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "not json"))
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0

    def test_exits_0_on_import_error(self, monkeypatch):
        mod = load_hook("memory-capture.py")
        payload = json.dumps({"session_id": "test", "summary": "did stuff"})
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: payload))
        # Simulate repomem not installed
        with patch.dict("sys.modules", {"repomem.capture": None}):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0

    def test_exits_0_on_capture_exception(self, monkeypatch, tmp_path):
        mod = load_hook("memory-capture.py")
        payload = json.dumps({"session_id": "test123", "summary": "fixed a bug"})
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: payload))
        mock_capture = MagicMock(side_effect=RuntimeError("db error"))
        with patch.dict("sys.modules", {
            "repomem.capture": MagicMock(capture_session=mock_capture)
        }):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0

    def test_extracts_session_id_from_payload(self, monkeypatch, tmp_path):
        mod = load_hook("memory-capture.py")
        payload = json.dumps({"session_id": "abc123"})
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: payload))
        captured_args = {}

        def fake_capture(session_summary, session_id=None):
            captured_args["session_id"] = session_id
            captured_args["summary"] = session_summary
            return 0

        mock_module = MagicMock()
        mock_module.capture_session = fake_capture
        mock_module.detect_project = MagicMock(return_value=("TestProject", "/tmp", "remote"))

        with patch.dict("sys.modules", {"repomem.capture": mock_module}):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0
        assert captured_args.get("session_id") == "abc123"

    def _run_with_transcript(self, monkeypatch, transcript_path):
        mod = load_hook("memory-capture.py")
        payload = json.dumps({
            "session_id": "xyz",
            "transcript_path": str(transcript_path),
            "cwd": "/tmp",
            "hook_event_name": "Stop",
            "stop_hook_active": False,
        })
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: payload))
        captured = {}

        def fake_capture(session_summary, session_id=None):
            captured["summary"] = session_summary
            captured["session_id"] = session_id
            return 0

        mock_module = MagicMock()
        mock_module.capture_session = fake_capture
        mock_module.detect_project = MagicMock(return_value=("P", "/tmp", ""))

        with patch.dict("sys.modules", {"repomem.capture": mock_module}):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0
        return captured

    def test_reads_summary_from_transcript(self, monkeypatch, tmp_path):
        transcript = tmp_path / "session.jsonl"
        lines = [
            {"type": "user", "message": {"role": "user", "content": "Fix the crash in UserRepo"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Looking."},
                {"type": "tool_use", "name": "Read", "input": {}},
            ]}},
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "content": "file body"},
            ]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "text", "text": "Fixed the crash."},
                {"type": "text", "text": "Added null check."},
            ]}},
        ]
        transcript.write_text(
            "\n".join(json.dumps(l) for l in lines) + "\nnot json\n", encoding="utf-8"
        )
        captured = self._run_with_transcript(monkeypatch, transcript)
        summary = captured["summary"]
        assert captured["session_id"] == "xyz"
        assert "User: Fix the crash in UserRepo" in summary
        assert "Assistant: Fixed the crash. Added null check." in summary
        assert "Looking." not in summary
        assert "file body" not in summary

    def test_truncates_long_transcript_text(self, monkeypatch, tmp_path):
        mod = load_hook("memory-capture.py")
        transcript = tmp_path / "long.jsonl"
        transcript.write_text(json.dumps(
            {"type": "user", "message": {"role": "user", "content": "x" * 5000}}
        ), encoding="utf-8")
        summary = mod.summarize_transcript(str(transcript))
        assert summary == "User: " + "x" * mod.MAX_PART

    def test_missing_transcript_still_captures_and_exits_0(self, monkeypatch, tmp_path):
        captured = self._run_with_transcript(monkeypatch, tmp_path / "does-not-exist.jsonl")
        assert captured["session_id"] == "xyz"
        assert captured["summary"] == "Session ended (no transcript text)."


# ── memory-inject.py ─────────────────────────────────────────────────────────

class TestMemoryInject:

    def test_exits_0_always(self, monkeypatch):
        mod = load_hook("memory-inject.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: ""))
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0

    def test_exits_0_on_import_error(self, monkeypatch):
        mod = load_hook("memory-inject.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "{}"))
        with patch.dict("sys.modules", {"repomem.inject": None}):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0

    def test_exits_0_on_exception(self, monkeypatch):
        mod = load_hook("memory-inject.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "{}"))
        mock_inject = MagicMock()
        mock_inject.build_system_message = MagicMock(side_effect=RuntimeError("db gone"))
        with patch.dict("sys.modules", {"repomem.inject": mock_inject}):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0

    def test_prints_json_when_context_available(self, monkeypatch, capsys):
        mod = load_hook("memory-inject.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "{}"))
        expected = {"system": "You have memory context here."}
        mock_inject = MagicMock()
        mock_inject.build_system_message = MagicMock(return_value=expected)
        with patch.dict("sys.modules", {"repomem.inject": mock_inject}):
            with pytest.raises(SystemExit):
                mod.main()
        captured = capsys.readouterr()
        assert json.loads(captured.out) == expected

    def test_prints_nothing_when_no_context(self, monkeypatch, capsys):
        mod = load_hook("memory-inject.py")
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "{}"))
        mock_inject = MagicMock()
        mock_inject.build_system_message = MagicMock(return_value=None)
        with patch.dict("sys.modules", {"repomem.inject": mock_inject}):
            with pytest.raises(SystemExit):
                mod.main()
        captured = capsys.readouterr()
        assert captured.out.strip() == ""
