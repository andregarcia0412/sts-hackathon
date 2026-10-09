from backend.search.sanitize import find_sensitive_term, sanitize_query


def test_sensitive_term_matching_ignores_case_and_accents():
    assert find_sensitive_term("Gateway da Plataforma de Servicos", ["Plataforma de Serviços"]) == "Plataforma de Serviços"
    assert find_sensitive_term("circuit breaker gateway", ["GW-7"]) is None


def test_short_terms_are_ignored():
    assert find_sensitive_term("a b", ["a"]) is None


def test_sanitize_removes_project_codes_internal_codes_numbers_and_terms():
    result = sanitize_query("PRJ21 runbook GW-7 circuit breaker 88,9% Plataforma de Serviços", ["Plataforma de Serviços"])
    assert result.sanitized == "runbook circuit breaker"
    assert result.original.startswith("PRJ21")
    assert set(result.removed) == {"PRJ21", "GW-7", "88,9%", "Plataforma de Serviços"}
    assert result.changed


def test_clean_query_is_unchanged():
    result = sanitize_query("bulkhead pattern microservices", [])
    assert result.sanitized == "bulkhead pattern microservices"
    assert not result.changed
    assert result.removed == []


def test_single_digits_survive():
    assert sanitize_query("HTTP 2 multiplexing", []).sanitized == "HTTP 2 multiplexing"
