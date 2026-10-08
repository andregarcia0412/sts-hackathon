---
title: Incerteza — Regras de Validação
created: 2026-10-07
tags: [sts-2026, lei-do-bem, frascati, criterios, incerteza, risco-tecnologico]
status: draft
---

# Incerteza — Regras de Validação

Critério 3 de [[Regras de Validação dos Critérios de Frascati]]. Evidência vem da **busca na internet** e
dos **documentos do projeto**. Pergunta do guia do desafio: *"Havia incerteza? Ninguém sabia de antemão
se ia funcionar, nem quanto custaria."*

## O que o critério exige

> [!quote] Frascati 2015 §2.18, p. 47 (paráfrase)
> A incerteza tem várias dimensões: no início do projeto não dá para determinar com precisão o **tipo de
> resultado** nem o **custo e o tempo** para chegar lá — nem se o objetivo será alcançado. Exemplo-chave:
> **protótipo de P&D** testa conceito técnico com alto risco de falha; protótipo que não é P&D é unidade
> de pré-produção para certificação.

- **Brasil:** a linha entre P&D e "engenharia" é o **risco tecnológico** (FAQ MCTI P17; Guia MCTI 2020
  Ap. B.1, pp. 46–47). A barreira tecnológica é o conjunto de etapas ou eventos que podem levar o projeto
  ao **insucesso** (Guia MCTI 2020 §6.3, pp. 20–21; FORMP&D 3.1.8). O Guia ANPEI 2017 (p. 27) põe
  "Qual o risco tecnológico do projeto?" entre as perguntas iniciais.
- **Software:** o projeto deve ter como objetivo a resolução sistemática de uma incerteza científica ou
  tecnológica (Frascati 2015 §2.68).

## Bloco A — Busca na internet

Aqui a busca é pela **solução da barreira**, não pelo produto (isso é a [[Novidade — Regras de Validação|novidade]]).

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| INC-W1 | A solução da barreira declarada **já estava disponível** ou era facilmente dedutível por um profissional competente na data de início? Se sim, não há incerteza | resultados de busca sobre a barreira (com data) | UK DSIT ¶13–14; CRA SR&ED ("Why"); AU R&DTI (conhecimento acessível "em qualquer lugar do mundo"); IE TDM §3.4; HMRC GfC3 parte 2, passo 4 |
| INC-W2 | **Não saber internamente** não é incerteza: se a solução era razoavelmente acessível (publicada, consultoria, especialista), a falta de know-how ou de diligência da empresa não conta | evidência de que a solução não estava publicada nem disponível | IE TDM §3.4; IT MIMIT 2024 §1.1.3.3; CRA SR&ED (base de conhecimento = equipe **+** fontes públicas razoavelmente acessíveis) |
| INC-W3 | A literatura ou documentação técnica relata o problema como **em aberto** ou aponta limitações das soluções existentes *(regra derivada)* | trechos de artigos, issues ou relatórios que descrevem a limitação | Guia MCTI 2020 §6.2 (descrever limitações das soluções existentes); INPI item 5.57 (analogia) |
| INC-W4 | Maturidade da tecnologia no setor como indício: quanto mais baixo o **TRL**, maior a incerteza *(heurística)* | TRL estimado com base no que foi encontrado | Guia MCTI 2020 §6.2 (estágios da prova de conceito à validação operacional, com incerteza decrescente); ISO 16290:2013; NASA TRL; Mankins 2009 |

