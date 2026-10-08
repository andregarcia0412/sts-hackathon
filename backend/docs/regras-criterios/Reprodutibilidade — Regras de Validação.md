---
title: Reprodutibilidade — Regras de Validação
created: 2026-10-07
tags: [sts-2026, lei-do-bem, frascati, criterios, reprodutibilidade, transferibilidade]
status: draft
aliases: [Transferibilidade — Regras de Validação]
---

# Reprodutibilidade — Regras de Validação

Critério 5 de [[Regras de Validação dos Critérios de Frascati]] (no Frascati: *transferable and/or
reproducible*). Evidência vem **só dos documentos do projeto**. Pergunta do guia do desafio: *"Dá para
reproduzir? O conhecimento gerado pode ser transferido e o resultado repetido."*

## O que o critério exige

> [!quote] Frascati 2015 §2.20, p. 48 (paráfrase)
> O projeto deve permitir **transferir o conhecimento novo** e deixar outros pesquisadores reproduzirem
> os resultados — inclusive os **negativos** (hipótese não confirmada, produto que não saiu como
> planejado). Os resultados **não podem ficar tácitos**, só na cabeça da equipe. Na empresa podem ser
> protegidos por sigilo ou propriedade intelectual, mas espera-se que processo e resultados sejam
> **registrados** para uso de outros pesquisadores da própria empresa.

- **Frascati Tab. 2.1(d), p. 48:** a transferência pode ser demonstrada, por exemplo, por publicação
  científica ou por instrumentos de proteção da propriedade intelectual.
- **Brasil:** a Tecnologia Industrial Básica inclui "a documentação técnica gerada e o patenteamento"
  (Decreto 5.798 art. 2º II "d"). O FORMP&D tem campos de resultado (3.1.13–3.1.14) e uma seção de
  patentes e registros; o descritivo complementar pede resultados alcançados, número de protótipos e
  ensaios, patentes e trabalhos acadêmicos (Guia MCTI 2020 §6.5, pp. 21–22).
- **Reprodutível ≠ publicado:** basta o potencial de reprodução por outro pesquisador, mesmo interno; patente
  ou segredo industrial não impedem o critério (IT MIMIT 2024 §1.1.3.5).

## Bloco B — Documentos do projeto

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| REP-D1 | O conhecimento gerado está **codificado** num registro (relatório técnico parcial/final), não só no know-how da equipe | relatório técnico datado | Frascati §2.20; IPCTN 2020 Anexo I; Nonaka 1994 (conhecimento tácito vs. explícito) |
| REP-D2 | O registro traz **método, dados, configuração e resultados** com detalhe suficiente para outro profissional competente repetir | seções de método e de resultados do relatório | Frascati §2.20; UK DSIT ¶34 (conhecimento "codificado de forma utilizável por um profissional competente"); NASEM 2019 |
| REP-D3 | **Resultados negativos** e hipóteses refutadas também estão documentados | registro de experimentos sem sucesso | Frascati §2.20; Guia MCTI 2020 §6.2; IT MIMIT §1.1.3.5 |
| REP-D4 | Os **artefatos** estão preservados e versionados: código, dados, modelos treinados, protótipos, protocolos de teste | repositório, versão/commit, local dos dados | Gundersen & Kjensmo 2018; Pineau et al. 2021 (checklist de reprodutibilidade em ML); Wilkinson et al. 2016 (FAIR); ACM Artifact Review and Badging v1.1 |
| REP-D5 | Existe ao menos um **mecanismo de transferência**: patente, registro de software, publicação, documentação interna, treinamento de outra equipe | nº de pedido/registro, DOI, documento interno, lista de presença | Frascati Tab. 2.1(d); Decreto 5.798 art. 2º II "d"; FORMP&D (patentes e registros); IT MIMIT §1.1.3.5 |
| REP-D6 | O registro é **coerente com a sistematização**: as fases planejadas e executadas dão para ser rastreadas do plano ao resultado | ligação entre plano ([[Sistematização — Regras de Validação\|SIS-D2]]) e relatório | IT MIMIT §1.1.3.5 |

> [!info] Vocabulário útil
> - **Reproduzido**: outra equipe obtém o resultado usando os artefatos do autor. **Replicado**: obtém o
>   resultado sem eles, por implementação própria (ACM Artifact Review and Badging v1.1).
> - A NASEM (2019) separa reprodutibilidade (mesmos dados e código → mesmo resultado) de replicabilidade
>   (novo estudo → resultado consistente).
> - Para o Frascati, basta o **potencial** de reprodução — não se exige que alguém de fato reproduza.

