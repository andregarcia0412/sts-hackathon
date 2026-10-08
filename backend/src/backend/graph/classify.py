"""Class from the vector of criterion states (exact answer-key patterns; mixed vectors → tree + flag)."""

from typing import Literal

from pydantic import BaseModel, Field

from backend.graph.states import Caveat, CriterionState, MissingLinkInfo

SuggestedClass = Literal["eligible", "eligible_with_caveats", "not_eligible", "insufficient_evidence"]
CLASS_LABELS: dict[str, str] = {
    "eligible": "Elegível",
    "eligible_with_caveats": "Com ressalvas",
    "not_eligible": "Não elegível",
    "insufficient_evidence": "Evidência insuficiente",
}
CORE = ("NOV", "CRI", "INC")
SCOPE_STATE = "DOCUMENTADA NO ESCOPO"
LIMIT_STATE = "DOCUMENTADA COM LIMITE"


class ClassSuggestion(BaseModel):
    suggested_class: SuggestedClass | None
    inconsistent: bool
    reason: str
    path: list[str] = Field(default_factory=list)
    caveat: Caveat | None = None
    missing_link: MissingLinkInfo | None = None
    incomplete: list[str] = Field(default_factory=list)


def _missing_link(states: dict[str, CriterionState]) -> MissingLinkInfo:
    links = [s.missing_link for s in states.values() if s.column == "insuficiente" and s.missing_link]
    return MissingLinkInfo(
        elo_ausente="; ".join(dict.fromkeys(l.elo_ausente for l in links if l.elo_ausente)) or None,
        evidencias_a_solicitar=list(dict.fromkeys(item for l in links for item in l.evidencias_a_solicitar)),
    )


def _finish(cls: SuggestedClass, states: dict[str, CriterionState], inconsistent: bool, reason: str,
            path: list[str]) -> ClassSuggestion:
    suggestion = ClassSuggestion(suggested_class=cls, inconsistent=inconsistent, reason=reason, path=path)
    if cls == "eligible_with_caveats":
        suggestion.caveat = states["REP"].caveat or Caveat()
        if not suggestion.caveat.complete():
            suggestion.incomplete.append("Com ressalvas exige recorte sustentado, limitação e evidência necessária")
    if cls == "insufficient_evidence":
        suggestion.missing_link = _missing_link(states)
        if not suggestion.missing_link.elo_ausente:
            suggestion.incomplete.append("Evidência insuficiente exige o elo ausente e as evidências a solicitar")
    return suggestion


def classify(states: dict[str, CriterionState]) -> ClassSuggestion:
    missing = [c for c, s in states.items() if s.state is None or s.column is None]
    if missing:
        return ClassSuggestion(suggested_class=None, inconsistent=True,
                               reason=f"critério(s) sem estado: {', '.join(missing)} — sem classe automática")
    columns = {c: s.column for c, s in states.items()}
    rep = states["REP"].state
    if all(col == "pd" for col in columns.values()):
        if rep == SCOPE_STATE:
            return _finish("eligible", states, False, "P&D nos 5 critérios, reprodução no escopo", ["padrão exato"])
        if rep == LIMIT_STATE:
            return _finish("eligible_with_caveats", states, False, "P&D nos 5 critérios, reprodução com limite", ["padrão exato"])
    if all(col == "rotina" for col in columns.values()):
        return _finish("not_eligible", states, False, "rotina nos 5 critérios", ["padrão exato"])
    if all(col == "insuficiente" for col in columns.values()):
        return _finish("insufficient_evidence", states, False, "insuficiente nos 5 critérios", ["padrão exato"])

    # Mixed vector: decision tree of the historical cases, as a suggestion for the analyst (T7).
    path = ["combinação fora dos padrões do gabarito"]
    core_insufficient = [c for c in CORE if columns[c] == "insuficiente"]
    if core_insufficient:
        path.append(f"núcleo alegado não verificável ({', '.join(core_insufficient)})")
        return _finish("insufficient_evidence", states, True, path[-1], path)
    path.append("núcleo verificável")
    core_routine = [c for c in CORE if columns[c] == "rotina"]
    if core_routine:
        path.append(f"referência anterior/configuração já fornecia a função ({', '.join(core_routine)})")
        return _finish("not_eligible", states, True, path[-1], path)
    path.append("novidade, criatividade e incerteza no recorte")
    if columns["SIS"] != "pd" or columns["REP"] != "pd":
        path.append("hipótese não confrontada com comparadores de forma registrada (SIS/REP fora da coluna P&D)")
        return _finish("insufficient_evidence", states, True, path[-1], path)
    if rep == LIMIT_STATE:
        path.append("lacuna técnica dentro da pretensão original")
        return _finish("eligible_with_caveats", states, True, path[-1], path)
    path.append("sem lacuna dentro da pretensão")
    return _finish("eligible", states, True, path[-1], path)
