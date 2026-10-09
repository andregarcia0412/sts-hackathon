"""Module 3: evidence graph (the system's memory). Pure function from the analysis results to nodes/edges."""

import hashlib

from backend.catalog.models import Catalog
from backend.checks.models import ChecksReport
from backend.criteria.schemas import CriterionResult
from backend.extraction.schema import CanonicalProject
from backend.graph.classify import CLASS_LABELS, ClassSuggestion
from backend.graph.consistency import ConsistencyReport
from backend.graph.models import EdgeData, NodeData
from backend.graph.scoring import RuleScore, score_criterion
from backend.graph.states import CriterionState

CLASS_NODE = "class:suggested"


def _short(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:12]


class _Graph:
    def __init__(self, analysis_id: str) -> None:
        self.analysis_id = analysis_id
        self.nodes: dict[str, NodeData] = {}
        self.edges: dict[tuple[str, str, str], EdgeData] = {}

    def node(self, node_id: str, kind: str, label: str, **props) -> str:
        if node_id not in self.nodes:
            self.nodes[node_id] = NodeData(analysis_id=self.analysis_id, node_id=node_id, kind=kind, label=label, props=props)
        return node_id

    def edge(self, source: str, kind: str, target: str, **props) -> None:
        key = (source, kind, target)
        if key not in self.edges:
            self.edges[key] = EdgeData(analysis_id=self.analysis_id, source=source, target=target, kind=kind, props=props)


