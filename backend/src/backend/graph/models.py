from typing import Any

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class NodeData(BaseModel):
    analysis_id: str
    node_id: str  # "rule:NOV-D2", "evidence:ev-…", "source:PRJ21-EV06#2"
    kind: str
    label: str
    props: dict[str, Any] = Field(default_factory=dict)


class EdgeData(BaseModel):
    analysis_id: str
    source: str
    target: str
    kind: str
    props: dict[str, Any] = Field(default_factory=dict)


class GraphNode(Document, NodeData):
    class Settings:
        name = "nodes"
        indexes = [IndexModel([("analysis_id", ASCENDING), ("node_id", ASCENDING)], unique=True)]


class GraphEdge(Document, EdgeData):
    class Settings:
        name = "edges"
        indexes = [
            IndexModel([("analysis_id", ASCENDING), ("target", ASCENDING)]),
            IndexModel([("analysis_id", ASCENDING), ("source", ASCENDING)]),
        ]
