---
title: Criatividade — Regras de Validação
created: 2026-10-07
tags: [sts-2026, lei-do-bem, frascati, criterios, criatividade]
status: draft
---
-
# Criatividade — Regras de Validação

Critério 2 de [[Regras de Validação dos Critérios de Frascati]]. Evidência vem da **busca na internet** e
dos **documentos do projeto**. Pergunta do guia do desafio: *"Foi criativo? Partiu de uma ideia ou
hipótese própria, e não de um manual."*

## O que o critério exige

> [!quote] Frascati 2015 §2.17, p. 47 (paráfrase)
> O projeto busca **conceitos ou hipóteses originais e não óbvios** que melhorem o conhecimento existente.
> Mudança rotineira de produto ou processo fica de fora. Como a criatividade exige contribuição humana,
> o projeto precisa de um **pesquisador**. Métodos novos para tarefas comuns contam (ex.: processar dados
> não é P&D, mas desenvolver um método novo de processamento é).

- **Frascati Tab. 2.1(b)–(c), p. 48:** abordagem criativa inclui novas aplicações de conhecimento
  científico existente ou novos usos de técnicas disponíveis; a **escolha do método** pode fazer parte da
  criatividade.
- **Pesquisador** (Frascati §5.35, p. 162): profissional que concebe ou cria conhecimento novo. No
  Brasil, "pesquisador contratado" está no Decreto 5.798 art. 2º III.
- **Brasil:** o Guia MCTI 2020 §6 e §6.2 (pp. 19–20) usa o teste de **não-obviedade** — a solução não é
  óbvia para quem conhece as técnicas básicas do setor (texto vindo do Frascati 2002 §84). O §6.2 chama
  o elemento novo de "a hipótese que está sendo testada para superação da barreira".

## Bloco A — Busca na internet

O teste de não-obviedade das patentes serve de roteiro (analogia — Frascati não exige patenteabilidade).

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| CRI-W1 | Aplicar o roteiro **problema-solução**: (i) achar o estado da arte mais próximo, (ii) definir o problema técnico que o projeto resolve a partir dele, (iii) verificar se um técnico no assunto chegaria à solução de forma óbvia | documento mais próximo + problema técnico + justificativa da não-obviedade | EPO G-VII 5; INPI Res. 169/2016 itens 5.9–5.21; LPI art. 13; Guia MCTI 2020 §6; Frascati 2002 (PT) §84 |
| CRI-W2 | Se a abordagem do projeto aparece como **prática padrão** (documentação oficial da ferramenta, tutorial, manual), é rotina | link do material que descreve a mesma abordagem | Guia do desafio, Parte 4; Frascati §2.72 ("métodos conhecidos e ferramentas existentes") |
| CRI-W3 | Combinação de elementos conhecidos só é criativa se o efeito conjunto **vai além da soma** dos efeitos isolados; justaposição simples é óbvia | comparação dos efeitos isolados vs. combinados | INPI itens 5.22 e 5.30 |
| CRI-W4 | Trazer conhecimento **de outro campo** conta quando a adaptação não era facilmente dedutível | origem do conhecimento + o que precisou ser adaptado | UK DSIT ¶6 e ¶23; IT MIMIT 2024 §1.1.3.2; Frascati Tab. 2.1(b) |
| CRI-W5 | Indícios a favor: o problema era **conhecido há tempo e não resolvido**, ou o projeto seguiu um caminho **contrário ao consenso** técnico | literatura relatando o problema em aberto ou o consenso contrariado | INPI itens 5.57 e 5.58 |

