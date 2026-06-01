"""Tests for repomem/config.py — path resolution and env override."""
import os
import pytest
from pathlib import Path


def test_default_repomem_dir_is_home_repomem(tmp_path, monkeypatch):
    monkeypatch.delenv("REPOMEM_DIR", raising=False)
    import importlib
    import repomem.config as cfg
    importlib.reload(cfg)
    assert cfg.REPOMEM_DIR == Path.home() / ".repomem"


def test_repomem_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    import importlib
    import repomem.config as cfg
    importlib.reload(cfg)
    assert cfg.REPOMEM_DIR == tmp_path


def test_db_path_under_repomem_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path))
    import importlib
    import repomem.config as cfg
    importlib.reload(cfg)
    assert cfg.DB_PATH == tmp_path / "memory.db"


def test_ensure_dirs_creates_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path / "repomem"))
    import importlib
    import repomem.config as cfg
    importlib.reload(cfg)
    cfg.ensure_dirs()
    assert cfg.REPOMEM_DIR.exists()
    assert cfg.SYNC_DIR.exists()
    assert cfg.EXPORT_DIR.exists()


def test_ensure_dirs_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("REPOMEM_DIR", str(tmp_path / "repomem"))
    import importlib
    import repomem.config as cfg
    importlib.reload(cfg)
    cfg.ensure_dirs()
    cfg.ensure_dirs()  # should not raise


def test_obs_types_contains_required_types():
    import repomem.config as cfg
    required = {"bugfix", "decision", "upgrade", "pending", "pattern",
                "warning", "learning", "error"}
    assert required == set(cfg.OBS_TYPES)


def test_max_inject_chars_is_2000():
    import repomem.config as cfg
    assert cfg.MAX_INJECT_CHARS == 2000


def test_topic_keywords_all_lowercase():
    import repomem.config as cfg
    for topic, keywords in cfg.TOPIC_KEYWORDS.items():
        for kw in keywords:
            assert kw == kw.lower(), f"keyword '{kw}' in topic '{topic}' is not lowercase"


def test_private_tags_are_correct():
    import repomem.config as cfg
    assert cfg.PRIVATE_TAG_START == "<private>"
    assert cfg.PRIVATE_TAG_END == "</private>"
