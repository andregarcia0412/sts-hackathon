"""Coherence gate: the criterion score (evidence layer) against the state chosen by the judge (state layer).

The code never picks the state from the score (the class is not a mean). It detects a contradiction, asks the judge
once more with the contradiction spelled out, and, if it persists, keeps the judge's state and flags it for review.
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.catalog.models import Catalog
from backend.criteria.schemas import CriterionResult
from backend.graph.options import JudgeOptions

Strength = Literal["forte_positivo", "forte_negativo"]
# In NOV, CRI and INC positive evidence speaks of R&D. In SIS and REP it speaks of documentation: a well documented
# acceptance test scores high and still sits in the negative column, so only the insufficient state contradicts it.
CORE = ("NOV", "CRI", "INC")
CONFLICT_NOTE = "estado em conflito com as evidências: revisar"
NUMERIC_NATURES = {"registro_primario", "derivado"}


class Coherence(BaseModel):
    score: int
    rules_with_evidence: int
    strength: Strength
    original_state: str | None  # state before the new judgement
    original_source: Literal["juiz", "gate"]
    choices: list[str] = Field(default_factory=list)  # what the new judgement was asked to choose between
    rejudged: bool = False
    status: Literal["resolvida", "incoerente"]


class Contradiction(BaseModel):
    criterion: str
    score: int
    rules_with_evidence: int
    strength: Strength
    state: str | None
    column: str | None
    source: Literal["juiz", "gate"]
    gate_rules: list[str] = Field(default_factory=list)
    choices: list[str]


def strength_of(score: int | None, rules_with_evidence: int, options: JudgeOptions) -> Strength | None:
    if score is None or rules_with_evidence < options.coherence_min_rules:
        return None
    if score >= options.coherence_high:
        return "forte_positivo"
    if score <= options.coherence_low:
        return "forte_negativo"
    return None


def check_coherence(criterion: str, state: str | None, column: str | None, llm_column: str | None,
                    gate_conflicts: list[str], score: int | None, rules_with_evidence: int, catalog: Catalog,
                    options: JudgeOptions, include_gate_conflicts: bool = True,
                    forced_by_gate: bool = False) -> Contradiction | None:
    strength = strength_of(score, rules_with_evidence, options)
    if strength is None or state is None:
        return None
    vocabulary = catalog.criteria[criterion].estados
    base = {"criterion": criterion, "score": score, "rules_with_evidence": rules_with_evidence,
            "strength": strength, "state": state, "column": column}
    # The numeric-record gate turned a positive judgement into the insufficient column: that is a missing record,
    # not the judge's caution, and asking again cannot change it.
    numeric_gate = column == "insuficiente" and llm_column == "pd"
    if criterion in CORE:
        if include_gate_conflicts and gate_conflicts and strength == "forte_positivo":
            return Contradiction(**base, source="gate", gate_rules=list(gate_conflicts),
                                 choices=[*vocabulary.positivo, vocabulary.negativo])
        if strength == "forte_positivo" and column == "insuficiente" and not numeric_gate:
            return Contradiction(**base, source="juiz", choices=[*vocabulary.positivo, vocabulary.negativo])
        # The judge itself chose routine against a strong positive score (a gate forcing it is a separate case):
        # the costly error of calling R&D routine — asked again, never overturned by the code.
        if strength == "forte_positivo" and column == "rotina" and not forced_by_gate:
            return Contradiction(**base, source="juiz", choices=[*vocabulary.positivo, vocabulary.negativo])
        if strength == "forte_negativo" and column == "pd":
            return Contradiction(**base, source="juiz", choices=[vocabulary.negativo, vocabulary.indeterminado])
        return None
    if strength == "forte_positivo" and state == vocabulary.indeterminado and not numeric_gate:
        return Contradiction(**base, source="juiz", choices=[*vocabulary.positivo, vocabulary.negativo])
    return None


def contradiction_block(contradiction: Contradiction, result: CriterionResult) -> str:
    """Data assembled by the code (not project text) for the new judgement."""
    evidences = [e for r in result.rules for e in r.evidences]
    positives = [e for e in evidences if e.polarity == "positiva"]
    primary = [e for e in positives if e.nature in NUMERIC_NATURES]
    choices = " | ".join(contradiction.choices)
    lines = [f"O score das evidências deste critério é {contradiction.score} ({contradiction.rules_with_evidence} "
             f"regras com evidência; {len(positives)} evidências positivas, {len(primary)} com registro primário "
             f"ou derivado)."]
    if contradiction.source == "gate":
        rules = ", ".join(contradiction.gate_rules)
        lines.append(f"A regra {rules} (a referência anterior ou a configuração já fornecia a função?) tem evidência "
                     f"negativa predominante, o que contradiz o score. O gate não foi aplicado.")
        lines.append(f"Reavalie escolhendo entre: {choices}.")
        lines.append(f"Escolha a coluna rotina somente se as evidências de {rules} mostram que a referência anterior "
                     "ou a configuração já fornecia a função; cite as evidências decisivas.")
    else:
        column = {"pd": "P&D", "rotina": "rotina", "insuficiente": "insuficiente"}.get(contradiction.column or "", "?")
        lines.append(f'O estado escolhido, {contradiction.state}, está na coluna "{column}".')
        lines.append(f"Reavalie escolhendo entre: {choices}.")
        if contradiction.column == "rotina":
            lines.append(f"Mantenha {contradiction.state} somente se citar a evidência de rotina: a referência anterior "
                         "ou uma configuração já fornecia a função, ou o elemento é renomeação de técnica conhecida. "
                         "Falta de um registro não é prova de rotina.")
        else:
            lines.append(f"Mantenha {contradiction.state} somente se citar a evidência decisiva que falta e explicar "
                         "por que as evidências do score não bastam.")
    return "<contradicao>\n" + "\n".join(lines) + "\n</contradicao>"


def forced_state(contradiction: Contradiction, catalog: Catalog) -> str | None:
    """`force` (re-judge only): the column the score points to. SIS and REP are never forced."""
    if contradiction.criterion not in CORE:
        return None
    vocabulary = catalog.criteria[contradiction.criterion].estados
    return vocabulary.positivo[0] if contradiction.strength == "forte_positivo" else vocabulary.negativo
