"""
RepoMem answer — grounded retrieval for question answering.

Unlike memory layers that call an LLM to synthesize an answer, RepoMem assumes
the *host* (Claude Code, Cursor, etc.) is the LLM. So `answer` does no model
call and needs no API key: it retrieves the most relevant memories and returns
a compact, #id-cited grounding block the agent answers from.
"""
from __future__ import annotations
from typing import Optional

from . import db
from .search import search

# Keep the grounding block well under the injection budget so it never
# crowds out the surrounding conversation.
ANSWER_MAX_CHARS = 1500

# Words too common to signal relevance when matching decisions/errors.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did", "why",
    "how", "what", "when", "where", "which", "who", "we", "i", "you", "it",
    "to", "of", "in", "on", "for", "and", "or", "this", "that", "with", "use",
}


def _tokens(text: str) -> set[str]:
    """Lowercase word set, minus stopwords and 1-char noise."""
    return {
        w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split()
        if len(w) > 1 and w not in _STOPWORDS
    }


def answer(question: str, project: Optional[str] = None,
           limit: int = 8, max_chars: int = ANSWER_MAX_CHARS) -> str:
    """
    Build a grounding block for `question`.

    Pulls observations (FTS5), plus decisions and unresolved errors that share
    keywords with the question, and formats them with #id citations. Returns a
    string capped at `max_chars`, or a "no memory" line if nothing matches.
    """
    db.init_db()
    q_tokens = _tokens(question)

    lines: list[str] = [
        "Answer the question using ONLY the memories below. Cite #id. "
        "If they don't cover it, say so.",
        f"Q: {question}",
        "",
    ]

    def _relevant(text: str) -> bool:
        return bool(q_tokens & _tokens(text))

    # 1. Observations — FTS5 ranked. Feed keywords OR-joined so a natural-language
    #    question ("why stdlib only?") matches on any term instead of requiring all.
    fts_query = " OR ".join(q_tokens) if q_tokens else question
    observations = search(fts_query, project=project, limit=limit)
    if observations:
        lines.append("MEMORIES:")
        for o in observations:
            detail = f" — {o.detail[:160]}" if o.detail else ""
            lines.append(f"  #{o.id} [{o.type}] {o.summary}{detail} ({o.date})")

    # 2. Decisions sharing keywords with the question (decisions aren't FTS-indexed).
    decisions = [
        d for d in db.get_decisions(scope=project)
        if _relevant(d["decision"] + " " + (d.get("topic") or ""))
    ]
    if decisions:
        lines.append("DECISIONS:")
        for d in decisions[:5]:
            scope = "global" if d["scope"] == "ALL" else d["scope"]
            lines.append(f"  [{scope}/{d['topic']}] {d['decision']}")

    # 3. Unresolved errors sharing keywords with the question.
    errors = [
        e for e in db.get_unresolved_errors(project=project)
        if _relevant(e["error_text"] + " " + (e.get("fix") or ""))
    ]
    if errors:
        lines.append("UNRESOLVED ERRORS:")
        for e in errors[:3]:
            fix = f" → fix: {e['fix'][:80]}" if e["fix"] else ""
            lines.append(f"  ❌ {e['error_text'][:120]}{fix}")

    if not (observations or decisions or errors):
        return f"No memory found for: {question}"

    block = "\n".join(lines)
    if len(block) > max_chars:
        block = block[:max_chars].rsplit("\n", 1)[0] + "\n  … (truncated)"
    return block