## Bloco B — Documentos do projeto

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| INC-D1 | A incerteza é **técnica/científica e intrínseca** — não de mercado, financiamento, prazo comercial, viabilidade comercial **nem de regra de negócio ou política** (diferença de resultado causada por política não é falha técnica) | descrição do risco e da sua causa; origem das divergências registradas | FAQ MCTI P4(b); IT MIMIT §1.1.3.3; IE TDM §3.5; Jalonen 2011 (8 tipos de incerteza da inovação — tecnológica, mercado, regulatória, social/política, aceitação, gerencial, timing, consequência; só a tecnológica serve aqui); Histórico PRJ20 ("diferenças de política, não falha científica a resolver") |
| INC-D2 | A incerteza está formulada como **pergunta técnica específica**: (a) dá para atingir o objetivo? ou (b) qual método atende às especificações (custo, confiabilidade, reprodutibilidade)? | lista nominal das incertezas | IE TDM §3.5(a)–(b); UK DSIT ¶13; HMRC GfC3 parte 2, passo 3; Guia MCTI 2020 §6.3 |
| INC-D3 | O projeto explica **por que** um profissional competente não resolveria aquilo com o conhecimento disponível | justificativa técnica | HMRC GfC3 parte 2, passo 4; UK DSIT ¶14 |
| INC-D4 | Há sinais de que o resultado **não era previsível**: atrasos, falhas, reprojetos, hipóteses refutadas — desde que sejam falhas **experimentais**, não operacionais (ver INC-D9); diz se a barreira foi superada ou o que ainda está sendo testado | relatórios de teste, registro de falhas, cronograma revisado | IT MIMIT §1.1.3.3; Guia MCTI 2020 §6.3; IE TDM §3.1 |
| INC-D5 | A incerteza foi **enfrentada**, não contornada: se o time desviou do problema usando conhecimento disponível (*workaround*), não conta | decisão técnica registrada | CRA SR&ED ("Why") |
| INC-D6 | Integração de sistemas só tem incerteza se **não era dedutível como combinar** os componentes; montar peças num padrão estabelecido não tem | descrição do problema de integração | UK DSIT ¶29–30 ("system uncertainty"); Frascati §2.73 |
| INC-D7 | Protótipo/piloto testa **conceito técnico arriscado**; unidade pré-produção, produção-teste ou ajuste fino para produzir não é P&D | finalidade do protótipo e o que foi testado | Frascati §2.18, §2.49–2.50, Tab. 2.3 (p. 61), §2.55–2.56 |
| INC-D8 | Dá para delimitar **início e fim** da P&D: começa quando o trabalho sobre a incerteza começa; termina quando ela é resolvida, abandonada ou o conhecimento é codificado. Levantar requisitos sem questão técnica não é P&D; estudo de viabilidade só conta como 1ª etapa de um projeto de P&D | datas de início/fim da etapa incerta | UK DSIT ¶33–34; HMRC GfC3 parte 2, passos 6–7; FAQ MCTI P4(c) |
| INC-D9 | Correção de bugs, *troubleshooting*, otimização e ajuste fino que não mexem na tecnologia de base **não são** incerteza. Isso inclui a **falha operacional** — resolvida por parâmetro, permissão, cadastro, mapeamento ou receita do fornecedor. Só a falha **experimental** (hipótese que pode não se confirmar) indica incerteza | natureza das tarefas; o que mudou entre v1 e v2 (`cronologia.csv`, `metodo.md#2`) e por quê | Frascati §2.57, §2.72; UK DSIT ¶14, ¶35; Guia do desafio, Parte 1; Guia do Participante, passo 5; Históricos PRJ01 (retenção), PRJ04 e PRJ09 (permissão), PRJ11 (cadastro), PRJ12 (janela do manual) |
| INC-D10 | Incerteza de **custo/tempo** conta quando decorre da técnica (atingir uma meta de custo pode exigir resolver um problema técnico); custo alto por motivo comercial não conta | ligação entre a meta de custo e a questão técnica | Frascati §2.18; IT MIMIT §1.1.3.3; IE TDM §3.5 |

> [!note] Novidade e incerteza andam juntas
> Combinar componentes pouco testados aumenta a **variabilidade** do resultado — mais chance de fracasso
> e de grande sucesso (Fleming 2001). Uma regra de novidade forte sem nenhuma incerteza registrada é
> um sinal de inconsistência na descrição.

## Regras derivadas dos históricos

Extraídas dos 20 projetos classificados do pacote — ver [[Padrão de Análise dos Históricos]].

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| INC-D11 | *Absorvida → INC-D9 (08/10/2026)* | — | — |
| INC-D12 | A incerteza só é "investigada" quando a hipótese foi **executada e confrontada com os comparadores conhecidos** e há registro do resultado. Hipótese só em plano, diagrama ou memorando → "alegada, não verificável" | ensaios por versão em `medicoes.csv` cobrindo a hipótese e os comparadores | Históricos PRJ02, 03, 13–16 (investigada) × PRJ08, 10, 17 (alegada) |
| INC-D13 | *Absorvida → INC-D1 (08/10/2026)* | — | — |

