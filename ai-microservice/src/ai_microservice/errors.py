import logging

import httpx

from ai_microservice.config import get_settings

logger = logging.getLogger("ai_microservice")


def safe_error_message(error: BaseException) -> str:
    """Mensagem de erro segura para devolver na API: sem URL (pode ter `api_key=`) e sem chaves configuradas.

    O erro completo vai só para o log do servidor.
    """
    logger.warning("erro tratado", exc_info=error)
    name = type(error).__name__
    if isinstance(error, httpx.HTTPStatusError):
        return f"{name}: HTTP {error.response.status_code}"
    if isinstance(error, httpx.RequestError):
        return name
    message = str(error)
    settings = get_settings()
    for secret in (settings.ollama_api_key, settings.openalex_api_key):
        if secret:
            message = message.replace(secret, "***")
    return f"{name}: {message}" if message else name
