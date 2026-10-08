"""Schema do grafo de evidências (pydantic) — spec 5.6."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    type: str  # projeto | criterio | regra | evidencia | fonte | web_source | query | gap
    label: str = ""
    props: dict = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    type: str  # sustenta | contraria | cita | retornou | compoe | neutra
    props: dict = Field(default_factory=dict)


class Graph(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


CRITERIA = ["novidade", "criatividade", "incerteza", "sistematizacao", "reprodutibilidade"]


def rule_criterion(rule_id: str) -> str:
    """NOV-D1 → novidade; T1 → transversal; CHK-* → compartilhada."""
    if rule_id.startswith("CHK-"):
        return "compartilhada"
    if rule_id.startswith("T"):
        return "transversal"
    prefix = rule_id.split("-")[0]
    return {
        "NOV": "novidade",
        "CRI": "criatividade",
        "INC": "incerteza",
        "SIS": "sistematizacao",
        "REP": "reprodutibilidade",
    }.get(prefix, "transversal")