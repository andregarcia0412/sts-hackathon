import csv
import hashlib
import io
import json

import pytest

from backend.analyses.jobs import InlineRunner
from backend.analyses.models import Analysis
from backend.analyses.orchestrator import AnalysisService
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.delivery.export import ANSWER_KEY_COLUMNS, PENDING, DeliveryError, export_delivery
from backend.delivery.run import pending_codes, run_delivery
from backend.review.models import Decision
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM

SETTINGS = Settings(_env_file=None, ollama_model="m")


def write_cases(root, codes=("PRJ91", "PRJ92")):
    for code in codes:
        for f in synthetic_package():
            target = root / code / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f.data.replace(b"PRJ90", code.encode()))
    return root


@pytest.fixture
async def delivered(db, tmp_path):
    folder = write_cases(tmp_path / "casos")
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, SETTINGS, get_catalog())
    benchmark = await run_delivery("owner-1", "entrega", folder, service, InlineRunner(), None)
    return benchmark, service, folder, tmp_path


async def test_export_writes_every_item_of_the_expected_delivery(delivered):
    benchmark, _, _, tmp_path = delivered
    out = tmp_path / "entrega"
    result = await export_delivery(benchmark, get_catalog(), out, expected=2)
    assert result.ok
    for name in ("parecer.pdf", "parecer.json", "criterios.csv", "evidencias.csv", "contrarias_e_divergencias.csv",
                 "lacunas.csv", "rastreabilidade.json", "grafo.json", "api.json"):
        assert (out / "PRJ91" / name).is_file(), name
    answers = (out / "respostas_PRJ91-PRJ92.csv").read_text(encoding="utf-8")
    header = next(csv.reader(io.StringIO(answers.lstrip("﻿")), delimiter=";"))
    assert header == ANSWER_KEY_COLUMNS and len(header) == 27 and answers.startswith("﻿")
    assert PENDING in answers  # no analyst decided yet: never a decision on anyone's behalf
    manifest = json.loads((out / "manifest.json").read_text())
    for path, digest in manifest["arquivos"].items():
        assert hashlib.sha256((out / path).read_bytes()).hexdigest() == digest
    assert "Entrega esperada" in (out / "LEIA-ME.md").read_text() and (out / "resumo.html").is_file()
    api = json.loads((out / "frontend" / "api_mock.json").read_text())
    assert "GET /projects" in api and any(k.endswith("/graph") for k in api)
    assert any(k.endswith("/analyses") and v[0]["criteria"] for k, v in api.items() if isinstance(v, list) and v)


async def test_decisions_and_require_decisions(delivered):
    benchmark, _, _, tmp_path = delivered
    first = await Analysis.get(benchmark.runs[0].analysis_id)
    await Decision(project_id=first.project_id, analysis_id=str(first.id), outcome="eligible", justification="ok",
                   analyst_name="Ana", analyst_id="u1").insert()
    result = await export_delivery(benchmark, get_catalog(), tmp_path / "e1", require_decisions=True)
    status = {p.code: p.status for p in result.projects}
    assert status == {"PRJ91": "ok", "PRJ92": "falhou"} and not result.ok
    trace = json.loads((tmp_path / "e1" / "PRJ91" / "rastreabilidade.json").read_text())
    assert trace["decisoes"][0]["quem"] == "Ana"


async def test_missing_or_failed_projects_make_the_export_fail(delivered):
    benchmark, _, _, tmp_path = delivered
    second = await Analysis.get(benchmark.runs[1].analysis_id)
    second.status = "falhou"
    await second.save()
    result = await export_delivery(benchmark, get_catalog(), tmp_path / "e2", expected=2)
    assert not result.ok and json.loads((tmp_path / "e2" / "manifest.json").read_text())["ok"] is False


async def test_the_delivery_never_goes_inside_a_git_repository(delivered, tmp_path):
    benchmark, *_ = delivered
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    with pytest.raises(DeliveryError):
        await export_delivery(benchmark, get_catalog(), tmp_path / "repo" / "entrega")


async def test_resume_reuses_unchanged_projects_and_redoes_changed_ones(delivered):
    benchmark, service, folder, _ = delivered
    todo, reused = await pending_codes(folder, benchmark, get_catalog().versao)
    assert todo == [] and reused == ["PRJ91", "PRJ92"]
    (folder / "PRJ92" / "evidencias" / "metodo.md").write_text("mudou", encoding="utf-8")
    todo, reused = await pending_codes(folder, benchmark, get_catalog().versao)
    assert todo == ["PRJ92"] and reused == ["PRJ91"]
    resumed = await run_delivery("owner-1", "entrega", folder, service, InlineRunner(), None, resume=benchmark)
    assert [r.code for r in resumed.runs] == ["PRJ92"] and resumed.config.resumed_from == str(benchmark.id)
