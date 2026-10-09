import logging

import httpx

from backend.config import settings

logger = logging.getLogger("backend")


def safe_error_message(error: BaseException) -> str:
    """Error message safe to store or return: no URLs (they may carry `api_key=`) and no configured secrets.

    The full error only goes to the server log.
    """
    logger.warning("handled error", exc_info=error)
    name = type(error).__name__
    if isinstance(error, httpx.HTTPStatusError):
        return f"{name}: HTTP {error.response.status_code}"
    if isinstance(error, httpx.RequestError):
        return name
    message = str(error)
    for secret in (settings.ollama_api_key, settings.openalex_api_key):
        if secret:
            message = message.replace(secret, "***")
    return f"{name}: {message}" if message else name
