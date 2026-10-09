"""Canonical project JSON: the single input of every analysis module (versioned with SCHEMA_VERSION)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr

SCHEMA_VERSION = "1.1"  # 1.1: deterministic mapping of the known files (mapping_source)

FileType = Literal[
    "dossie",
    "registro_tecnico",
    "entrevista",
    "metodo",
    "cronologia",
    "medicoes",
    "resultados",
    "atividades",
    "configuracao",
    "inventario",
    "entradas",
    "observacoes",
    "revisao",
    "checagem",  # deterministic check computed by code (CHK-*), citable like any fragment
    "desconhecido",
]
Nature = Literal["registro_primario", "derivado", "sintese", "depoimento"]
FileStatus = Literal["reconhecido", "pendente_validacao", "nao_extraido"]

# T9 hierarchy of proof: what kind of record each file is.
NATURE_BY_TYPE: dict[str, Nature] = {
    "medicoes": "registro_primario",
    "configuracao": "registro_primario",
    "cronologia": "registro_primario",
    "entradas": "registro_primario",
    "observacoes": "registro_primario",
    "resultados": "derivado",
    "checagem": "derivado",
    "dossie": "sintese",
    "registro_tecnico": "sintese",
    "metodo": "sintese",
    "revisao": "sintese",
    "atividades": "sintese",
    "inventario": "sintese",
    "desconhecido": "sintese",
    "entrevista": "depoimento",
}

DOCUMENT_TYPES = {"dossie", "registro_tecnico", "entrevista", "metodo", "revisao"}
TABLE_TYPES = {"cronologia", "medicoes", "resultados", "atividades", "inventario", "entradas", "observacoes"}

# Fixed section keys per document (Fluxo do Backend §1). `revisao` accepts any snake_case heading key.
SECTION_KEYS: dict[str, list[str]] = {
    "dossie": [
        "contexto",
        "pergunta_registrada",
        "referencia_anterior",
        "trabalho_documentado",
        "limite_da_conclusao",
        "localizacao_da_prova",
    ],
    "registro_tecnico": [
        "mecanismo_e_comparacao",
        "desenho_e_criterios",
        "resultados_recalculaveis",
        "recortes_de_observacao",
        "limite_tecnico",
        "proveniencia",
    ],
    "entrevista": [
        "situacao",
        "ocorrencia",
        "mecanismo",
        "continuidade",
        "verificacao",
        "conclusao",
        "alternativas",
        "condicao_do_registro",
    ],
    "metodo": ["1", "2", "3", "4", "5", "6", "7"],
    "revisao": [
        "material_recebido",
        "verificacao_de_resultados",
        "limites_e_pendencias",
        "proxima_acao",
        "declaracao_da_equipe",
        "unidades_de_comparacao",
    ],
}
REQUIRED_SECTIONS = {"dossie": 6, "registro_tecnico": 6, "entrevista": 7, "metodo": 7}
PREAMBLE_KEY = "cabecalho"


class Fragment(BaseModel):
    """Unit of citation: verbatim text with a stable id."""

    id: str  # PRJ21-EV06#2, PRJ21-S01-M001, PRJ21-CR01
    alias: str  # evidencias/metodo.md#2, evidencias/medicoes.csv#PRJ21-S01-M001
    file: str
    file_type: FileType
    anchor: str
    page: int | None = None
    line: int | None = None
    text: str
    nature: Nature
    data: dict[str, str | None] | None = None  # table rows: column -> raw value (empty cell -> None)


class ExtractedFile(BaseModel):
    path: str
    sha256: str
    file_type: FileType
    evidence_id: str | None = None
    status: FileStatus
    missing_sections: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    fragment_count: int = 0
    mapping_source: Literal["deterministico", "agente"] = "agente"


class ContextField(BaseModel):
    text: str | None = None  # copied from the fragments, never written by the LLM
    fragment_ids: list[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    title: str | None = None
    team: str | None = None
    elemento_novo: ContextField = Field(default_factory=ContextField)
    referencia_anterior: ContextField = Field(default_factory=ContextField)
    barreira: ContextField = Field(default_factory=ContextField)
    pergunta: ContextField = Field(default_factory=ContextField)
    produtos_citados: list[str] = Field(default_factory=list)
    termos_sensiveis: list[str] = Field(default_factory=list)
    palavras_chave_pt: list[str] = Field(default_factory=list)
    palavras_chave_en: list[str] = Field(default_factory=list)
    data_referencia: date | None = None
    data_referencia_origem: Literal["cabecalho", "llm", "informada"] | None = None
    data_referencia_fragmento: str | None = None
    corte: date | None = None
    recorte_semanas: int | None = None


class CanonicalProject(BaseModel):
    schema_version: str = SCHEMA_VERSION
    project_code: str
    files: list[ExtractedFile]
    fragments: list[Fragment]
    context: ProjectContext
    _fragment_index: dict[str, Fragment] | None = PrivateAttr(default=None)

    def fragment(self, fragment_id: str) -> Fragment | None:
        return self._index().get(fragment_id)

    def _index(self) -> dict[str, Fragment]:
        if self._fragment_index is None or len(self._fragment_index) != len(self.fragments):
            self._fragment_index = {f.id: f for f in self.fragments}
        return self._fragment_index

    def fragments_of(self, file_type: str, anchor: str | None = None) -> list[Fragment]:
        return [
            f for f in self.fragments if f.file_type == file_type and (anchor is None or f.anchor == anchor)
        ]
