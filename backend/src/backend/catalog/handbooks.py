"""Per-criterion handbooks (catalog/handbooks/*.md): pitfalls, when to use each state, signals that do not count.

Versioned with the catalog and registered as prompts, so every analysis records the hash of each one."""

import re
from functools import cache
from pathlib import Path

from backend.catalog.models import CRITERIA_ORDER
from backend.llm.prompts import register_prompt

HANDBOOKS_DIR = Path(__file__).with_name("handbooks")
SECTIONS = ("Armadilhas", "Quando usar cada estado", "Sinais que não contam")


@cache
def _texts() -> dict[str, str]:
    return {c: register_prompt(f"graph.state.{c}", (HANDBOOKS_DIR / f"{c}.md").read_text(encoding="utf-8").strip())
            for c in CRITERIA_ORDER}


def handbook(criterion: str) -> str:
    return _texts()[criterion]


def section(criterion: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", handbook(criterion), flags=re.M | re.S)
    return match.group(1).strip() if match else ""


def pitfalls(criterion: str) -> str:
    return section(criterion, "Armadilhas")


_texts()  # register on import, like every other prompt
