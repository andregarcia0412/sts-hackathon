from datetime import date

from ai_microservice.modules.novelty.schemas import CampoComOrigem, ProjectProfile, SourceDoc


def make_profile(**overrides) -> ProjectProfile:
    field = CampoComOrigem(texto="isolamento de dependências lentas com circuit breaker", origem="dossie")
    data = dict(
        titulo="Isolamento dinâmico de serviços lentos",
        elemento_novo_declarado=field,
        problema_tecnico=field,
        dominio_setor=field,
        referencia_anterior_declarada=field,
        corte="2025-08-18",
        recorte_semanas=32,
        trecho_data="Recorte de 32 semanas | Corte: 2025-08-18",
        palavras_chave_pt=["isolamento"],
        palavras_chave_en=["bulkhead"],
        termos_sensiveis=["GW-7", "Plataforma de Serviços"],
        data_referencia=date(2025, 1, 6),
        data_inicio_origem="calculada",
    )
    return ProjectProfile(**(data | overrides))


def make_doc(doc_id: str, anterior: bool | None = True, frente: str = "literatura") -> SourceDoc:
    published = {True: date(2020, 1, 1), False: date(2025, 6, 1), None: None}[anterior]
    return SourceDoc(
        id=doc_id,
        frente=frente,
        base="openalex",
        titulo=f"Doc {doc_id}",
        url=f"https://example.org/{doc_id}",
        data_publicacao=published,
        data_verificada=published is not None,
        anterior_a_referencia=anterior,
    )
