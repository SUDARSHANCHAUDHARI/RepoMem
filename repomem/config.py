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
KNOWN_FOLDERS = [
    "AndroidApps",
    "AIProjects",
    "SignageProjects",
    "WebAppsProjects",
    "FromAndroidToWebApps",
    "AIDashboards",
    "RustProjects",
    "CyberSecurity",
    "Plugins",
    "Practice",
    "QA Projects",
]

# ── Topic keywords for auto-tagging ────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "room":        ["room", "database", "dao", "entity", "migration", "sqlite"],
    "hilt":        ["hilt", "di", "dependency injection", "inject", "module", "component"],
    "compose":     ["compose", "composable", "recomposition", "LazyColumn", "scaffold"],
    "agp":         ["agp", "android gradle", "build.gradle", "gradle plugin"],
    "kotlin":      ["kotlin", "coroutine", "flow", "stateflow", "suspend"],
    "networking":  ["retrofit", "ktor", "okhttp", "api", "network", "http"],
    "navigation":  ["navigation", "navgraph", "navhost", "deeplink", "backstack"],
    "viewmodel":   ["viewmodel", "uistate", "uievent", "uieffect"],
    "datastore":   ["datastore", "preferences", "sharedpreferences"],
    "build":       ["build", "gradle", "ksp", "kapt", "compileSdk", "targetSdk"],
    "release":     ["release", "play store", "aab", "signing", "keystore"],
    "performance": ["performance", "recomposition", "slow", "lag", "memory leak"],
    "security":    ["security", "proguard", "obfuscation", "keystore", "certificate"],
}


def ensure_dirs() -> None:
    """Create all required directories."""
    for d in [REPOMEM_DIR, SYNC_DIR, EXPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