## Bloco B — Documentos do projeto

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| CRI-D1 | Há **hipótese explícita** (ideia ou abordagem proposta para superar a barreira), registrada antes dos testes | plano, ata ou relatório datado com a hipótese | Guia MCTI 2020 §6.2; CRA SR&ED ("How": gerar uma ideia coerente com fatos conhecidos); AU R&DTI (hipótese antes do trabalho); IE TDM §8.1(f) |
| CRI-D2 | Há **obstáculo técnico** que exigiu solução original, descrito de forma concreta | campo 3.1.8 (barreira) / relatório técnico | IT MIMIT §1.1.3.2; Guia MCTI 2020 §6.3; FORMP&D 3.1.8 |
| CRI-D3 | A equipe inclui **pesquisador** — e dá para saber quem formulou a hipótese, com qual qualificação e dedicação | lista da equipe com titulação, função e horas | Frascati §2.17, §2.19, §5.35–5.36, Tab. 2.1(e); Decreto 5.798 art. 2º III; Guia ANPEI 2017 p. 27; IE TDM §8.1(g)–(h); IT MIMIT §1.1.3.4 |
| CRI-D4 | Estão registradas as **alternativas** consideradas e as abandonadas, inclusive os insucessos | registro de decisões técnicas, experimentos descartados | IT MIMIT §1.1.3.2; IE TDM §3.1; 26 CFR §1.41-4(a)(5) (identificar alternativas) |
| CRI-D5 | A mudança **não é rotineira**: não se resume a layout, design, **configurar, ativar, cadastrar, mapear campos ou ajustar parâmetro dentro da faixa já suportada** pelo produto, sem alterar o algoritmo | o que mudou tecnicamente; verbos do mecanismo em `metodo.md#2`; frases como "nenhum algoritmo foi modificado" | Frascati §2.17 e §2.56; Guia MCTI 2020 Ap. B.1; FAQ MCTI P17; Históricos PRJ01 (retenção dentro de 10–300 s), PRJ04, 09, 11, 12, 19 ("não treinar modelo nem alterar pré-processador"), 20 |
| CRI-D6 | Método novo para tarefa comum **conta** (ex.: novo método de processamento de dados) | descrição do método e do que ele tem de diferente | Frascati §2.17; IT MIMIT §1.1.3.2 |
| CRI-D7 | Quem afirma a criatividade/avanço é **profissional competente** na área (qualificação + conhecimento do estado da arte), não alguém só com interesse no tema | currículo / justificativa assinada | HMRC GfC3 parte 3 |

> [!tip] Como avaliar algo subjetivo
> A criatividade é avaliada de forma confiável pelo **consenso de especialistas independentes** que
> conhecem o domínio (Consensual Assessment Technique — Amabile 1982). É a mesma lógica dos dois
> avaliadores independentes do MCTI (Portaria 9.563/2025 art. 7º). Para a ferramenta: a regra produz
> evidência; quem julga é o analista.

## Regras derivadas dos históricos

Extraídas dos 20 projetos classificados do pacote — ver [[Padrão de Análise dos Históricos]]. Na massa,
a prova de criatividade sempre veio de `metodo.md#2` (Mecanismo e hipótese).

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| CRI-D8 | O mecanismo está especificado com **regra de decisão e parâmetros concretos** (limiares, pesos, janelas, condições de empate, pseudocódigo), não só com o nome de uma técnica. Plano ou diagrama sem limiares, empate ou versão definida → criatividade indeterminada | `metodo.md#2`, `metodo.md#4`, `configuracao.json` (parâmetros não nulos) | Históricos PRJ02 (custo 0,6/0,4, margem 0,15), PRJ03 (histerese), PRJ13 (2,5/3,0 desvios) × PRJ08 (`limiares: null`), PRJ10 (sem regra de empate), PRJ17 (políticas só "antiga/nova") |
| CRI-D9 | *Absorvida → CRI-D5 (08/10/2026)* | — | — |
| CRI-D10 | A criatividade **não exige inventar primitiva** (cifra, algoritmo criptográfico, novo modelo): pode estar num acoplamento ou numa combinação original, desde que testada contra os conhecidos. Mas **renomear** técnica conhecida não conta | mecanismo vs. comparadores nomeados em `metodo.md#1` | Históricos PRJ05 ("não envolve inventar cifra"), PRJ07 ("não criar um algoritmo criptográfico"), PRJ03 ("não um novo nome para retry"); Frascati Tab. 2.1(b) |

### Revisão das regras A e B para a massa do hackathon

- **CRI-D1, D2, D4, D5 e D6** batem com o que os avaliadores usaram: hipótese explícita, obstáculo
  técnico, alternativas comparadas e exclusão de mudança rotineira.