## Regras derivadas dos históricos

Extraídas dos 20 projetos classificados do pacote — ver [[Padrão de Análise dos Históricos]]. Na massa,
este critério é o que separa **Elegível** de **Com ressalvas** (estado "documentada no escopo" ×
"documentada com limite").

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| REP-D7 | A conclusão declara o **limite de escopo**. Limite **excluído desde o início** ("não reivindicado") não gera ressalva. Lacuna **dentro da pretensão original** — hipótese do protocolo não ensaiada ou critério prévio não atingido — gera ressalva, que precisa de: recorte sustentado + limitação concreta + evidência necessária. A ressalva é técnica, nunca "falta reprodução por outra equipe" em abstrato | `metodo.md#6` e `#7`, `revisao_tecnica.md`, flags `..._executado: false` em `configuracao.json` | Históricos PRJ03, 14, 15, 16 (limite excluído → elegível) × PRJ05 (corte de energia), PRJ06 (exclusão concorrente), PRJ07 (adulteração local), PRJ18 (meta 100% → 96%); [[GUIA_DO_PARTICIPANTE]] |
| REP-D8 | Documentação completa **de uma configuração** reproduz a configuração, não um conhecimento novo: "a existência de documentação não transforma rotina em P&D" | natureza do que está documentado | Históricos PRJ01, 04, 09, 11, 12, 19, 20 (estado "documentada para a configuração") |
| REP-D9 | Os números do parecer são **recalculáveis** do registro primário (`medicoes.csv` → `resultados.csv`) e ligados a ensaio e versão (hierarquia de prova: ver T9) | recálculo a partir de `medicoes.csv` | [[LEIA_ME]]; Históricos PRJ02, 13, 15 |

### Revisão das regras do Bloco B para a massa do hackathon

- **Confirmadas:** REP-D1, D2, D3 (PRJ18 registra os 2.000 casos sem trilha completa), D6.
- **REP-D4 adaptada:** na massa não há código executável — "as especificações não equivalem a um programa
  executável". O artefato reproduzível é **especificação + `configuracao.json` + registros por versão**
  (PRJ16: "a transferência é da especificação e dos resultados sintéticos").
- **REP-D5 fora do escopo da massa:** não há patentes ou publicações; a documentação interna basta.

## Sinais de alerta

- O único resultado registrado é "funcionou" ou "foi implantado"
- Nenhum relatório técnico; o conhecimento depende de uma pessoa
- Código, dados ou modelo sem versão ou sem local definido
- Protótipo sem documentação de testes — Frascati §2.21 (exemplo da engenharia mecânica: transferibilidade vem da documentação técnica dos testes)

Relacionadas: [[Sistematização — Regras de Validação]] · [[Dossiê e Rastreabilidade]] ·
[[Projetos de Software e IA na Lei do Bem]]

## Fontes desta nota

Detalhes, links e forma de leitura em [[Regras de Validação — Referências]].

- Frascati 2015 §2.20–2.21, Tab. 2.1 — [[Frascati Manual 2015 - OECD.pdf]]
- Decreto 5.798/2006 art. 2º II "d" — [[Decreto 5.798-2006 - Planalto.pdf]]
- Guia Prático MCTI 2020 §6.2, §6.5 — [[Guia Pratico da Lei do Bem 2020 - MCTI.pdf]]
- UK DSIT Guidelines ¶34 — <https://assets.publishing.service.gov.uk/media/5a7952ce40f0b676f4a7d80c/rd-tax-purposes.pdf>
- IT MIMIT Linee guida 2024 §1.1.3.5 — <https://www.mimit.gov.it/images/stories/normativa/LineeguidacreditoRS-4luglio2024.pdf>
- IPCTN 2020 Anexo I — <https://www.fct.pt/wp-content/uploads/2022/09/ipctn20i_Pag_16-20.pdf>
- Nonaka 1994 — <https://doi.org/10.1287/orsc.5.1.14>
- NASEM 2019 — <https://doi.org/10.17226/25303>
- Gundersen & Kjensmo 2018 — <https://doi.org/10.1609/aaai.v32i1.11503>
- Pineau et al. 2021 — <https://jmlr.org/papers/v22/20-303.html>
- Wilkinson et al. 2016 (FAIR) — <https://doi.org/10.1038/sdata.2016.18>
- ACM Artifact Review and Badging v1.1 — <https://www.acm.org/publications/policies/artifact-review-and-badging-current>
