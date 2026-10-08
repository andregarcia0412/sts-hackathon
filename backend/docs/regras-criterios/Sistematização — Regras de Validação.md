---
title: Sistematização — Regras de Validação
created: 2026-10-07
tags: [sts-2026, lei-do-bem, frascati, criterios, sistematizacao, metodologia]
status: draft
---

# Sistematização — Regras de Validação

Critério 4 de [[Regras de Validação dos Critérios de Frascati]]. Evidência vem **só dos documentos do
projeto** (não há busca na internet para este critério). Pergunta do guia do desafio: *"Foi organizado?
Teve método, planejamento e registro, não foi tentativa e erro solto."*

## O que o critério exige

> [!quote] Frascati 2015 §2.19, p. 47 (paráfrase)
> P&D é atividade formal, feita de forma **planejada**, com **registro do processo e do resultado**. Para
> verificar, identificam-se o **propósito** do projeto e as **fontes de financiamento**; o projeto tem
> recursos **humanos e financeiros próprios**. Vale também para projetos pequenos, desde que haja um
> pesquisador encarregado de resolver um problema prático.

- **Brasil:** desenvolvimento experimental = "trabalhos **sistemáticos**" (Decreto 5.798 art. 2º II "c").
  O campo de metodologia do FORMP&D deve descrever a metodologia de **pesquisa ou desenvolvimento
  experimental**, não uma metodologia convencional ou de gestão (Guia MCTI 2020 §6.4, p. 21). Dispêndios
  ficam em **contas contábeis específicas** (Lei 11.196 art. 22 I; Decreto 5.798 art. 10 I) e a
  documentação é guardada durante o **prazo prescricional** (Decreto 5.798 art. 14 §1º).
- **Contexto:** o TCU (Acórdão 447/2025-Plenário) achou divergências entre gastos com pessoal informados
  ao MCTI e os registros oficiais (RAIS/Caged) — vínculo frágil entre equipe, horas e projeto.

## Bloco B — Documentos do projeto

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| SIS-D1 | O **projeto** tem objetivo, escopo e **datas de início e fim** (a unidade é o projeto — ver T1) | termo de abertura, plano, campos 3.1.11–3.1.12 | FAQ MCTI P4(d)–(e); Frascati §2.12; IT MIMIT 2024 §1.1.3.4 |
| SIS-D2 | Há **plano**: etapas, cronograma, marcos, objetivos intermediários e **indicadores de sucesso definidos no início** | plano de projeto datado | Guia MCTI 2020 Ap. B.4; IE TDM §8.1(f); IT MIMIT §1.1.3.4 |
| SIS-D3 | **Recursos próprios** identificados: equipe (nome, titulação, função, horas) **adequada ao problema** (composição, competência, experiência), orçamento e fonte de financiamento | tabela de RH do projeto, currículos, orçamento aprovado | Frascati §2.19; FORMP&D (seção de RH por projeto); IE TDM §8.1(g)–(h); IT MIMIT §1.1.3.4 |
| SIS-D4 | **Dispêndios rastreáveis** ao projeto: contas contábeis específicas e apontamento de horas por pessoa | plano de contas, timesheets | Lei 11.196 art. 22 I; Decreto 5.798 art. 10 I; Portaria 9.563 art. 6º II; FAQ MCTI P2 |
| SIS-D5 | A metodologia é de **pesquisa/experimentação** — hipótese → experimento ou análise → observação → avaliação → conclusão —, não só Scrum, ágil ou gestão, **nem teste de aceite**. Experimento: alternativas (incluindo os comparadores conhecidos) rodadas **nas mesmas entradas**, referência fixada antes e critérios de sucesso definidos **antes da rodada**. Aceite: roteiros com resultado esperado, repetidos até passar | descrição do método + protocolo (`metodo.md#3`), versões dos comparadores em `cronologia.csv`, ensaios em `medicoes.csv` | Guia MCTI 2020 §6.4; FAQ MCTI P4; CRA SR&ED ("How"); AU R&DTI (*systematic progression of work*); 26 CFR §1.41-4(a)(5); IE TDM §3.6 (Lean não é P&D); Históricos PRJ02 ("mesma referência lacrada", limites prévios), PRJ13, PRJ14, PRJ16 × PRJ04 ("a segunda cumpriu os 12 resultados esperados"), PRJ09, PRJ12 |
| SIS-D6 | *Absorvida → T5 (08/10/2026)* | — | — |
| SIS-D7 | Estão registrados os **desvios**: caminhos que falharam e por que se mudou de rumo | registro de decisões, relatório de experimentos sem sucesso | IE TDM §3.1; IT MIMIT §1.1.3.4 |
| SIS-D8 | *Absorvida → T2 (08/10/2026)* | — | — |
| SIS-D9 | *Absorvida → CRI-D3 (pesquisador) e SIS-D3 (adequação da equipe) (08/10/2026)* | — | — |
| SIS-D10 | A documentação fica **guardada e acessível** durante o prazo prescricional | onde e por quanto tempo os documentos ficam guardados | Decreto 5.798 art. 14 §1º; IE TDM §8.4 (integridade, autor e data de cada registro) |

> [!note] Conteúdo mínimo
> Mesmo em projetos pequenos, as Linee guida italianas (§1.1.3.4) exigem pelo menos: **objetivos,
> hipóteses, resultados intermediários, cronograma e orçamento**. Admitem reconstruir o plano depois,
> desde que se identifiquem início, fim e objetivos e o trabalho possa ser ligado a recursos e tempo — a
> Irlanda (TDM §3.1) é mais rígida e exige registros contemporâneos.

## Regras derivadas dos históricos

