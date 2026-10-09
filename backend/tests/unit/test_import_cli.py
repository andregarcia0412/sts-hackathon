import pytest

from backend.analyses.jobs import InlineRunner
from backend.analyses.orchestrator import AnalysisService
from backend.catalog.loader import get_catalog
from backend.config import Settings
from backend.projects.cli import run_import
from backend.users.service import create_user
from tests.factories import fake_providers, full_handlers, synthetic_package
from tests.fakes import FakeLLM


@pytest.fixture
def package(tmp_path):
    for f in synthetic_package():
        target = tmp_path / "PRJ90" / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.data)
    return tmp_path


async def test_run_import_analyses_every_project_folder(db, package):
    await create_user("ana@sts.com", "password1", "Ana")
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    panel = await run_import(package, "ana@sts.com", service, InlineRunner(), poll_s=0)
    assert panel.total == 1
    assert panel.counts["concluida"] == 1
    assert panel.items[0].suggested_class == "eligible"


async def test_unknown_owner_is_an_error(db, package):
    service = AnalysisService(FakeLLM(full_handlers()), fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    with pytest.raises(SystemExit, match="ninguem@sts.com"):
        await run_import(package, "ninguem@sts.com", service, InlineRunner(), poll_s=0)
