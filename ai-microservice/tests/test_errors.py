import httpx

from ai_microservice.config import get_settings
from ai_microservice.errors import safe_error_message


def test_http_status_error_hides_url_with_api_key():
    request = httpx.Request("GET", "https://api.openalex.org/works?api_key=SECRET123")
    error = httpx.HTTPStatusError("boom", request=request, response=httpx.Response(429, request=request))
    message = safe_error_message(error)
    assert message == "HTTPStatusError: HTTP 429"
    assert "SECRET123" not in message


def test_request_error_keeps_only_the_type():
    request = httpx.Request("GET", "https://api.openalex.org/works?api_key=SECRET123")
    assert safe_error_message(httpx.ConnectTimeout("timeout url=...SECRET123", request=request)) == "ConnectTimeout"


def test_configured_keys_are_redacted(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-secret")
    get_settings.cache_clear()
    try:
        assert safe_error_message(RuntimeError("bad token ollama-secret")) == "RuntimeError: bad token ***"
    finally:
        get_settings.cache_clear()