- **CRI-W1…W5 (internet):** complementares — os manuais citados nos projetos são fictícios (ver a revisão
  em [[Novidade — Regras de Validação#Revisão das regras A e B para a massa do hackathon]]).
- **Fusões de 08/10:** CRI-D9 → CRI-D5; CRI-D3 absorveu o pesquisador da antiga SIS-D9.
- **CRI-D3 (pesquisador) e CRI-D7 (profissional competente):** não dá para verificar na massa — as
  atividades só trazem `responsavel_por_funcao` (ex.: "Engenharia de Mensageria"), sem titulação. Nenhum
  histórico usou esse ponto.

## Sinais de alerta

- Não há hipótese — só um objetivo de produto
- A solução está num manual, tutorial ou documentação de fornecedor
- Equipe só de suporte/operação, sem pesquisador — Frascati §2.17
- O trabalho é configurar, parametrizar ou integrar ferramenta pronta — Frascati §2.72
- A pergunta registrada já nomeia a solução conhecida ou o produto contratado ("como **aplicar
  idempotência conhecida**…", "como **integrar ao cofre contratado**") — Históricos PRJ01, PRJ12 *(sinal
  fraco: a decisão vem do mecanismo)*

Relacionadas: [[Novidade — Regras de Validação]] · [[Incerteza — Regras de Validação]] ·
[[Prova de Não Rotina]]

## Fontes desta nota

Detalhes, links e forma de leitura em [[Regras de Validação — Referências]].

- Frascati 2015 §2.17, Tab. 2.1, §2.56, §2.72, §5.35–5.36 — [[Frascati Manual 2015 - OECD.pdf]]
- Frascati 2002 (PT-BR) §84 — [[Manual de Frascati 2002 (PT-BR) - OCDE.pdf]]
- Decreto 5.798/2006 art. 2º III — [[Decreto 5.798-2006 - Planalto.pdf]]
- Portaria MCTI 9.563/2025 art. 7º — [[Portaria MCTI 9.563-2025.pdf]]
- Guia Prático MCTI 2020 §6, §6.2, §6.3, Ap. B.1 — [[Guia Pratico da Lei do Bem 2020 - MCTI.pdf]]
- FAQ MCTI P17 — [[Lei do Bem FAQ - MCTI.pdf]]
- Guia ANPEI/MCTIC 2017 p. 27 — [[Guia da Lei do Bem 2017 - ANPEI-MCTI.pdf]]
- Guia do desafio, Parte 4 — [[Guia_do_Desafio_Hackathon_STS_2026 - guia-do-desafio-hackathon-sts-2026.pdf]]
- LPI 9.279/1996 art. 13 — <https://www.planalto.gov.br/ccivil_03/leis/l9279.htm>
- INPI Res. 169/2016 — <https://www.wipo.int/wipolex/edocs/lexdocs/laws/pt/br/br170pt.pdf>
- EPO Guidelines 2025 G-VII 5 — <https://www.epo.org/en/legal/guidelines-epc/2025/g_vii_5.html>
- UK DSIT Guidelines ¶6, ¶23 — <https://assets.publishing.service.gov.uk/media/5a7952ce40f0b676f4a7d80c/rd-tax-purposes.pdf>
- HMRC GfC3 parte 3 — <https://www.gov.uk/government/publications/help-to-see-if-your-work-qualifies-as-research-and-development-for-tax-purposes-gfc3/importance-of-a-competent-professional-part-3>
- CRA SR&ED — <https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/sred-policies-guidelines/guidelines-eligibility-work-sred-tax-incentives.html>
- AU R&DTI — <https://business.gov.au/grants-and-programs/research-and-development-tax-incentive/check-if-you-are-eligible-for-the-randd-tax-incentive/conducting-core-activities>
- 26 CFR §1.41-4 — <https://www.law.cornell.edu/cfr/text/26/1.41-4>
- IE Revenue TDM 29-02-03 — <https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-29/29-02-03.pdf>
- IT MIMIT Linee guida 2024 §1.1.3.2 — <https://www.mimit.gov.it/images/stories/normativa/LineeguidacreditoRS-4luglio2024.pdf>
- Amabile 1982 — <https://doi.org/10.1037/0022-3514.43.5.997>
