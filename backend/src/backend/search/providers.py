import httpx

from backend.config import Settings
from backend.llm import LLM
from backend.search.base import SearchProvider
from backend.search.cache import CachedProvider
from backend.search.ollama_web import OllamaWebProvider
from backend.search.openalex import OpenAlexProvider


def build_providers(llm: LLM, http: httpx.AsyncClient, settings: Settings) -> dict[str, SearchProvider]:
    """The four search fronts, every one behind the shared Mongo cache."""
    return {
        "literatura": CachedProvider(OpenAlexProvider(http, settings.openalex_api_key, settings.openalex_mailto)),
        "patentes": CachedProvider(OllamaWebProvider(llm, name="google_patents", site="patents.google.com")),
        "mercado": CachedProvider(OllamaWebProvider(llm, name="ollama_web")),
        "documentacao": CachedProvider(OllamaWebProvider(llm, name="ollama_web_docs")),
    }
