"""
RepoMem entity linking — extract named entities from observations.
Entities: PascalCase classes, snake_case files, known library names.
Links entities to observations for richer search.
"""
from __future__ import annotations
import re
from typing import Optional

from . import db


# ── Entity extraction ─────────────────────────────────────────────────────────

# PascalCase class/object names (min 2 words joined, e.g. HomeViewModel)
_PASCAL = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b")

# snake_case file references (e.g. build.gradle.kts, HomeViewModel.kt)
_SNAKE_FILE = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\b")

# Known library/tool names (exact match, case-insensitive)
KNOWN_LIBS = {
    "hilt", "room", "retrofit", "ktor", "compose", "navigation",
    "datastore", "workmanager", "ksp", "kapt", "gradle", "agp",
    "firebase", "crashlytics", "coroutines", "flow", "stateflow",
    "viewmodel", "livedata", "glide", "coil", "okhttp", "moshi",
    "gson", "kotlinx", "serialization", "paging", "lifecycle",
}


def extract_entities(text: str) -> list[tuple[str, str]]:
    """
    Extract entities from text.
    Returns list of (name, type) tuples.
    Types: class | file | library
    """
    found: dict[str, str] = {}

    # PascalCase → class
    for m in _PASCAL.finditer(text):
        name = m.group(1)
        if name not in found:
            found[name] = "class"

    # snake_case with extension → file
    for m in _SNAKE_FILE.finditer(text):
        name = m.group(1)
        # Only keep if it looks like a filename (has a dot with known ext)
        if "." in name and not name.startswith("http"):
            found[name] = "file"

    # Known libs → library
    text_lower = text.lower()
    for lib in KNOWN_LIBS:
        if re.search(r"\b" + re.escape(lib) + r"\b", text_lower):
            canonical = lib.capitalize()
            if canonical not in found:
                found[canonical] = "library"

    return list(found.items())


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_or_create_entity(conn, name: str, entity_type: str, project: Optional[str]) -> int:
    row = conn.execute(
        "SELECT id, mention_count FROM entities WHERE name=? AND type=?",
        (name, entity_type)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE entities SET mention_count=mention_count+1 WHERE id=?",
            (row["id"],)
        )
        return row["id"]
    cur = conn.execute(
        "INSERT INTO entities (name, type, project, first_seen, mention_count) VALUES (?,?,?,date('now'),1)",
        (name, entity_type, project or "")
    )
    return cur.lastrowid


def link_observation(obs_id: int, project: Optional[str], text: str) -> int:
    """
    Extract entities from text and link them to an observation.
    Returns number of entities linked.
    """
    entities = extract_entities(text)
    if not entities:
        return 0

    count = 0
    with db.db() as conn:
        for name, etype in entities:
            entity_id = _get_or_create_entity(conn, name, etype, project)
            # Link (ignore if already linked)
            conn.execute(
                "INSERT OR IGNORE INTO entity_links (entity_id, obs_id) VALUES (?,?)",
                (entity_id, obs_id)
            )
            count += 1
    return count


def get_entities(project: Optional[str] = None, min_mentions: int = 1) -> list[dict]:
    """List known entities, optionally filtered by project."""
    with db.db() as conn:
        if project:
            rows = conn.execute("""
                SELECT * FROM entities
                WHERE (project=? OR project='') AND mention_count >= ?
                ORDER BY mention_count DESC
            """, (project, min_mentions)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM entities WHERE mention_count >= ?
                ORDER BY mention_count DESC
            """, (min_mentions,)).fetchall()
        return [dict(r) for r in rows]


def get_observations_for_entity(entity_name: str) -> list[dict]:
    """Find all observations mentioning a given entity."""
    with db.db() as conn:
        rows = conn.execute("""
            SELECT o.* FROM observations o
            JOIN entity_links el ON el.obs_id = o.id
            JOIN entities e ON e.id = el.entity_id
            WHERE e.name = ? AND o.is_archived = 0
            ORDER BY o.created_at DESC
        """, (entity_name,)).fetchall()
        return [dict(r) for r in rows]
