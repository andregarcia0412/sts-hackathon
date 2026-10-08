"""Builder do grafo: upsert idempotente, ID determinístico, versões + meta."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from ai_microservice.graph.schema import CRITERIA, Edge, Graph, Node, rule_criterion
from ai_microservice.graph.store import GraphStore


def _hid(*parts: str) -> str:
    h = hashlib.sha256("\x1f".join(parts).encode("utf-8"))
    return h.hexdigest()[:16]


def evidence_id(regra_id: str, fonte: str, quote: str) -> str:
    """ID determinístico: hash(regra_id + fonte + quote) — reanálise não duplica."""
    return "ev-" + _hid(regra_id, fonte, quote)


def source_id(fonte: str) -> str:
    if fonte.startswith("http"):
        return "web-" + _hid(fonte)
    return "frag-" + _hid(fonte)


class GraphBuilder:
    def __init__(self, store: GraphStore, project_id: str):
        self.store = store
        self.project_id = project_id
        self._nodes: dict[str, Node] = {}
        self._edges: dict[tuple[str, str, str], Edge] = {}
        self._ensure_backbone()

    # ------------------------------------------------------------------ backbone
    def _ensure_backbone(self):
        pid = f"projeto:{self.project_id}"
        self._upsert(Node(id=pid, type="projeto", label=self.project_id))
        for c in CRITERIA:
            cid = f"criterio:{c}"
            self._upsert(Node(id=cid, type="criterio", label=c, props={"criterio": c}))
            self._edge(pid, cid, "compoe")

    def _upsert(self, node: Node) -> Node:
        if node.id in self._nodes:
            # mescla props (última escrita ganha por chave)
            self._nodes[node.id].props.update(node.props)
            return self._nodes[node.id]
        self._nodes[node.id] = node
        return node

    def _edge(self, source: str, target: str, type_: str, props: dict | None = None):
        key = (source, target, type_)
        if key not in self._edges:
            self._edges[key] = Edge(source=source, target=target, type=type_, props=props or {})
        elif props:
            self._edges[key].props.update(props)

    # ------------------------------------------------------------------ regras
    def ensure_rule(self, regra_id: str, props: dict | None = None) -> Node:
        rid = f"regra:{regra_id}"
        node = self._upsert(
            Node(id=rid, type="regra", label=regra_id, props=props or {"id": regra_id})
        )
        crit = rule_criterion(regra_id)
        if crit in CRITERIA:
            cid = f"criterio:{crit}"
            self._edge(cid, rid, "compoe")
        else:
            pid = f"projeto:{self.project_id}"
            self._edge(pid, rid, "compoe")
        return node

    # ------------------------------------------------------------------ evidências
    def add_evidence(
        self,
        regra_id: str,
        fonte: str,
        quote: str,
        polaridade: str,
        natureza: str,
        justificativa: str,
        mode: str = "llm",
        model: str | None = None,
    ) -> Node:
        self.ensure_rule(regra_id)
        eid = evidence_id(regra_id, fonte, quote)
        props = {
            "regra_id": regra_id,
            "fonte": fonte,
            "quote": quote,
            "polaridade": polaridade,
            "natureza": natureza,
            "justificativa": justificativa,
            "mode": mode,
        }
        if model:
            props["model"] = model
        node = self._upsert(Node(id=eid, type="evidencia", label=quote[:60], props=props))
        rid = f"regra:{regra_id}"
        etype = {"sustenta": "sustenta", "contraria": "contraria"}.get(polaridade, "neutra")
        self._edge(eid, rid, etype)
        # fonte citada
        sid = source_id(fonte)
        if fonte.startswith("http"):
            self._upsert(
                Node(id=sid, type="web_source", label=fonte[:80], props={"url": fonte})
            )
        else:
            self._upsert(Node(id=sid, type="fonte", label=fonte, props={"ancora": fonte}))
        self._edge(eid, sid, "cita")
        return node

    def add_rejected_evidence(self, regra_id: str, fonte: str, quote: str, motivo: str) -> Node:
        """Evidência rejeitada pelo gate vira gap registrado (nunca silêncio)."""
        rid = regra_id.split(":", 1)[-1]
        self.ensure_rule(rid, props={"id": rid})
        return self.add_gap(regra_id=f"gate:{rid}", motivo=f"citação inválida: {motivo} | fonte={fonte} quote={quote[:120]}")

    def add_gap(self, regra_id: str, motivo: str) -> Node:
        rid = f"regra:{regra_id}" if not regra_id.startswith("gate:") else f"regra:{regra_id.split(':', 1)[1]}"
        gid = "gap-" + _hid(regra_id, motivo)
        node = self._upsert(
            Node(id=gid, type="gap", label=motivo[:80], props={"regra_id": regra_id, "motivo": motivo})
        )
        self._edge(gid, rid, "neutra")
        return node

    def add_rule_gap(self, regra_id: str, motivo: str) -> Node:
        """Regra sem evidência: gap ligado à regra."""
        self.ensure_rule(regra_id)
        rid = f"regra:{regra_id}"
        gid = "gap-" + _hid(regra_id, motivo)
        node = self._upsert(
            Node(id=gid, type="gap", label=motivo[:80], props={"regra_id": regra_id, "motivo": motivo})
        )
        self._edge(gid, rid, "neutra")
        return node

    # ------------------------------------------------------------------ web
    def add_web_source(self, url: str, trecho: str, captured_at: str, title: str | None = None) -> Node:
        sid = source_id(url)
        node = self._upsert(
            Node(
                id=sid,
                type="web_source",
                label=title or url[:80],
                props={"url": url, "trecho_citado": trecho, "captured_at": captured_at},
            )
        )
        return node

    def add_query(
        self, original: str, sanitized: str, rule_id: str | None = None, removed: list | None = None
    ) -> Node:
        qid = "query-" + _hid(original, sanitized)
        node = self._upsert(
            Node(
                id=qid,
                type="query",
                label=sanitized[:80],
                props={
                    "original": original,
                    "sanitized": sanitized,
                    "removed": removed or [],
                    "rule_id": rule_id,
                },
            )
        )
        pid = f"projeto:{self.project_id}"
        self._edge(qid, pid, "retornou")
        return node

    def link_query_to_source(self, original: str, sanitized: str, url: str) -> None:
        qid = "query-" + _hid(original, sanitized)
        sid = source_id(url)
        if qid in self._nodes and sid in self._nodes:
            self._edge(qid, sid, "retornou")

    # ------------------------------------------------------------------ saída
    def build(self) -> Graph:
        return Graph(nodes=list(self._nodes.values()), edges=list(self._edges.values()))

    def save_version(self, catalog_version: str, model: str, extra_meta: dict | None = None) -> str:
        graph = self.build()
        meta = {
            "project_id": self.project_id,
            "catalog_version": catalog_version,
            "model": model,
            "analyst_model": model,
            "manifest_hash": None,
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra_meta:
            meta.update(extra_meta)
        return self.store.save_version(self.project_id, graph, meta)