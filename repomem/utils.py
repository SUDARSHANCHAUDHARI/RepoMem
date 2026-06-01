"""
RepoMem shared utilities.
"""
from __future__ import annotations
import re


def text_similarity(a: str, b: str) -> float:
    """Word-overlap Jaccard similarity (0.0–1.0). No external deps."""
    wa = set(re.sub(r"[^a-z0-9 ]", "", a.lower()).split())
    wb = set(re.sub(r"[^a-z0-9 ]", "", b.lower()).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))
