"""Calibration against the answer key (PRJ01–20): `uv run backend-calibrate gabarito.csv nosso.csv`."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

STATE_COLUMNS = [f"estado_{n}" for n in range(1, 6)]


class CalibrationReport(BaseModel):
    total: int
    class_hits: int
    state_hits: dict[str, int]
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)


def compare(key_rows: list[dict[str, str]], our_rows: list[dict[str, str]]) -> CalibrationReport:
    ours = {row["projeto_id"]: row for row in our_rows}
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    state_hits = dict.fromkeys(STATE_COLUMNS, 0)
    class_hits, missing, total = 0, [], 0
    for key in key_rows:
        row = ours.get(key["projeto_id"])
        if row is None:
            missing.append(key["projeto_id"])
            continue
        total += 1
        confusion[key["classificacao"]][row.get("classificacao") or "(sem classe)"] += 1
        class_hits += key["classificacao"] == row.get("classificacao")
        for column in STATE_COLUMNS:
            state_hits[column] += key.get(column) == row.get(column)
    return CalibrationReport(total=total, class_hits=class_hits, state_hits=state_hits,
                             confusion={k: dict(v) for k, v in confusion.items()}, missing=missing)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as file:
        return list(csv.DictReader(file, delimiter=";"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare our CSV (27 columns) with the answer key")
    parser.add_argument("answer_key", type=Path)
    parser.add_argument("ours", type=Path)
    args = parser.parse_args()
    report = compare(_read(args.answer_key), _read(args.ours))
    print(f"Classe: {report.class_hits}/{report.total}")
    for column, hits in report.state_hits.items():
        print(f"{column}: {hits}/{report.total}")
    print("Matriz de confusão (gabarito → nosso):")
    for expected, row in report.confusion.items():
        print(f"  {expected}: {row}")
    if report.missing:
        print("Sem saída nossa:", ", ".join(report.missing))
