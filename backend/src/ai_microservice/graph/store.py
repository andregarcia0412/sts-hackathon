"""Interface GraphStore + JSONFileGraphStore (MongoGraphStore documentado como stub)."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from ai_microservice.graph.schema import Edge, Graph, Node


class GraphStore(ABC):
    """Interface de persistência do grafo (spec 5.6).

    MongoGraphStore (futuro): mesma interface, coleções `nodes`/`edges`,
    consultas com $graphLookup. Entra sem tocar no resto do código.
    """

    @abstractmethod
    def add_nodes(self, project_id: str, nodes: list[Node]) -> None: ...

    @abstractmethod
    def add_edges(self, project_id: str, edges: list[Edge]) -> None: ...

    @abstractmethod
    def save_version(
        self, project_id: str, graph: Graph, meta: dict
    ) -> str:
        """Grava nova versão e retorna o rótulo (v1, v2, ...). Nunca sobrescreve."""

    @abstractmethod
    def get_graph(self, project_id: str, version: str | None = None) -> dict: ...

    @abstractmethod
    def diff_versions(self, project_id: str, v_old: str, v_new: str) -> dict: ...


class JSONFileGraphStore(GraphStore):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def _project_dir(self, project_id: str) -> Path:
        return self.base_dir / project_id

    def _versions(self, project_id: str) -> list[str]:
        d = self._project_dir(project_id)
        if not d.exists():
            return []
        return sorted(
            (p.name for p in d.iterdir() if p.is_dir() and p.name.startswith("v")),
            key=lambda n: int(n[1:]),
        )

    def add_nodes(self, project_id: str, nodes: list[Node]) -> None:
        raise NotImplementedError("use save_version — grava por versão")

    def add_edges(self, project_id: str, edges: list[Edge]) -> None:
        raise NotImplementedError("use save_version — grava por versão")

    def save_version(self, project_id: str, graph: Graph, meta: dict) -> str:
        versions = self._versions(project_id)
        next_n = len(versions) + 1
        vdir = self._project_dir(project_id) / f"v{next_n}"
        vdir.mkdir(parents=True, exist_ok=True)
        nodes = [n.model_dump() for n in graph.nodes]
        edges = [e.model_dump() for e in graph.edges]
        (vdir / "nodes.json").write_text(
            json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (vdir / "edges.json").write_text(
            json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        meta = dict(meta)
        meta["version"] = f"v{next_n}"
        meta["saved_at"] = datetime.now(timezone.utc).isoformat()
        (vdir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return f"v{next_n}"

    def get_graph(self, project_id: str, version: str | None = None) -> dict:
        versions = self._versions(project_id)
        if not versions:
            raise FileNotFoundError(f"sem grafo para {project_id}")
        v = version or versions[-1]
        vdir = self._project_dir(project_id) / v
        nodes = json.loads((vdir / "nodes.json").read_text(encoding="utf-8"))
        edges = json.loads((vdir / "edges.json").read_text(encoding="utf-8"))
        meta = json.loads((vdir / "meta.json").read_text(encoding="utf-8"))
        return {"version": v, "nodes": nodes, "edges": edges, "meta": meta}

    def diff_versions(self, project_id: str, v_old: str, v_new: str) -> dict:
        old = self.get_graph(project_id, v_old)
        new = self.get_graph(project_id, v_new)
        old_nodes = {n["id"]: n for n in old["nodes"]}
        new_nodes = {n["id"]: n for n in new["nodes"]}
        old_edges = {(e["source"], e["target"], e["type"]) for e in old["edges"]}
        new_edges = {(e["source"], e["target"], e["type"]) for e in new["edges"]}
        return {
            "v_old": v_old,
            "v_new": v_new,
            "added": {
                "nodes": [new_nodes[i] for i in sorted(new_nodes.keys() - old_nodes.keys())],
                "edges": [
                    {"source": s, "target": t, "type": ty}
                    for s, t, ty in sorted(new_edges - old_edges)
                ],
            },
            "removed": {
                "nodes": [old_nodes[i] for i in sorted(old_nodes.keys() - new_nodes.keys())],
                "edges": [
                    {"source": s, "target": t, "type": ty}
                    for s, t, ty in sorted(old_edges - new_edges)
                ],
            },
            "changed_polarity": [
                {"id": i, "old": old_nodes[i]["props"].get("polaridade"),
                 "new": new_nodes[i]["props"].get("polaridade")}
                for i in sorted(old_nodes.keys() & new_nodes.keys())
                if old_nodes[i]["props"].get("polaridade")
                != new_nodes[i]["props"].get("polaridade")
            ],
        }