from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from ai_microservice.rules import RuleStatus, RuleVerdict

Front = Literal["literatura", "patentes", "mercado"]
FRONTS: tuple[Front, ...] = ("literatura", "patentes", "mercado")

Origem = Literal["dossie", "entrevista", "ambos"]
Tristate = Literal["sim", "nao", "indeterminado"]


# ---- Saídas estruturadas pedidas à LLM ----


class CampoComOrigem(BaseModel):
    texto: str
    origem: Origem


class Divergencia(BaseModel):
    campo: str
    dossie_diz: str
    entrevista_diz: str


class ProfileExtraction(BaseModel):
    titulo: str
    elemento_novo_declarado: CampoComOrigem = Field(
        description="O conhecimento/técnica que a equipe diz ser novo (o 'como'), não o produto"
    )
    problema_tecnico: CampoComOrigem
    dominio_setor: CampoComOrigem = Field(description="Campo tecnológico e setor em que a solução se aplica")
    referencia_anterior_declarada: CampoComOrigem = Field(
        description="Soluções, técnicas ou referências que a equipe diz que já existiam antes do projeto"
    )
    divergencias: list[Divergencia] = Field(
        default_factory=list, description="Pontos em que dossiê e entrevista afirmam coisas diferentes"
    )
    corte: str | None = Field(description="Data de corte do dossiê, AAAA-MM-DD, ou null")
    recorte_semanas: int | None = Field(description="Duração do recorte em semanas, ou null")
    trecho_data: str = Field(description="Trecho literal do dossiê de onde saíram corte e semanas")
    palavras_chave_pt: list[str]
    palavras_chave_en: list[str]
    termos_sensiveis: list[str] = Field(
        description="Nomes de organizações, equipes, pessoas, sistemas, runbooks e códigos internos citados"
    )


class QueryPlan(BaseModel):
    queries: list[str]


class DocComparison(BaseModel):
    cobertura: Literal["total", "parcial", "nenhuma"] = Field(
        description="Quanto o documento já descreve o elemento novo declarado"
    )
    o_que_o_projeto_tem_a_mais: str
    em_uso_no_setor: Tristate = Field(description="O documento mostra a solução já em uso por outros atores do setor?")
    metodo_publico: Tristate = Field(description="O documento descreve publicamente o método (o 'como')?")
    resumo: str = Field(description="Até 2 frases")


class EvidenceCitation(BaseModel):
    fonte_id: str
    justificativa: str = Field(description="Até 2 frases explicando por que esta fonte sustenta o veredito")


class RuleJudgement(BaseModel):
    status: RuleStatus
    resumo: str = Field(description="Até 2 frases")
    evidencias: list[EvidenceCitation]


# ---- Domínio e resposta da API ----


class ProjectProfile(ProfileExtraction):
    data_referencia: date
    data_inicio_origem: Literal["calculada", "informada"]


class SourceDoc(BaseModel):
    id: str
    frente: Front
    base: str
    titulo: str
    url: str
    data_publicacao: date | None
    data_verificada: bool
    # False = publicado depois da data de referência: não é estado da arte, só serve à NOV-W6.
    # None = sem data verificável.
    anterior_a_referencia: bool | None
    tipo_data: str | None = None
    trecho: str = ""
    comparacao: DocComparison | None = None


class Descarte(BaseModel):
    alvo: str
    motivo: str


class SearchLogEntry(BaseModel):
    frente: Front
    base: str
    query: str
    filtros: dict[str, str] = Field(default_factory=dict)
    executado_em: datetime
    n_resultados: int = 0
    selecionados: list[str] = Field(default_factory=list)
    descartados: list[Descarte] = Field(default_factory=list)
    erro: str | None = None


class FrontResult(BaseModel):
    frente: Front
    fontes: list[SourceDoc]
    log: list[SearchLogEntry]


class NoveltyReport(BaseModel):
    criterio: str = "novidade"
    perfil: ProjectProfile
    regras: list[RuleVerdict]
    fontes: list[SourceDoc]
    log_busca: list[SearchLogEntry]
    modelos: dict[str, str]


class JobCreated(BaseModel):
    job_id: str
