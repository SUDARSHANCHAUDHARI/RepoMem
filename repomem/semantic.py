"""
RepoMem semantic search — OPTIONAL, opt-in. Requires `pip install repomem[semantic]`.

Keeps RepoMem's zero-dependency guarantee intact: nothing here is imported unless
the user explicitly asks for semantic search (`search --semantic`), and even then it
fails soft back to FTS5 if the extra isn't installed. Embeddings live in their own
`embeddings` table created on demand — the core schema is never touched.
"""
from __future__ import annotations
import importlib
import importlib.util
import json
from typing import Optional

from . import db
from .models import SearchResult

# The optional extra is loaded via importlib (never a static `import`), so the
# default install stays genuinely zero-dependency and the no-external-imports
# guard stays honest. Nothing here runs unless the user opts into --semantic.
_EXTRA = "sentence_transformers"
MODEL_NAME = "all-MiniLM-L6-v2"   # 384-dim, small, the sentence-transformers default
_MODEL = None


def is_available() -> bool:
    """True iff the optional `sentence-transformers` extra is installed."""
    try:
        return importlib.util.find_spec(_EXTRA) is not None
    except Exception:
        return False


def _get_model():
    global _MODEL
    if _MODEL is None:
        st = importlib.import_module(_EXTRA)
        _MODEL = st.SentenceTransformer(MODEL_NAME)
    return _MODEL


def _embed(text: str) -> list[float]:
    """Return a normalized embedding as a plain Python list (no numpy leaks out)."""
    vec = _get_model().encode(text, normalize_embeddings=True)
    return [float(x) for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    """Dot product — inputs are already L2-normalized, so this is cosine similarity."""
    return sum(x * y for x, y in zip(a, b))


def _ensure_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS embeddings (
               obs_id INTEGER PRIMARY KEY,
               model  TEXT NOT NULL,
               vec    TEXT NOT NULL
           )"""
    )


def index_missing(conn, model_name: str = MODEL_NAME) -> int:
    """Embed and store any live observation lacking an embedding for this model. Returns count indexed."""
    _ensure_table(conn)
    rows = conn.execute(
        """SELECT o.id, o.summary, o.detail
             FROM observations o
             LEFT JOIN embeddings e ON e.obs_id = o.id AND e.model = ?
            WHERE e.obs_id IS NULL AND o.is_stale = 0 AND o.is_archived = 0""",
        (model_name,),
    ).fetchall()
    for r in rows:
        text = f"{r['summary'] or ''} {r['detail'] or ''}".strip()
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (obs_id, model, vec) VALUES (?, ?, ?)",
            (r["id"], model_name, json.dumps(_embed(text))),
        )
    conn.commit()
    return len(rows)


def semantic_search(query: str, project: Optional[str] = None,
                    obs_type: Optional[str] = None, limit: int = 20) -> list[SearchResult]:
    """Rank live observations by cosine similarity to the query embedding."""
    qvec = _embed(query)
    with db.db() as conn:
        index_missing(conn, MODEL_NAME)
        sql = (
            "SELECT o.id, o.project, o.type, o.topic, o.summary, o.date, "
            "       o.confidence, o.detail, e.vec "
            "  FROM observations o JOIN embeddings e "
            "    ON e.obs_id = o.id AND e.model = ? "
            " WHERE o.is_stale = 0 AND o.is_archived = 0"
        )
        params: list = [MODEL_NAME]
        if project:
            sql += " AND o.project = ?"
            params.append(project)
        if obs_type:
            sql += " AND o.type = ?"
            params.append(obs_type)
        rows = conn.execute(sql, params).fetchall()

    ranked = sorted(
        rows, key=lambda r: _cosine(qvec, json.loads(r["vec"])), reverse=True
    )
    return [
        SearchResult(
            id=r["id"], project=r["project"], type=r["type"], topic=r["topic"],
            summary=r["summary"], date=r["date"], confidence=r["confidence"],
            detail=r["detail"],
        )
        for r in ranked[:limit]
    ]
