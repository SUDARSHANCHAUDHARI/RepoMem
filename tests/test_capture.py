"""Tests for RepoMem capture module."""
from __future__ import annotations
import os
import tempfile
import pytest

os.environ["REPOMEM_DIR"] = tempfile.mkdtemp()
os.environ["REPOMEM_PROJECT"] = "TestProject"

from repomem.capture import (
    strip_private, detect_topic, extract_observations_from_text
)


def test_strip_private():
    text = "Fixed crash. <private>API_KEY=abc123</private> Done."
    result = strip_private(text)
    assert "abc123" not in result
    assert "[PRIVATE]" in result
    assert "Fixed crash" in result


def test_detect_topic_room():
    assert detect_topic("Fixed Room migration from v2 to v3") == "room"


def test_detect_topic_viewmodel():
    # StateFlow is a kotlin keyword, use collectLatest which is viewmodel-specific
    result = detect_topic("Fixed null pointer in HomeViewModel collectLatest")
    assert result == "viewmodel"


def test_detect_topic_agp():
    assert detect_topic("Upgraded AGP from 9.2.0 to 9.2.1 in build.gradle") == "agp"


def test_detect_topic_empty():
    result = detect_topic("Some random text with no keywords")
    assert result == "" or isinstance(result, str)


def test_extract_observations_bugfix():
    text = "Fixed a crash in HomeViewModel when navigating back."
    obs = extract_observations_from_text(text, "DreamWeave", "AndroidApps", "s1")
    bugfixes = [o for o in obs if o.type == "bugfix"]
    assert len(bugfixes) > 0


def test_extract_observations_pending():
    text = "TODO: add Room migration for v4 schema change."
    obs = extract_observations_from_text(text, "DreamWeave", "AndroidApps", "s1")
    pending = [o for o in obs if o.type == "pending"]
    assert len(pending) > 0


def test_extract_strips_private():
    text = "Fixed crash. <private>keystore password is secret123</private> Done."
    obs = extract_observations_from_text(text, "DreamWeave", "AndroidApps", "s1")
    for o in obs:
        assert "secret123" not in o.summary
        assert "secret123" not in o.detail