def build_graph(
    analysis_id: str,
    canonical: CanonicalProject,
    catalog: Catalog,
    results: dict[str, CriterionResult],
    scores: dict[str, list[RuleScore]],
    states: dict[str, CriterionState],
    suggestion: ClassSuggestion,
    consistency: ConsistencyReport | None = None,
    checks: ChecksReport | None = None,
) -> tuple[list[NodeData], list[EdgeData]]:
    g = _Graph(analysis_id)
    project = g.node(f"project:{canonical.project_code}", "project", canonical.context.title or canonical.project_code,
                     code=canonical.project_code, data_referencia=str(canonical.context.data_referencia or ""))
    g.node(CLASS_NODE, "class", CLASS_LABELS.get(suggestion.suggested_class or "", "Sem classe automática"),
           suggested_class=suggestion.suggested_class, inconsistent=suggestion.inconsistent, reason=suggestion.reason,
           path=suggestion.path, incomplete=suggestion.incomplete,
           caveat=suggestion.caveat.model_dump() if suggestion.caveat else None,
           missing_link=suggestion.missing_link.model_dump() if suggestion.missing_link else None)
    g.edge(CLASS_NODE, "de", project)

    for criterion, result in results.items():
        info = catalog.criteria[criterion]
        state = states.get(criterion)
        rule_scores = {s.rule_id: s for s in scores.get(criterion, [])}
        criterion_node = g.node(
            f"criterion:{criterion}", "criterion", info.nome,
            criterion=criterion, state=state.state if state else None, column=state.column if state else None,
            llm_state=state.llm_state if state else None, justification=state.justification if state else "",
            gates=state.gates if state else [], error=state.error if state else None,
            score=score_criterion(list(rule_scores.values())), normative_source=info.fonte_normativa,
        )
        g.edge(criterion_node, "compoe", CLASS_NODE)
        for run in result.rules:
            rule = catalog.get(run.rule_id)
            score = rule_scores.get(run.rule_id)
            rule_node = g.node(
                f"rule:{run.rule_id}", "rule", rule.titulo if rule else run.rule_id,
                rule_id=run.rule_id, status=run.status, reason=run.reason, note=run.note,
                score=score.score if score else None, positive=score.positive if score else 0,
                negative=score.negative if score else 0, in_mean=score.in_mean if score else False,
                normative_sources=rule.fontes_normativas if rule else [],
            )
            g.edge(rule_node, "compoe", criterion_node)
            for item in run.evidences:
                evidence_node = g.node(
                    f"evidence:{item.id}", "evidence", item.quote[:80],
                    rule_id=item.rule_id, polarity=item.polarity, quote=item.quote, explanation=item.explanation,
                    origin=item.origin, nature=item.nature, query=item.query, source_id=item.source_id,
                    source_alias=item.source_alias, counted=item.id in (score.counted_evidence_ids if score else []),
                    adjustment=item.adjustment.model_dump() if item.adjustment else None,
                )
                g.edge(evidence_node, "sustenta" if item.polarity == "positiva" else "contraria", rule_node)
                source_node = _source_node(g, canonical, result, item.source_id)
                g.edge(evidence_node, "cita", source_node)
        for evidence_id_ in state.decisive_evidence_ids if state else []:
            if f"evidence:{evidence_id_}" in g.nodes:
                g.edge(f"evidence:{evidence_id_}", "decisiva", criterion_node)
        for answer in state.answers if state else []:
            node = g.node(f"answer:{criterion}:{answer.pergunta}", "answer", f"{answer.pergunta} = {answer.effective}",
                          criterion=criterion, decision_rule=state.decision_rule, effective=answer.effective,
                          **answer.model_dump())
            g.edge(node, "responde", criterion_node)
            for evidence_id_ in answer.evidencias:
                if f"evidence:{evidence_id_}" in g.nodes:
                    g.edge(f"evidence:{evidence_id_}", "fundamenta", node)
        if state and state.coherence:
            coherence = state.coherence
            node = g.node(f"coherence:{criterion}", "coherence",
                          f"Coerência score × estado: {coherence.status}", criterion=criterion,
                          final_state=state.state, **coherence.model_dump())
            g.edge(node, "afeta", criterion_node)
            for evidence_id_ in state.decisive_evidence_ids:
                if f"evidence:{evidence_id_}" in g.nodes:
                    g.edge(node, "cita", f"evidence:{evidence_id_}")
        for divergence in result.divergences:
            node = g.node(f"divergence:{_short(divergence.testimony_fragment_id + divergence.record_fragment_id)}",
                          "divergence", "Divergência entrevista × registro", statement=divergence.statement,
                          criterion=criterion)
            g.edge(node, "liga", _source_node(g, canonical, result, divergence.testimony_fragment_id), role="depoimento")
            g.edge(node, "liga", _source_node(g, canonical, result, divergence.record_fragment_id), role="registro",
                   prevalece=True)
            g.edge(node, "afeta", criterion_node)
        for link in result.missing_links:
            node = g.node(f"gap:{_short(criterion + link.description)}", "gap", link.description,
                          evidence_to_request=link.evidence_to_request, criterion=criterion)
            g.edge(node, "afeta", criterion_node)
            for fragment_id in link.fragment_ids:
                g.edge(node, "cita", _source_node(g, canonical, result, fragment_id))
        for entry in result.search_log:
            node = g.node(f"search:{_short(criterion + entry.front + entry.original_query + entry.base)}", "search",
                          entry.sanitized_query or "(não enviada)", **entry.model_dump(mode="json"))
            g.edge(node, "registra", "rule:NOV-W8" if "rule:NOV-W8" in g.nodes else criterion_node)
            for source_id in entry.selected:
                if f"source:{source_id}" in g.nodes or any(s.id == source_id for s in result.web_sources):
                    g.edge(node, "trouxe", _source_node(g, canonical, result, source_id))
    for check_id, check in (checks.results.items() if checks else []):
        node = g.node(f"check:{check_id}", "check", check_id, status=check.status, facts=check.facts,
                      notes=check.notes, version=checks.version)
        for fragment_id in check.fragment_ids:
            if canonical.fragment(fragment_id):
                g.edge(node, "usa", _source_node(g, canonical, CriterionResult(criterion=""), fragment_id))
        for rule in catalog.rules:
            if check_id in rule.checagens and f"rule:{rule.id}" in g.nodes:
                g.edge(node, "alimenta", f"rule:{rule.id}")
    if consistency and (consistency.neutralized or consistency.inverted):
        node = g.node("consistency:analysis", "consistency", "Consistência entre critérios",
                      **consistency.model_dump())
        for item in consistency.neutralized:
            if f"rule:{item.by_rule}" in g.nodes:
                g.edge(node, "por", f"rule:{item.by_rule}")
            if f"evidence:{item.evidence_id}" in g.nodes:
                g.edge(node, "neutraliza", f"evidence:{item.evidence_id}")
    return list(g.nodes.values()), list(g.edges.values())


def _source_node(g: _Graph, canonical: CanonicalProject, result: CriterionResult, source_id: str) -> str:
    node_id = f"source:{source_id}"
    if node_id in g.nodes:
        return node_id
    fragment = canonical.fragment(source_id)
    if fragment:
        return g.node(node_id, "source", fragment.alias, origin="doc", fragment_id=fragment.id, alias=fragment.alias,
                      file=fragment.file, page=fragment.page, nature=fragment.nature, text=fragment.text)
    web = next((s for s in result.web_sources if s.id == source_id), None)
    if web:
        return g.node(node_id, "source", web.title, origin="web", url=web.url, base=web.base, front=web.front,
                      published_date=str(web.published_date or ""), prior_art=web.prior_art, date_label=web.date_label,
                      captured_at=web.captured_at.isoformat(), text=web.snippet)
    return g.node(node_id, "source", source_id, origin="unknown")
