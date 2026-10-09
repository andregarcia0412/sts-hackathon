from backend.analyses.jobs import InlineRunner
from backend.analyses.orchestrator import AnalysisService
from backend.benchmark.cli import parser, print_summary, run
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.users.service import create_user
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM


async def test_cli_runs_a_folder_and_prints_the_summary(db, tmp_path, capsys):
    for f in synthetic_package():
        target = tmp_path / "PRJ90" / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.data)
    (tmp_path / "pre.csv").write_text("projeto_id;classificacao\nPRJ90;Elegível\n", encoding="utf-8")
    await create_user("ana@sts.com", "password1", "Ana")
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    args = parser().parse_args(["--sets", "analise", "--analise", str(tmp_path), "--preliminary", str(tmp_path / "pre.csv"),
                                "--owner", "ana@sts.com", "--poll", "0", "--projects", "PRJ90"])
    benchmark = await run(args, service, InlineRunner())
    assert benchmark.status == "concluido"
    assert benchmark.metrics.accuracy["preliminar"].class_accuracy == 1.0
    print_summary(benchmark.metrics)
    out = capsys.readouterr().out
    assert "leitura preliminar (NÃO oficial): 1/1" in out and "== Tempo" in out
