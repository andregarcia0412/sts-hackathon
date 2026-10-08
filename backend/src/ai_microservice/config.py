"""Env → settings (pydantic-settings). Lê backend/.env (gitignored)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com"
    model_extractor: str = "gemma4:31b"
    model_analyst: str = "gpt-oss:120b"
    analyze_concurrency: int = 5

    # caminhos
    catalog_dir: Path = BACKEND_DIR / "catalog"
    data_dir: Path = BACKEND_DIR / "data"
    graphs_dir: Path = BACKEND_DIR / "data" / "graphs"

    # execução
    llm_max_retries: int = 4
    agent_max_tool_rounds: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()