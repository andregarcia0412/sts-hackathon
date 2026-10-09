"""Synthetic project package (fictitious PRJ90, written here) and a deterministic stand-in for the
extraction agent. The real hackathon package never enters the repository."""

import json
import re
import unicodedata

from fpdf import FPDF

from backend.extraction.agent import ContextOut, FileMapping, SectionMark
from backend.projects.importer import IncomingFile

FOOTER = "Massa inteiramente ficticia | V9 | Registros sinteticos"

DOSSIE_LINES = [
    "PRJ90 | Fila adaptativa de conciliacao",
    "Equipe: Time Conciliacao | Recorte de 10 semanas | Corte: 2025-03-17",
    "Contexto",
    "Lotes atrasados travavam a conciliacao noturna.",
    "Pergunta registrada",
    "Como ordenar lotes sem violar a precedencia contabil?",
    "Referencia anterior",
    "Fila FIFO e prioridade fixa falham quando dois lotes dependem do mesmo saldo.",
    "Trabalho documentado",
    "Fila por dependencia testada contra FIFO e prioridade fixa nas mesmas 200 entradas.",
    "Limite da conclusao",
    "Somente lotes de ate 500 itens. Lotes maiores excluidos desde o inicio.",
    "Localizacao da prova",
    "Metodo em evidencias/metodo.md. Registros em medicoes.csv.",
]

ENTREVISTA_LINES = [
    "PRJ90 | Entrevista tecnica",
    "Equipe ficticia: Time Conciliacao | Data: 2025-03-17",
    "1. Como ficou a conclusao da rodada?",
    "A fila por dependencia acertou todos os 200 lotes.",
    "2. Qual situacao motivou o trabalho?",
    "Lotes atrasados travavam a conciliacao noturna.",
    "3. O que a equipe fez no mecanismo?",
    "Criamos uma fila por dependencia de saldo.",
    "4. Que ponto ficou para continuidade?",
    "Lotes maiores.",
    "5. Como foi organizada a verificacao?",
    "Mesmas entradas para as tres filas.",
    "6. Qual ocorrencia voce recorda?",
    "Um lote circular.",
    "7. Que alternativas ou recursos ja existiam?",
    "FIFO e prioridade fixa.",
    "Condicao do registro",
    "Depoimento de memoria. Confrontar com versoes, criterios, resultados e fontes entregues.",
]

METODO = """# PRJ90 — Método e referência

Documento sintético. Data de corte: 2025-03-17.

## 1. Referência anterior

FIFO e prioridade fixa são comparadores conhecidos. Ambos falham quando dois lotes dependem do mesmo saldo.

## 2. Mecanismo e hipótese

Ordenar lotes por grafo de dependência de saldo, com desempate pelo menor atraso e janela de 15 minutos.

## 3. Protocolo e critérios

Três filas nas mesmas 200 entradas. Critério prévio: pelo menos 95% de lotes na ordem correta.

## 4. Parâmetros, versões e execução registrada

- janela_min: 15

Versões localizadas: fifo-v1, prioridade-v1, dependencia-v2.

## 5. Leitura e reconstrução dos resultados

`medicoes.csv` é a fonte primária.

## 6. Limite da conclusão

Somente lotes de até 500 itens.

## 7. Continuidade e detalhamento técnico

Testar lotes maiores.
"""

REVISAO = """# PRJ90 — Registro de revisão técnica

## Limites e pendências técnicas

Lotes acima de 500 itens não foram ensaiados.

## Declaração da equipe

MEMO-90 cita 100% sem identificar a versão.
"""

