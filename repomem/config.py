"""
RepoMem configuration — paths, settings, env vars.
All paths respect REPOMEM_DIR env override.
"""
from __future__ import annotations
import os
from pathlib import Path

# ── Base directory ─────────────────────────────────────────────────────────────
REPOMEM_DIR = Path(os.environ.get("REPOMEM_DIR", Path.home() / ".repomem"))
DB_PATH     = REPOMEM_DIR / "memory.db"
LOG_PATH    = REPOMEM_DIR / "repomem.log"
SYNC_DIR    = REPOMEM_DIR / "sync"
EXPORT_DIR  = REPOMEM_DIR / "exports"

# ── Injection settings ─────────────────────────────────────────────────────────
MAX_INJECT_CHARS    = 2000   # hard cap on context injection
MAX_OBS_PER_PROJECT = 10     # max observations per project in inject
MAX_DECISIONS       = 20     # max global decisions in inject
MAX_PENDING         = 5      # max pending tasks in inject

# ── Capture settings ───────────────────────────────────────────────────────────
PRIVATE_TAG_START = "<private>"
PRIVATE_TAG_END   = "</private>"

# ── Observation types ──────────────────────────────────────────────────────────
OBS_TYPES = [
    "bugfix",     # what was broken, how we fixed it
    "decision",   # architectural choice made
    "upgrade",    # version / dependency change
    "pending",    # next task / blocker
    "pattern",    # reusable solution
    "warning",    # watch out for this
    "learning",   # new knowledge gained
    "error",      # crash / exception seen
]

# ── Known project folders ──────────────────────────────────────────────────────
# Used to tag observations with their parent folder for filtering.
# Add your own folder names here — any folder in your repo root that groups projects.
# Example: if you keep repos in ~/code/mobile/, ~/code/web/, ~/code/tools/, add those.
KNOWN_FOLDERS = [
    "mobile",
    "web",
    "backend",
    "tools",
    "plugins",
    "experiments",
    "services",
    "apps",
    "libs",
    "scripts",
]

# ── Topic keywords for auto-tagging ────────────────────────────────────────────
# Maps topic names to keyword lists. An observation is tagged with the topic
# whose keywords appear most often in the observation text.
# Customize for your tech stack — add, remove, or rename topics freely.
# Short topic keywords that must match as whole words to avoid false positives.
# e.g. "di" would match "audio", "media", "studio" without word-boundary matching.
SHORT_TOPIC_KEYWORDS: set[str] = {"di", "ui", "sql", "api", "orm", "r8", "ksp"}

TOPIC_KEYWORDS = {
    "database":    ["database", "migration", "schema", "query", "sql", "sqlite",
                    "dao", "entity", "orm", "room", "prisma", "drizzle"],
    "di":          ["dependency injection", "inject", "di", "hilt", "dagger",
                    "ioc", "container", "wire", "provider"],
    "ui":          ["ui", "compose", "composable", "component", "widget",
                    "layout", "render", "view", "screen", "scaffold"],
    "build":       ["build", "gradle", "webpack", "vite", "cmake", "make",
                    "ci", "pipeline", "compile", "lint", "ksp", "kapt"],
    "networking":  ["api", "http", "network", "request", "response", "retrofit",
                    "ktor", "okhttp", "fetch", "axios", "rest", "graphql"],
    "state":       ["state", "viewmodel", "stateflow", "livedata", "store",
                    "redux", "zustand", "observable", "reactive", "flow"],
    "auth":        ["auth", "authentication", "login", "token", "session",
                    "oauth", "jwt", "permission", "credential"],
    "storage":     ["storage", "cache", "preferences", "datastore", "sharedprefs",
                    "localstorage", "keyvalue", "persist"],
    "release":     ["release", "deploy", "publish", "version", "tag",
                    "signing", "store", "upload", "distribution"],
    "performance": ["performance", "slow", "lag", "memory", "leak", "optimize",
                    "profile", "benchmark", "latency", "throughput"],
    "security":    ["security", "vulnerability", "obfuscation", "certificate",
                    "ssl", "tls", "encryption", "proguard", "r8"],
    "testing":     ["test", "mock", "fake", "stub", "assert", "coverage",
                    "unit", "integration", "e2e", "fixture"],
}


def ensure_dirs() -> None:
    """Create all required directories."""
    for d in [REPOMEM_DIR, SYNC_DIR, EXPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
