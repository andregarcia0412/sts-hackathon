"""Gate de citação e sanitização de query (T6/NOV-W8)."""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent


def test_gate_aceita_literal():
    from ai_microservice.gate import quote_in_source

    src = "Configurar deduplicação por (operação, versão). Uma retransmissão mantém a chave."
    assert quote_in_source("Configurar deduplicação por (operação, versão).", src) is True


def test_gate_aceita_com_normalizacao_de_espaco():
    from ai_microservice.gate import quote_in_source

    src = "Configurar  deduplicação\npor (operação, versão)."
    assert quote_in_source("Configurar deduplicação por (operação, versão).", src) is True


def test_gate_rejeita_parafrase():
    from ai_microservice.gate import quote_in_source

    src = "Configurar deduplicação por (operação, versão)."
    assert quote_in_source("Configura a deduplicação usando operação e versão.", src) is False


def test_gate_rejeita_citacao_inventada():
    from ai_microservice.gate import quote_in_source

    src = "O manual BARR-2 fornece chave composta."
    assert quote_in_source("O manual BARR-3 fornece chave composta.", src) is False


def test_gate_vazio_rejeita():
    from ai_microservice.gate import quote_in_source

    assert quote_in_source("", "qualquer texto") is False
    assert quote_in_source("  ", "qualquer texto") is False


class TestSanitizacao:
    def test_remove_id_de_projeto(self):
        from ai_microservice.tools.web import sanitize_query

        q, log = sanitize_query("deduplicação de mensagens PRJ01 barramento")
        assert "PRJ01" not in q
        assert "PRJ" not in q
        assert log["original"] == "deduplicação de mensagens PRJ01 barramento"
        assert log["sanitized"] == q

    def test_remove_nome_de_equipe_do_pacote(self):
        from ai_microservice.tools.web import sanitize_query

        # equipe vem do dossiê (ex.: "Engenharia de Mensageria")
        q, log = sanitize_query(
            "Engenharia de Mensageria deduplicação",
            extra_blocklist=["Engenharia de Mensageria"],
        )
        assert "Engenharia" not in q
        assert "Mensageria" not in q

    def test_remove_codigo_interno(self):
        from ai_microservice.tools.web import sanitize_query

        q, _ = sanitize_query("retenção BARR-2 em barramento de mensagens")
        assert "BARR-2" not in q

    def test_log_original_x_sanitizada(self):
        from ai_microservice.tools.web import sanitize_query

        q, log = sanitize_query("PRJ01 como configurar idempotência")
        assert log["removed"] == ["PRJ01"]
        assert log["sanitized"] == q


class TestFileSearch:
    def test_busca_por_artefato_e_termo(self):
        from ai_microservice.extraction.parsers import parse_project
        from ai_microservice.tools.file_search import search_fragments

        parsed = parse_project(BACKEND / "data" / "casos_test" / "PRJ01")
        frags = search_fragments(parsed["fragments"], termo="Nenhum algoritmo do barramento")
        assert len(frags) >= 2  # metodo.md#2 e registro_tecnico + transcrição + atividades
        anchors = {f.anchor for f in frags}
        assert "evidencias/metodo.md#2" in anchors

    def test_busca_por_artefato(self):
        from ai_microservice.extraction.parsers import parse_project
        from ai_microservice.tools.file_search import search_fragments

        parsed = parse_project(BACKEND / "data" / "casos_test" / "PRJ01")
        frags = search_fragments(parsed["fragments"], artefato="evidencias/metodo.md")
        assert len(frags) == 7
        frags2 = search_fragments(parsed["fragments"], artefato="evidencias/metodo.md", secao="2")
        assert len(frags2) == 1 and frags2[0].anchor == "evidencias/metodo.md#2"