INVENTARIO = (
    "﻿id_evidencia;projeto_id;tipo;arquivo;conteudo_esperado;status;observacao\n"
    "PRJ90-EV01;PRJ90;Dossiê;dossie_projeto.pdf;contexto;Localizada;síntese\n"
    "PRJ90-EV04;PRJ90;Inventário;inventario_evidencias.csv;arquivos;Localizada;índice\n"
    "PRJ90-EV05;PRJ90;Configuração;evidencias/configuracao.json;parâmetros;Localizada;especificação\n"
    "PRJ90-EV06;PRJ90;Método;evidencias/metodo.md;método;Localizada;especificação\n"
    "PRJ90-EV07;PRJ90;Cronologia;evidencias/cronologia.csv;datas;Localizada;registro de versões\n"
    "PRJ90-EV08;PRJ90;Medições;evidencias/medicoes.csv;contadores;Localizada;registro primário\n"
    "PRJ90-EV09;PRJ90;Resultados;evidencias/resultados.csv;consolidação;Localizada;calculado\n"
    "PRJ90-EV10;PRJ90;Entrevista;transcricao_entrevista_tecnica.pdf;depoimento;Localizada;depoimento\n"
    "PRJ90-EV13;PRJ90;Revisão técnica;evidencias/revisao_tecnica.md;alcance;Localizada;revisão\n"
)

CRONOLOGIA = (
    "﻿evento_id;data;versao;evento;estado;fonte\n"
    "PRJ90-CR01;2025-01-06;documento-inicial;Registro do problema;registrado;evidencias/metodo.md#1\n"
    "PRJ90-CR02;2025-01-20;protocolo-r1;Critérios descritos no método;registrado;evidencias/metodo.md#3\n"
    "PRJ90-CR03;2025-02-10;dependencia-v2;Arquivamento dos registros;registrado;evidencias/medicoes.csv\n"
)

MEDICOES = (
    "﻿registro_id;ensaio_id;versao;cenario;tipo;metrica;valor;numerador;denominador;peso;unidade\n"
    "PRJ90-S01-M001;PRJ90-S01;fifo-v1;C001;contador;lotes na ordem;;150;200;;casos\n"
    "PRJ90-S02-M001;PRJ90-S02;dependencia-v2;C001;contador;lotes na ordem;;196;200;;casos\n"
)

RESULTADOS = (
    "﻿ensaio_id;versao;metrica;operacao;valor;base_de_calculo;descricao_base;taxa_percentual;unidade;fonte;natureza\n"
    "PRJ90-S01;fifo-v1;lotes na ordem;contagem;150;200;Lotes;75.0;casos;evidencias/medicoes.csv#PRJ90-S01;desempenho\n"
    "PRJ90-S02;dependencia-v2;lotes na ordem;contagem;196;200;Lotes;98.0;casos;evidencias/medicoes.csv#PRJ90-S02;desempenho\n"
)

CONFIGURACAO = {
    "projeto_id": "PRJ90",
    "parametros": {"janela_min": 15, "limiar_desempate": None},
    "versoes_registradas": ["fifo-v1", "prioridade-v1", "dependencia-v2"],
}


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")


