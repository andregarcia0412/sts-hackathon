from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LLMRole = Literal["default", "extraction", "search", "judge"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_host: str = "https://ollama.com"
    ollama_api_key: str | None = None
    ollama_model: str = ""
    ollama_model_extraction: str | None = None
    ollama_model_search: str | None = None
    ollama_model_judge: str | None = None
    ollama_max_concurrency: int = 4
    ollama_timeout_s: float = 180

    openalex_api_key: str | None = None
    openalex_mailto: str | None = None

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    novelty_queries_per_front: int = 3
    novelty_results_per_query: int = 5
    novelty_fetch_per_front: int = 6

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def model_for(self, role: LLMRole) -> str:
        override = {
            "extraction": self.ollama_model_extraction,
            "search": self.ollama_model_search,
            "judge": self.ollama_model_judge,
        }.get(role)
        model = override or self.ollama_model
        if not model:
            raise RuntimeError("OLLAMA_MODEL não configurado no .env")
        return model


@lru_cache
def get_settings() -> Settings:
    return Settings()
