"""Expected answers: the official answer key (PRJ01–20) and the team's preliminary reading (PRJ21–40, NOT official)."""

from pathlib import Path
from typing import Literal

from pydantic import Field

from backend.api_schema import CamelModel
from backend.catalog.models import Catalog
from backend.graph.classify import CLASS_LABELS
from backend.report.calibration import read_csv

ReferenceSource = Literal["oficial", "preliminar"]
LABEL_TO_CLASS = {label: cls for cls, label in CLASS_LABELS.items()}


class PlantedDivergence(CamelModel):
    """A planted interview error: what the testimony says × what the record shows (tokens to look for)."""

    testimony: str
    record: str
    prevailing_source: str = ""


class ExpectedCase(CamelModel):
    code: str
    source: ReferenceSource
    expected_class: str | None  # eligible | eligible_with_caveats | not_eligible | insufficient_evidence
    states: dict[str, str | None] = Field(default_factory=dict)  # criterion → exact vocabulary (official only)
    planted_divergences: list[PlantedDivergence] = Field(default_factory=list)


def _class_of(label: str | None) -> str | None:
    return LABEL_TO_CLASS.get((label or "").strip())


def load_answer_key(path: Path, catalog: Catalog) -> dict[str, ExpectedCase]:
    """historicos_classificados.csv (27 columns): class + the five criterion states, matched by criterion name."""
    by_name = {info.nome.casefold(): cid for cid, info in catalog.criteria.items()}
    cases: dict[str, ExpectedCase] = {}
    for row in read_csv(path):
        states: dict[str, str | None] = {}
        for n in range(1, 6):
            criterion = by_name.get((row.get(f"criterio_{n}") or "").strip().casefold())
            if criterion:
                states[criterion] = (row.get(f"estado_{n}") or "").strip() or None
        code = row["projeto_id"].strip()
        cases[code] = ExpectedCase(code=code, source="oficial", expected_class=_class_of(row.get("classificacao")),
                                   states=states)
    return cases


def load_preliminary(path: Path) -> dict[str, ExpectedCase]:
    """leitura_preliminar.csv: the team's reading of the cases without answer key. Never reported as accuracy."""
    cases: dict[str, ExpectedCase] = {}
    for row in read_csv(path):
        code = row["projeto_id"].strip()
        testimony, record = (row.get("divergencia_entrevista") or "").strip(), (row.get("divergencia_registro") or "").strip()
        planted = [PlantedDivergence(testimony=testimony, record=record,
                                     prevailing_source=(row.get("fonte_que_prevalece") or "").strip())] \
            if testimony or record else []
        cases[code] = ExpectedCase(code=code, source="preliminar", expected_class=_class_of(row.get("classificacao")),
                                   planted_divergences=planted)
    return cases
