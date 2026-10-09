"""The decision path of an analysis graph: what an analyst reads to sign (≈50 nodes instead of hundreds).

class → criteria → questionnaire answers (or the decisive evidence of the state judge) → evidence → the cited
fragment; plus the coherence records, the divergences and, for criteria in the insufficient column, the missing
links. Searches, rules without evidence and the rows used by the checks stay in the full graph (audit)."""

from typing import TypeVar

N = TypeVar("N")
E = TypeVar("E")
ALWAYS = {"project", "class", "criterion", "answer", "coherence", "divergence"}


def decision_graph(nodes: list[N], edges: list[E]) -> tuple[list[N], list[E]]:
    """Works on any node/edge objects with `node_id`/`kind`/`props` and `source`/`target`/`kind`."""
    by_id = {n.node_id: n for n in nodes}
    keep = {i for i, n in by_id.items() if n.kind in ALWAYS}
    insufficient = {i for i, n in by_id.items() if n.kind == "criterion" and (n.props or {}).get("column") == "insuficiente"}
    evidence = {e.source for e in edges if e.kind in ("fundamenta", "decisiva") and e.source in by_id}
    keep |= evidence
    keep |= {e.target for e in edges if e.kind == "cita" and e.source in evidence}  # the cited fragments
    keep |= {e.target for e in edges if e.kind == "liga" and e.source in keep}  # testimony × record of divergences
    gaps = {e.source for e in edges if e.kind == "afeta" and e.target in insufficient
            and by_id.get(e.source) is not None and by_id[e.source].kind == "gap"}
    keep |= gaps
    keep |= {e.target for e in edges if e.kind == "cita" and e.source in gaps}
    kept_nodes = [by_id[i] for i in by_id if i in keep]
    kept_edges = [e for e in edges if e.source in keep and e.target in keep]
    return kept_nodes, kept_edges