### Revisão das regras A e B para a massa do hackathon

- **INC-D4 agora remete à INC-D9:** atrasos, falhas e reprojetos só contam se forem falhas da
  hipótese. Na massa, os 7 não elegíveis também têm falha na v1 — corrigida por configuração.
- **INC-D9** (bugs, ajuste fino, falha operacional) é a regra que mais aparece nos não elegíveis.
- **Fusões de 08/10:** INC-D11 → INC-D9, INC-D13 → INC-D1.
- **INC-D10** confirmada: em PRJ18 a meta de latência (≤ 10 %) era técnica e entrou como critério prévio.
- **INC-W1…W4 (internet):** complementares, pelo mesmo motivo da Novidade.
- **Pouco aplicáveis à massa:** INC-D7 (quase não há protótipos físicos) e INC-D8 (início e fim vêm
  prontos em `cronologia.csv`).

## Sinais de alerta

- "Risco" descrito como prazo, orçamento, adoção pelo cliente ou mercado — FAQ MCTI P4(b)
- Nenhuma falha, alternativa ou ajuste registrado durante todo o projeto
- "Não sabíamos fazer" sem mostrar que ninguém sabia — IE TDM §3.4
- Protótipo feito só para homologação/certificação — Frascati §2.18

Relacionadas: [[Criatividade — Regras de Validação]] · [[Sistematização — Regras de Validação]] ·
[[Prova de Não Rotina]] · [[Atividades Elegíveis vs Não Elegíveis]]

## Fontes desta nota

Detalhes, links e forma de leitura em [[Regras de Validação — Referências]].

- Frascati 2015 §2.18, §2.49–2.57, Tab. 2.3, §2.68, §2.72–2.73 — [[Frascati Manual 2015 - OECD.pdf]]
- Guia Prático MCTI 2020 §6.2, §6.3, Ap. B.1 — [[Guia Pratico da Lei do Bem 2020 - MCTI.pdf]]
- FAQ MCTI P4, P17 — [[Lei do Bem FAQ - MCTI.pdf]]
- Guia ANPEI/MCTIC 2017 p. 27 — [[Guia da Lei do Bem 2017 - ANPEI-MCTI.pdf]]
- Guia do desafio, Parte 1 — [[Guia_do_Desafio_Hackathon_STS_2026 - guia-do-desafio-hackathon-sts-2026.pdf]]
- UK DSIT Guidelines ¶13–14, ¶29–30, ¶33–35 — <https://assets.publishing.service.gov.uk/media/5a7952ce40f0b676f4a7d80c/rd-tax-purposes.pdf>
- HMRC GfC3 parte 2 — <https://www.gov.uk/government/publications/help-to-see-if-your-work-qualifies-as-research-and-development-for-tax-purposes-gfc3/expectations-of-claimants-part-2>
- CRA SR&ED — <https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/sred-policies-guidelines/guidelines-eligibility-work-sred-tax-incentives.html>
- AU R&DTI — <https://business.gov.au/grants-and-programs/research-and-development-tax-incentive/check-if-you-are-eligible-for-the-randd-tax-incentive/conducting-core-activities>
- IE Revenue TDM 29-02-03 §3.1, §3.4, §3.5 — <https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-29/29-02-03.pdf>
- IT MIMIT Linee guida 2024 §1.1.3.3 — <https://www.mimit.gov.it/images/stories/normativa/LineeguidacreditoRS-4luglio2024.pdf>
- INPI Res. 169/2016 item 5.57 — <https://www.wipo.int/wipolex/edocs/lexdocs/laws/pt/br/br170pt.pdf>
- ISO 16290:2013 — <https://www.iso.org/standard/56064.html>
- NASA, Technology Readiness Levels — <https://www.nasa.gov/directorates/somd/space-communications-navigation-program/technology-readiness-levels/>
- Mankins 2009 — <https://doi.org/10.1016/j.actaastro.2009.03.058>
- Jalonen 2011 — <https://doi.org/10.5296/jmr.v4i1.1039>
- Fleming 2001 — <https://doi.org/10.1287/mnsc.47.1.117.10671>
