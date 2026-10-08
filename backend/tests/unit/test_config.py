import pytest

from backend.config import Settings


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_role_falls_back_to_default_model():
    settings = make(ollama_model="base")
    assert settings.model_for("doc") == "base"
    assert settings.model_for("chat") == "base"


def test_role_override_wins():
    settings = make(ollama_model="base", ollama_model_judge="judge-model", ollama_model_report="writer")
    assert settings.model_for("judge") == "judge-model"
    assert settings.model_for("report") == "writer"
    assert settings.model_for("extraction") == "base"


def test_empty_override_counts_as_unset():
    assert make(ollama_model="base", ollama_model_doc="").model_for("doc") == "base"


def test_missing_model_is_a_clear_error():
    with pytest.raises(RuntimeError, match="OLLAMA_MODEL"):
        make(ollama_model="").model_for("default")


def test_models_by_role_lists_every_role():
    roles = make(ollama_model="m").models_by_role()
    assert set(roles) == {"default", "extraction", "doc", "search", "judge", "report", "chat"}


def test_models_by_role_tolerates_missing_model():
    assert make(ollama_model="").models_by_role()["doc"] is None


def test_cors_origins_accepts_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    assert make().cors_origins == ["http://a.test", "http://b.test"]


def test_relative_paths_resolve_from_the_backend_folder():
    from backend.config import BACKEND_ROOT

    settings = make(norms_dir="data/normas", package_dir="../pacote")
    assert settings.norms_dir == BACKEND_ROOT / "data" / "normas"
    assert settings.package_dir == BACKEND_ROOT / "../pacote"
