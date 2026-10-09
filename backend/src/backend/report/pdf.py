from pathlib import Path

from fpdf import FPDF
from fpdf.enums import WrapMode

from backend.graph.classify import CLASS_LABELS
from backend.report.builder import Parecer

FONTS = Path(__file__).with_name("fonts")
LINE = 5


class _Doc(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.add_font("DejaVu", "", FONTS / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", FONTS / "DejaVuSans-Bold.ttf")
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 7)
        self.cell(0, 5, f"Parecer preliminar gerado pelo sistema — a decisão é do analista. Página {self.page_no()}", align="C")

    def h1(self, text: str) -> None:
        self.set_font("DejaVu", "B", 15)
        self.multi_cell(0, 8, text, wrapmode=WrapMode.CHAR, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h2(self, text: str) -> None:
        self.ln(2)
        self.set_font("DejaVu", "B", 11)
        self.multi_cell(0, 6, text, wrapmode=WrapMode.CHAR, new_x="LMARGIN", new_y="NEXT")

    def p(self, text: str, size: int = 9, bold: bool = False) -> None:
        self.set_font("DejaVu", "B" if bold else "", size)
        self.multi_cell(0, LINE, text or "-", wrapmode=WrapMode.CHAR, new_x="LMARGIN", new_y="NEXT")

    def bullets(self, items: list[str], size: int = 8) -> None:
        for item in items or ["(nenhum)"]:
            self.p(f"• {item}", size=size)


def render_pdf(parecer: Parecer) -> bytes:
    doc = _Doc()
    doc.h1(f"{parecer.projeto_id} — {parecer.titulo}")
    doc.p(f"Gerado em {parecer.gerado_em:%d/%m/%Y %H:%M} UTC · análise {parecer.rastreabilidade.analysis_id} "
          f"(versão {parecer.rastreabilidade.version})", size=8)

    doc.h2("Resumo")
    doc.p(f"Classificação sugerida pelo sistema: {parecer.classificacao or 'sem classe automática'}", size=11, bold=True)
    if parecer.inconsistente:
        doc.p("Atenção: combinação de estados fora dos padrões do gabarito — revisar. Caminho: "
              + " → ".join(parecer.caminho_arvore), size=8)
    doc.p(parecer.resumo)
    for item in parecer.incompleto:
        doc.p(f"Pendência do parecer: {item}", size=8)
    if parecer.ressalva:
        r = parecer.ressalva
        doc.p(f"Recorte sustentado: {r.recorte_sustentado or '-'}\nLimitação: {r.limitacao or '-'}\n"
              f"Evidência necessária: {r.evidencia_necessaria or '-'}")
    if parecer.elo_ausente:
        e = parecer.elo_ausente
        doc.p(f"Elo ausente: {e.elo_ausente or '-'}\nEvidências a solicitar: {', '.join(e.evidencias_a_solicitar) or '-'}")

    doc.h2("Decisão do analista")
    if parecer.decisoes_analista:
        for d in parecer.decisoes_analista:
            doc.p(f"{d.decided_at:%d/%m/%Y %H:%M} — {d.analyst_name}: {CLASS_LABELS.get(d.outcome, d.outcome)}. "
                  f"Justificativa: {d.justification}")
        doc.p(f"Sugestão original do sistema (preservada): {parecer.classificacao or '-'}", size=8)
    else:
        doc.p("Ainda não decidido. A classificação acima é sugestão do sistema.")

    doc.h2("Justificativa")
    doc.p(parecer.justificativa)
    doc.p(f"Limite da conclusão: {parecer.limite or '-'}")

    doc.h2("Os cinco critérios")
    for section in parecer.criterios:
        doc.p(f"{section.criterio}: {section.estado or 'não avaliado'}"
              + (f" (nota indicativa {section.nota})" if section.nota is not None else ""), size=10, bold=True)
        doc.p(section.justificativa)
        doc.p(f"Fonte: {section.fonte or '-'} · Norma: {section.fonte_normativa}", size=8)
        for gate in section.gates:
            doc.p(f"Gate aplicado: {gate}", size=8)
        if section.respostas:
            doc.bullets([f"{a.pergunta} — {a.texto} → {a.resposta}"
                         + (f": {a.explicacao}" if a.explicacao else "")
                         + (f" [{', '.join(a.fontes)}]" if a.fontes else "")
                         + (f" (falta: {a.o_que_falta})" if a.o_que_falta and a.resposta == "sem_registro" else "")
                         + (" (gate do sistema)" if a.origem == "gate" else "") for a in section.respostas], size=7)
            doc.p(f"Tabela de decisão: {section.regra_de_decisao or '-'}", size=7)

    doc.h2("Evidências utilizadas (favoráveis)")
    doc.bullets([f"{e.regra} [{e.fonte}] “{e.trecho}” — {e.explicacao}" for e in parecer.evidencias_usadas])
    doc.h2("Evidências contrárias")
    doc.bullets([f"{e.regra} [{e.fonte}] “{e.trecho}” — {e.explicacao}" for e in parecer.evidencias_contrarias])
    doc.h2("Divergências entre depoimento e documento")
    doc.bullets(parecer.divergencias)
    doc.h2("Elos ausentes e lacunas")
    doc.bullets(parecer.elos_ausentes)
    doc.bullets([f"{g.regra} ({g.status}): {g.motivo}" for g in parecer.lacunas], size=7)

    doc.h2("Rastreabilidade")
    t = parecer.rastreabilidade
    doc.p(f"Regras aplicadas: {t.regras_aplicadas} · catálogo {t.catalog_version} · schema {t.schema_version} · "
          f"temperatura {t.temperature}", size=8)
    doc.p("Modelos: " + ", ".join(f"{role}={model}" for role, model in t.models.items()), size=8)
    doc.p("Arquivos (sha256): " + "; ".join(f"{path}={digest[:12]}" for path, digest in t.file_hashes.items()), size=7)

    doc.h2("Anexo — busca na internet (reproduzível)")
    doc.bullets([f"{s.executed_at:%d/%m/%Y %H:%M} · {s.front}/{s.base} · original: “{s.original_query}” → enviada: "
                 f"“{s.sanitized_query}” · {s.n_results} resultados · selecionados: {', '.join(s.selected) or '-'}"
                 + (f" · erro: {s.error}" if s.error else "") for s in parecer.anexo_busca], size=7)
    return bytes(doc.output())
