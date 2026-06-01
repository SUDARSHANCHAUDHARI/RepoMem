"""
RepoMem graphify integration — enriches observations with graph context.
Reads graphify-out/graph.json from current project.

Provides:
- God node detection (high edge count → high blast radius)
- Community tagging (group related files)
- Session-start warnings for high-blast-radius files touched in session

Usage:
  repomem graphify --project my-app
  repomem graphify --scan   (scan current repo)
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from . import db


# ── Graph loading ─────────────────────────────────────────────────────────────

def _find_graph_json(repo_path: Optional[str] = None) -> Optional[Path]:
    """Find graphify-out/graph.json for current or specified repo."""
    if repo_path:
        p = Path(repo_path) / "graphify-out" / "graph.json"
        return p if p.exists() else None

    # Try cwd and parents
    cwd = Path(os.getcwd())
    for d in [cwd] + list(cwd.parents)[:3]:
        p = d / "graphify-out" / "graph.json"
        if p.exists():
            return p
    return None


def load_graph(repo_path: Optional[str] = None) -> Optional[dict]:
    """Load and parse graph.json. Returns None if not found."""
    graph_path = _find_graph_json(repo_path)
    if not graph_path:
        return None
    try:
        return json.loads(graph_path.read_text())
    except Exception:
        return None


# ── Analysis ──────────────────────────────────────────────────────────────────

def get_god_nodes(graph: dict, threshold: int = 10) -> list[dict]:
    """
    Return nodes with edge count >= threshold (God Nodes = high blast radius).
    Sorted by edge count descending.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Count edges per node
    edge_count: dict[str, int] = {}
    for e in edges:
        src = e.get("source", e.get("from", ""))
        tgt = e.get("target", e.get("to", ""))
        edge_count[src] = edge_count.get(src, 0) + 1
        edge_count[tgt] = edge_count.get(tgt, 0) + 1

    god_nodes = []
    for node in nodes:
        node_id = node.get("id", node.get("name", ""))
        count = edge_count.get(node_id, 0)
        if count >= threshold:
            god_nodes.append({
                "id": node_id,
                "label": node.get("label", node_id),
                "edge_count": count,
                "type": node.get("type", "unknown"),
            })

    return sorted(god_nodes, key=lambda n: n["edge_count"], reverse=True)


def get_communities(graph: dict) -> dict[str, list[str]]:
    """Extract community groupings from graph if available."""
    communities: dict[str, list[str]] = {}
    nodes = graph.get("nodes", [])
    for node in nodes:
        community = str(node.get("community", node.get("group", "")))
        if community and community != "":
            node_id = node.get("id", node.get("name", ""))
            communities.setdefault(community, []).append(node_id)
    return communities


def enrich_observation(obs_id: int, project: str, text: str,
                        graph: dict) -> list[str]:
    """
    Check if any God Nodes are mentioned in the observation text.
    Returns list of God Node labels found.
    Tags the observation via entity linking with type='god_node'.
    """
    god_nodes = get_god_nodes(graph)
    found = []
    text_lower = text.lower()

    for node in god_nodes:
        label = node["label"]
        if label.lower() in text_lower or node["id"].lower() in text_lower:
            found.append(label)
            # Record as entity
            with db.db() as conn:
                existing = conn.execute(
                    "SELECT id FROM entities WHERE name=? AND type='god_node'",
                    (label,)
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE entities SET mention_count=mention_count+1 WHERE id=?",
                        (existing["id"],)
                    )
                    entity_id = existing["id"]
                else:
                    cur = conn.execute(
                        "INSERT INTO entities (name, type, project, first_seen, mention_count) VALUES (?,?,?,date('now'),1)",
                        (label, "god_node", project)
                    )
                    entity_id = cur.lastrowid

                conn.execute(
                    "INSERT OR IGNORE INTO entity_links (entity_id, obs_id) VALUES (?,?)",
                    (entity_id, obs_id)
                )

    return found


# ── Session-start context ─────────────────────────────────────────────────────

def build_graph_context(project: str, repo_path: Optional[str] = None) -> str:
    """
    Build a short graph-aware context block for session injection.
    Shows top God Nodes so Claude knows high-blast-radius files.
    """
    graph = load_graph(repo_path)
    if not graph:
        return ""

    god_nodes = get_god_nodes(graph, threshold=10)[:5]
    if not god_nodes:
        return ""

    lines = ["║ GRAPH: GOD NODES (high blast radius)\n"]
    for n in god_nodes:
        lines.append(f"║  ⚡ {n['label']} ({n['edge_count']} edges)\n")
    return "".join(lines)


# ── CLI entry point ────────────────────────────────────────────────────────────

def analyze(project: str, repo_path: Optional[str] = None,
            threshold: int = 10) -> dict:
    """Full graphify analysis for a project. Returns summary dict."""
    graph = load_graph(repo_path)
    if not graph:
        return {"error": "graph.json not found — run `graphify .` first"}

    god_nodes = get_god_nodes(graph, threshold=threshold)
    communities = get_communities(graph)

    node_count = len(graph.get("nodes", []))
    edge_count = len(graph.get("edges", []))

    return {
        "project": project,
        "nodes": node_count,
        "edges": edge_count,
        "god_nodes": god_nodes,
        "communities": len(communities),
        "graph_path": str(_find_graph_json(repo_path)),
    }
