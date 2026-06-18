#!/usr/bin/env python3
"""
RepoMem retrieval benchmark harness.

Measures recall@k: for each example, ingest its memories into a throwaway DB,
run a query, and check whether any of the top-k results contains the gold answer
string. Works for both retrieval modes:

    python3 bench/run_benchmark.py --dataset bench/sample_dataset.jsonl --mode fts
    python3 bench/run_benchmark.py --dataset bench/sample_dataset.jsonl --mode semantic --k 5

`--mode semantic` requires the optional extra: pip install repomem[semantic]

Dataset format — one JSON object per line (JSONL):

    {
      "id": "q1",
      "memories": [{"type": "learning", "summary": "...", "detail": "..."}, ...],
      "question": "natural-language query",
      "answer_contains": "substring that a correct memory must contain"
    }

See bench/README.md for converting LongMemEval / LoCoMo into this format.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
import time

# Make the repo importable when run from the project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _ingest(memories: list[dict]) -> None:
    from repomem import db
    from repomem.models import Observation
    from datetime import date

    with db.db() as conn:
        if not conn.execute("SELECT id FROM sessions WHERE id='bench'").fetchone():
            conn.execute(
                "INSERT INTO sessions (id, project, folder, repo_path, started_at) "
                "VALUES ('bench','Bench','','',?)",
                (int(time.time()),),
            )
    for m in memories:
        db.save_observation(Observation(
            session_id="bench", project="Bench", folder="",
            type=m.get("type", "learning"), topic=m.get("topic", ""),
            summary=m["summary"], detail=m.get("detail", ""),
            date=date.today().isoformat(), created_at=int(time.time()),
        ))


def _hit(results, needle: str) -> bool:
    needle = needle.lower()
    return any(needle in f"{r.summary} {r.detail}".lower() for r in results)


def _query_for_mode(question: str, mode: str) -> str:
    """Each mode queries the way it really does in the product.

    FTS5 ANDs every token, so a raw question ("why no external deps?") misses —
    RepoMem's own `answer` primitive OR-tokenizes keywords, so the fair FTS
    baseline does the same. Semantic search takes the natural question directly.
    """
    if mode == "fts":
        from repomem.answer import _tokens
        toks = _tokens(question)
        return " OR ".join(toks) if toks else question
    return question


def run(dataset_path: str, mode: str, k: int) -> dict:
    from repomem import db
    from repomem.search import search

    total = hits = 0
    with open(dataset_path) as f:
        examples = [json.loads(line) for line in f if line.strip()]

    for ex in examples:
        # Fresh DB per example so memories don't leak across questions.
        tmp = tempfile.mkdtemp(prefix="repomem-bench-")
        os.environ["REPOMEM_DIR"] = tmp
        db.init_db()
        _ingest(ex["memories"])
        query = _query_for_mode(ex["question"], mode)
        results = search(query, limit=k, semantic=(mode == "semantic"))
        total += 1
        if _hit(results, ex["answer_contains"]):
            hits += 1

    return {"mode": mode, "k": k, "examples": total,
            "recall_at_k": round(hits / total, 4) if total else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser(description="RepoMem retrieval benchmark")
    ap.add_argument("--dataset", required=True, help="Path to a JSONL dataset")
    ap.add_argument("--mode", choices=["fts", "semantic"], default="fts")
    ap.add_argument("--k", type=int, default=5, help="top-k cutoff for recall")
    args = ap.parse_args()

    result = run(args.dataset, args.mode, args.k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