Extraídas dos 20 projetos classificados do pacote — ver [[Padrão de Análise dos Históricos]]. Na massa,
a prova de sistematicidade sempre veio de `medicoes.csv` (registro primário).

> [!important] Sistematicidade sozinha não prova P&D
> Os 7 não elegíveis têm testes bem organizados — o estado deles é "documentada **como aceite**". A
> pergunta não é *se* houve método, mas se o método era um **experimento** ou um **aceite**.

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| SIS-D11 | *Absorvida → SIS-D5 (08/10/2026)* | — | — |
| SIS-D12 | A execução está registrada **por versão**: cada versão alegada tem ensaio identificado (`ensaio_id`) em `medicoes.csv`. Plano, diagrama ou memorando sem registro de execução → sistematicidade parcial | `cronologia.csv` × `medicoes.csv` × `configuracao.json` | Históricos PRJ08, 10, 17 (uma versão, parâmetros `null`, só contagem de entrega) |
| SIS-D13 | Controles de desenho experimental são **indícios fortes** (não obrigatórios): estrato do caso difícil, repetições para falha intermitente, ordem contrabalançada, separação temporal do rótulo para evitar vazamento | `metodo.md#3`, `configuracao.json` | Históricos PRJ02 (estrato ambíguo), PRJ13 (segmentos escassos, rótulo com atraso de 20 eventos), PRJ15 (ordem contrabalançada), PRJ16 (5 repetições) |
| SIS-D14 | **Contagem de entrega** (quantas linhas/fichas foram entregues) **não** é desempenho e não prova execução; desempenho exige operação e base explícitas (ver T11) | coluna `natureza` e `taxa_percentual` de `resultados.csv` | [[LEIA_ME]] (dicionário de resultados); Históricos PRJ08, 10, 17 (`natureza = entrega`) |

### Revisão das regras do Bloco B para a massa do hackathon

- **Confirmadas:** SIS-D1 (dossiê traz recorte e data de corte), SIS-D2 (protocolo e critérios prévios),
  SIS-D5 (método experimental — na massa, "método" = comparadores + mesma entrada + critério prévio),
  SIS-D7 (versões que falharam); a contemporaneidade (`cronologia.csv` datada) agora é a T5.
- **Fora do escopo da massa:** SIS-D3 (orçamento e financiamento; a equipe só aparece por função, sem
  titulação), SIS-D4 (horas e despesas — o [[LEIA_ME]] manda **não** avaliar), SIS-D10 (guarda de
  documentos). Plurianual agora é a T2.
- **Fusões de 08/10:** SIS-D6 → T5, SIS-D8 → T2, SIS-D9 → CRI-D3 + SIS-D3, SIS-D11 → SIS-D5.

## Sinais de alerta

- Metodologia = "Scrum", "ágil" ou "PMBOK", sem nada sobre o desafio técnico — FAQ MCTI P4; Guia MCTI 2020 §6.4
- Departamento ou área inteira no lugar de projeto — FAQ MCTI P4(d)
- Sem datas de início e fim — FAQ MCTI P4(e)
- Gastos (principalmente pessoal) sem vínculo claro com o projeto — FAQ MCTI P2; TCU Acórdão 447/2025
- Documentos criados todos de uma vez, no fim — "arqueologia documental" (Guia ANPEI 2017 p. 27)
- Texto do relatório igual ao do ano anterior — Guia MCTI 2020 Ap. B.4

Relacionadas: [[Incerteza — Regras de Validação]] · [[Reprodutibilidade — Regras de Validação]] ·
[[Dossiê e Rastreabilidade]] · [[Principais Motivos de Glosa]]

## Fontes desta nota

Detalhes, links e forma de leitura em [[Regras de Validação — Referências]].

- Frascati 2015 §2.12, §2.19 — [[Frascati Manual 2015 - OECD.pdf]]
- Lei 11.196/2005 art. 22 — [[Lei 11.196-2005 (Lei do Bem) - Planalto.pdf]]
- Decreto 5.798/2006 arts. 2º, 10, 14 — [[Decreto 5.798-2006 - Planalto.pdf]]
- Portaria MCTI 9.563/2025 art. 6º — [[Portaria MCTI 9.563-2025.pdf]]
- Guia Prático MCTI 2020 §6.4, Ap. B.4 — [[Guia Pratico da Lei do Bem 2020 - MCTI.pdf]]
- FAQ MCTI P2, P4 — [[Lei do Bem FAQ - MCTI.pdf]]
- Guia ANPEI/MCTIC 2017 p. 27 — [[Guia da Lei do Bem 2017 - ANPEI-MCTI.pdf]]
- TCU, Acórdão 447/2025-Plenário (notícia) — <https://portal.tcu.gov.br/imprensa/noticias/lei-do-bem-tcu-identifica-problemas-na-prestacao-de-contas-das-empresas-beneficiadas>
- CRA SR&ED — <https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/sred-policies-guidelines/guidelines-eligibility-work-sred-tax-incentives.html>
- AU R&DTI, atividades e registros — <https://business.gov.au/grants-and-programs/research-and-development-tax-incentive/check-if-you-are-eligible-for-the-randd-tax-incentive/conducting-core-activities> · <https://www.business.gov.au/grants-and-programs/research-and-development-tax-incentive/assess-if-your-randd-activities-are-eligible/records-to-show-eligibility>
- 26 CFR §1.41-4 — <https://www.law.cornell.edu/cfr/text/26/1.41-4>
- IE Revenue TDM 29-02-03 §3.1, §3.6, §8.1, §8.4 — <https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-29/29-02-03.pdf>
- IT MIMIT Linee guida 2024 §1.1.3.4 — <https://www.mimit.gov.it/images/stories/normativa/LineeguidacreditoRS-4luglio2024.pdf>
