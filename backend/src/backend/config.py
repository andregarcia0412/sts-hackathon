from pathlib import Path
from typing import Annotated, Literal, get_args

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LLMRole = Literal["default", "extraction", "doc", "search", "judge", "report", "chat"]
LLM_ROLES: tuple[LLMRole, ...] = get_args(LLMRole)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://root:root@localhost:27017/?authSource=admin"
    mongodb_db: str = "sts"

    jwt_access_secret: str
    jwt_refresh_secret: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    seed_email_pattern: str
    seed_password: str

    # Ollama: change models here only (.env). Empty role override = OLLAMA_MODEL.
    ollama_host: str = "https://ollama.com"
    ollama_api_key: str | None = None
    ollama_model: str = ""
    ollama_model_extraction: str | None = None
    ollama_model_doc: str | None = None
    ollama_model_search: str | None = None
    ollama_model_judge: str | None = None
    ollama_model_report: str | None = None
    ollama_model_chat: str | None = None
    ollama_max_concurrency: int = 4
    ollama_timeout_s: float = 180
    ollama_retries: int = 2
    ollama_schema_retries: int = 2  # new attempts after an answer that does not match the JSON schema

    openalex_api_key: str | None = None
    openalex_mailto: str | None = None

    web_queries_per_front: int = 3
    web_results_per_query: int = 5
    web_fetch_per_front: int = 6

    analysis_concurrency: int = 2

    judge_mode: Literal["estado", "questionario"] = "estado"
    coherence_mode: Literal["off", "flag", "reask"] = "reask"
    coherence_high: int = 75
    coherence_low: int = 25
    coherence_min_rules: int = 4
    prompt_max_table_rows: int = 300
    package_dir: Path | None = None
    norms_dir: Path = BACKEND_ROOT / "data" / "normas"
    norms_auto_ingest: bool = True

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("seed_email_pattern")
    @classmethod
    def _pattern_has_placeholder(cls, value: str) -> str:
        if "{n}" not in value:
            raise ValueError("SEED_EMAIL_PATTERN must contain '{n}', e.g. user{n}@sts.com")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("package_dir", mode="before")
    @classmethod
    def _empty_path_is_none(cls, value: object) -> object:
        return value or None

    @field_validator("package_dir", "norms_dir")
    @classmethod
    def _relative_to_backend(cls, value: Path | None) -> Path | None:
        return BACKEND_ROOT / value if value is not None and not value.is_absolute() else value

    def model_for(self, role: LLMRole) -> str:
        override = getattr(self, f"ollama_model_{role}", None) if role != "default" else None
        model = override or self.ollama_model
        if not model:
            raise RuntimeError("OLLAMA_MODEL is not set in .env")
        return model

    def models_by_role(self) -> dict[str, str | None]:
        """Model used by each role, recorded in every analysis (None when not configured)."""
        models: dict[str, str | None] = {}
        for role in LLM_ROLES:
            try:
                models[role] = self.model_for(role)
            except RuntimeError:
                models[role] = None
        return models


settings = Settings()