def make_pdf(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, FOOTER, new_x="LMARGIN", new_y="NEXT")
    for line in lines:
        pdf.cell(0, 6, _ascii(line), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def synthetic_package() -> list[IncomingFile]:
    files = {
        "dossie_projeto.pdf": make_pdf(DOSSIE_LINES),
        "transcricao_entrevista_tecnica.pdf": make_pdf(ENTREVISTA_LINES),
        "inventario_evidencias.csv": INVENTARIO.encode(),
        "evidencias/metodo.md": METODO.encode(),
        "evidencias/revisao_tecnica.md": REVISAO.encode(),
        "evidencias/cronologia.csv": CRONOLOGIA.encode(),
        "evidencias/medicoes.csv": MEDICOES.encode(),
        "evidencias/resultados.csv": RESULTADOS.encode(),
        "evidencias/configuracao.json": json.dumps(CONFIGURACAO, ensure_ascii=False, indent=2).encode(),
        "notas_soltas.txt": b"Anotacao solta sem estrutura.",
    }
    return [IncomingFile(path=path, data=data, top_folder="PRJ90") for path, data in files.items()]


# ----------------------------------------------------------------------------- fake extraction agent

NUMBERED_RE = re.compile(r"^L(\d+): ?(.*)$", re.MULTILINE)
DOSSIE_HEADINGS = {
    "Contexto": "contexto",
    "Pergunta registrada": "pergunta_registrada",
    "Referencia anterior": "referencia_anterior",
    "Trabalho documentado": "trabalho_documentado",
    "Limite da conclusao": "limite_da_conclusao",
    "Localizacao da prova": "localizacao_da_prova",
}
INTERVIEW_PREFIXES = {
    "Como ficou a conclusao": "conclusao",
    "Qual situacao": "situacao",
    "O que a equipe fez": "mecanismo",
    "Que ponto ficou": "continuidade",
    "Como foi organizada": "verificacao",
    "Qual ocorrencia": "ocorrencia",
    "Que alternativas": "alternativas",
    "Condicao do registro": "condicao_do_registro",
}
TABLE_BY_FIRST_COLUMN = {
    "id_evidencia": "inventario",
    "registro_id": "medicoes",
    "ensaio_id": "resultados",
    "evento_id": "cronologia",
    "id_atividade": "atividades",
}


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")


def fake_file_mapping(messages) -> FileMapping:
    """Maps a file the way the extraction agent is asked to, reading the numbered lines of the prompt."""
    user = messages[-1]["content"]
    lines = {int(n): text for n, text in NUMBERED_RE.findall(user)}
    ignore = [n for n, text in lines.items() if text.startswith("Massa inteiramente")]
    first = next(iter(lines.values()), "").lstrip("﻿")
    first_column = first.split(";", 1)[0]
    if first_column in TABLE_BY_FIRST_COLUMN:
        kind = TABLE_BY_FIRST_COLUMN[first_column]
        return FileMapping(
            tipo=kind,
            justificativa="cabeçalho",
            linha_cabecalho=1,
            coluna_id=first_column,
            coluna_arquivo="arquivo" if kind == "inventario" else None,
        )
    if '"parametros"' in user:
        return FileMapping(tipo="configuracao", justificativa="chaves")
    marks: list[SectionMark] = []
    if any("Recorte de" in text for text in lines.values()):
        for n, text in lines.items():
            if text in DOSSIE_HEADINGS:
                marks.append(SectionMark(chave=DOSSIE_HEADINGS[text], linha=n, titulo=text))
        return FileMapping(tipo="dossie", justificativa="seções", secoes=marks, linhas_ignorar=ignore)
    if any("Entrevista tecnica" in text for text in lines.values()):
        for n, text in lines.items():
            for prefix, key in INTERVIEW_PREFIXES.items():
                if prefix in text:
                    marks.append(SectionMark(chave=key, linha=n, titulo=text))
        return FileMapping(tipo="entrevista", justificativa="perguntas", secoes=marks, linhas_ignorar=ignore)
    if any("Método e referência" in text for text in lines.values()):
        for n, text in lines.items():
            if match := re.match(r"## (\d)\.", text):
                marks.append(SectionMark(chave=match.group(1), linha=n, titulo=text))
        return FileMapping(tipo="metodo", justificativa="seções", secoes=marks)
    if any("revisão técnica" in text for text in lines.values()):
        for n, text in lines.items():
            if text.startswith("## "):
                marks.append(SectionMark(chave=_slug(text[3:]), linha=n, titulo=text))
        return FileMapping(tipo="revisao", justificativa="seções", secoes=marks)
    return FileMapping(tipo="desconhecido", justificativa="sem padrão")


def fake_context(messages) -> ContextOut:
    return ContextOut(
        titulo="Fila adaptativa de conciliacao",
        equipe="Time Conciliacao",
        elemento_novo=["PRJ90-EV06#2"],
        referencia_anterior=["PRJ90-EV06#1", "PRJ90-EV01#referencia_anterior"],
        barreira=["PRJ90-EV01#contexto", "PRJ90-INEXISTENTE#x"],
        pergunta=["PRJ90-EV01#pergunta_registrada"],
        produtos_citados=["FIFO"],
        termos_sensiveis=["Time Conciliacao"],
        palavras_chave_pt=["fila por dependência"],
        palavras_chave_en=["dependency-aware batch scheduling"],
        corte=None,
        recorte_semanas=None,
    )


def extraction_handlers() -> dict:
    return {FileMapping: fake_file_mapping, ContextOut: fake_context}


async def synthetic_canonical():
    from backend.extraction.pipeline import extract_project
    from tests.fakes import FakeLLM

    return await extract_project(FakeLLM(extraction_handlers()), synthetic_package(), code_hint="PRJ90")


def evidence(rule_id, polarity="positiva", source="PRJ90-EV06#2", nature="sintese", criterion=None, quote="q", origin="doc"):
    from backend.criteria.schemas import EvidenceItem, evidence_id

    return EvidenceItem(
        id=evidence_id(rule_id, source, quote + polarity),
        rule_id=rule_id,
        criterion=criterion or rule_id.split("-")[0],
        origin=origin,
        source_id=source,
        source_alias=f"alias/{source}",
        quote=quote,
        polarity=polarity,
        explanation="porque",
        query="o que verificar",
        nature=nature,
    )


def run(rule_id, *evidences, status=None, reason=None):
    from backend.criteria.schemas import RuleRun

    return RuleRun(
        rule_id=rule_id,
        criterion=rule_id.split("-")[0],
        status=status or ("executada" if evidences else "sem_evidencia"),
        reason=reason,
        evidences=list(evidences),
    )


# ----------------------------------------------------------------------------- full fake pipeline

NUMERIC_RULE = {"NOV": "NOV-D6", "CRI": "CRI-D10", "INC": "INC-D12", "SIS": "SIS-D12", "REP": "REP-D9"}
CRITERION_BY_NAME = {"Novidade": "NOV", "Criatividade técnica": "CRI", "Incerteza tecnológica": "INC",
                     "Sistematicidade": "SIS", "Transferência/reprodução": "REP"}
ELIGIBLE_STATES = {"NOV": "DEMONSTRADA NO RECORTE", "CRI": "DEMONSTRADA NO RECORTE", "INC": "INVESTIGADA",
                   "SIS": "DOCUMENTADA", "REP": "DOCUMENTADA NO ESCOPO"}


def _criterion_in(messages) -> str:
    text = messages[-1]["content"]
    match = re.search(r"Critério: ([^—\n]+)", text)
    return CRITERION_BY_NAME[match.group(1).strip()]


def fake_doc_sub(messages):
    from backend.criteria.doc_sub import DocSubOut

    criterion = _criterion_in(messages)
    out = {
        "evidencias": [{"regra_id": NUMERIC_RULE[criterion], "fragmento_id": "PRJ90-S02", "quote": "196;200",
                        "polaridade": "positiva", "justificativa": "Mecanismo supera o comparador nas mesmas entradas."}],
        "regras_sem_evidencia": [],
        "divergencias": [],
        "elos_ausentes": [],
    }
    if criterion == "NOV":
        out["evidencias"].append({"regra_id": "NOV-D2", "fragmento_id": "PRJ90-EV06#1",
                                  "quote": "Ambos falham quando dois lotes dependem do mesmo saldo.",
                                  "polaridade": "positiva", "justificativa": "Modo de falha das alternativas."})
        out["divergencias"].append({"depoimento_fragmento_id": "PRJ90-EV10#conclusao",
                                    "depoimento_quote": "acertou todos os 200 lotes", "registro_fragmento_id": "PRJ90-S02",
                                    "registro_quote": "196;200", "afirmacao": "200", "registro_mostra": "196"})
    return DocSubOut.model_validate(out)


def fake_query_plan(messages):
    from backend.criteria.web_sub import QueryPlanOut

    return QueryPlanOut(queries=[{"frente": "literatura", "query": "dependency aware batch scheduling", "regras": []}])


def fake_web_judge(messages):
    from backend.criteria.web_sub import WebJudgeOut

    return WebJudgeOut(
        evidencias=[{"regra_id": "NOV-W3", "fonte_id": "src-paper", "quote": "priority queues for batches",
                     "polaridade": "positiva", "justificativa": "Não descreve dependência de saldo."}],
        documento_mais_proximo={"fonte_id": "src-paper", "cobertura": "parcial", "o_que_o_projeto_tem_a_mais": "dependência de saldo"},
    )


def fake_state(states: dict[str, str] | None = None):
    states = states or ELIGIBLE_STATES

    def handler(messages):
        from backend.graph.states import StateJudgeOut

        criterion = _criterion_in(messages)
        evidence_ids = re.findall(r"\[(ev-[0-9a-f]+)\]", messages[-1]["content"])
        return StateJudgeOut(estado=states[criterion], justificativa=f"Sustentado por [{evidence_ids[0]}]." if evidence_ids else "x",
                             evidencias_decisivas=evidence_ids[:1])

    return handler


ELIGIBLE_ANSWERS = {"N1": "nao", "N2": "sim", "N3": "sim", "C1": "nao", "C2": "sim", "C3": "sim",
                    "I1": "nao", "I2": "experimental", "I3": "sim", "S1": "sim", "S2": "experimento",
                    "R1": "sim", "R2": "conhecimento", "R3": "nao"}


def fake_answers(answers: dict[str, str] | None = None):
    """Questionnaire judge: answers every asked question (from the <perguntas> block) citing the first evidence."""
    answers = ELIGIBLE_ANSWERS | (answers or {})

    def handler(messages):
        from backend.graph.questionnaire import QuestionnaireOut

        text = messages[1]["content"]
        block = text.split("<perguntas>")[1].split("</perguntas>")[0]
        asked = re.findall(r"^([A-Z]\d) \[", block, flags=re.M)
        evidence_ids = re.findall(r"\[(ev-[0-9a-f]+)\]", text)
        out = []
        for question in asked:
            value = answers[question]
            if value == "sem_registro":
                out.append({"pergunta": question, "resposta": value, "o_que_falta": "registro da execução"})
            else:
                out.append({"pergunta": question, "resposta": value, "evidencias": evidence_ids[:1],
                            "explicacao": "O trecho mostra o fato."})
        return QuestionnaireOut(respostas=out)

    return handler


def full_handlers(states: dict[str, str] | None = None) -> dict:
    from backend.criteria.doc_sub import DocSubOut
    from backend.criteria.web_sub import QueryPlanOut, WebJudgeOut
    from backend.graph.states import StateJudgeOut

    return extraction_handlers() | {
        DocSubOut: fake_doc_sub,
        QueryPlanOut: fake_query_plan,
        WebJudgeOut: fake_web_judge,
        StateJudgeOut: fake_state(states),
    }


def fake_providers():
    from datetime import date

    from backend.search.base import SearchHit
    from tests.fakes import FakeSearchProvider

    paper = SearchHit(id="src-paper", provider="openalex", title="Priority queues for ledgers", url="https://doi.org/p",
                      snippet="We study priority queues for batches in ledgers.", published_date=date(2018, 2, 1),
                      date_source="metadata")
    return {"literatura": FakeSearchProvider("openalex", [paper])}


def fake_report_text(messages):
    from backend.report.redact import ReportTextOut

    return ReportTextOut(
        resumo="Elegível. O mecanismo foi testado contra os comparadores nas mesmas 200 entradas.",
        justificativa="Elegível: os cinco critérios estão na coluna P&D. A entrevista diverge do registro.",
        limite="Somente lotes de até 500 itens.",
    )


def _with_report(handlers: dict) -> dict:
    from backend.report.redact import ReportTextOut

    return handlers | {ReportTextOut: fake_report_text}


_full_handlers_without_report = full_handlers


def full_handlers(states: dict[str, str] | None = None) -> dict:  # noqa: F811  (adds the report writer)
    return _with_report(_full_handlers_without_report(states))


LAST_FAKE_LLM = None


async def analysed_project(states: dict[str, str] | None = None, owner_id: str = "owner-1"):
    """A project with a finished analysis, run through the whole fake pipeline."""
    from backend.analyses.orchestrator import AnalysisService
    from backend.catalog.loader import get_catalog
    from backend.config import Settings
    from backend.projects.models import Project
    from backend.projects.service import create_project
    from tests.fakes import FakeLLM

    project = await create_project(owner_id, "PRJ90 fila", synthetic_package())
    global LAST_FAKE_LLM
    LAST_FAKE_LLM = FakeLLM(full_handlers(states))
    service = AnalysisService(LAST_FAKE_LLM, fake_providers, Settings(_env_file=None, ollama_model="m"), get_catalog())
    analysis = await service.run(str((await service.create(project)).id))
    return await Project.get(project.id), analysis
