---
title: Novidade — Regras de Validação
created: 2026-10-07
tags: [sts-2026, lei-do-bem, frascati, criterios, novidade]
status: draft
---

# Novidade — Regras de Validação

Critério 1 de [[Regras de Validação dos Critérios de Frascati]]. Evidência vem da **busca na internet** e
dos **documentos do projeto**. Pergunta do guia do desafio: *"Era novo?"*

## O que o critério exige

> [!quote] Frascati 2015 §2.14–2.16, p. 46 (paráfrase)
> Na empresa, a novidade é medida contra o **estoque de conhecimento do setor**: o resultado tem de ser
> novo para a empresa **e** não estar em uso no setor. Copiar, imitar ou fazer engenharia reversa não
> conta. O que se mede é o **conhecimento novo**, não o produto novo.

- **Brasil:** campo 3.1.7 do [[FORMP&D — O Formulário Anual|FORMP&D]], "elemento tecnologicamente novo
  ou inovador". O Guia MCTI 2020 §6.2 (pp. 19–20) pede tecnologias **não bem conhecidas e de amplo
  domínio** e a descrição das soluções que já existiam e de suas limitações.
- **Frascati Tab. 2.1(a), p. 48:** adaptação ou customização que não tenta expandir o estado da arte fica
  de fora.

## Bloco A — Busca na internet

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| NOV-W1 | Fixar a **data de referência** = início do projeto; só é estado da arte o que estava acessível ao público antes dela | data de início (FORMP&D 3.1.11) + data de publicação de cada resultado | LPI art. 11 §1º; INPI Res. 169/2016 itens 3.1 e 3.3; HMRC GfC3 parte 2, passo 5; IE TDM §8.1(e) |
| NOV-W2 | Buscar em **três frentes**: patentes, literatura científica e soluções de mercado/concorrentes | lista de bases consultadas por frente | IT MIMIT 2024 §1.1.3.1 (estudos de mercado, tecnologias análogas, concorrentes, patentes, publicações, bancos de dados); AU R&DTI (literatura, internet, patentes, especialistas) |
| NOV-W3 | Comparar o **elemento novo declarado** (o conhecimento/técnica, não o produto) com o documento mais próximo; se **um único** documento já descreve o elemento inteiro, não há novidade | documento mais próximo + quadro "o que o projeto tem que o documento não tem" | Frascati §2.16; INPI itens 4.6 e 4.10 (analogia: novidade contra um documento por vez); EPO G-VII 5, etapa (i) |
| NOV-W4 | Comparar com o **setor/campo**, não com a empresa: algo que já existe no mercado mas é novo para o BNB **não** é novo | ausência de uso da solução por outros atores do setor | Frascati §2.15; UK DSIT ¶6, ¶20, ¶22; IE TDM §3.4; IT MIMIT §1.1.3.1; FAQ MCTI P4(a) |
| NOV-W5 | Se outra empresa já chegou ao resultado mas o **como** não é público (segredo industrial), a novidade se mantém | ausência de documentação pública sobre o método | UK DSIT ¶11, ¶21; IE TDM §3.4; IT MIMIT §1.1.3.1 (cita DM 26/05/2020 art. 2 c. 3) |
| NOV-W6 | Trabalho **simultâneo e independente** de concorrentes não elimina a novidade, se os resultados deles não estavam acessíveis | datas das publicações dos concorrentes vs. início do projeto | UK DSIT ¶21; IE TDM §3.4; IT MIMIT §1.1.3.1 |
| NOV-W7 | Página da internet conta como estado da técnica se pode ser achada por buscador público e continuou acessível | URL + data de publicação ou de captura | INPI Res. 169/2016 item 3.33 |
| NOV-W8 | Registrar a busca de forma **reproduzível**: bases, data, string exata, filtros, nº de resultados, selecionados e por quê | log de busca (vira nó do grafo de evidências) | PRISMA-S (Rethlefsen et al. 2021); WIPO Pub. 946 (palavras-chave + classificação IPC/CPC) |

> [!tip] Indicadores quantitativos (apoio, não regra)
> A literatura mede novidade por combinações inéditas de classes tecnológicas em patentes (Verhoeven,
> Bakker & Veugelers 2016), termos novos no texto de patentes (Arts, Hou & Gomez 2021), combinações
> atípicas de referências (Uzzi et al. 2013) ou distância semântica entre referências (Shibayama, Yin &
> Matsumoto 2021). Cuidado: indicadores bibliométricos tendem a penalizar trabalhos novos no curto
> prazo (Wang, Veugelers & Stephan 2017).

> [!info] Bases sugeridas por fonte oficial
> As Linee guida italianas (nota 5 do §1.1.3.1) citam Scopus, Google Scholar, Turnitin, Espacenet,
> IPERICO e brevettidb. Equivalentes abertos e brasileiros: ver [[Regras de Validação — Referências#Bases e APIs de busca]].

## Bloco B — Documentos do projeto

| ID     | Regra (o que verificar)                                                                                                                                                                                                                                | Evidência que sustenta                                  | Fontes                                                                                                               |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| NOV-D1 | O projeto declara **explicitamente** o elemento novo: a tecnologia, as novas funcionalidades/características e a aplicação                                                                                                                             | texto do campo 3.1.7 ou do relatório técnico            | FORMP&D 3.1.7; Guia MCTI 2020 §6.2; FAQ MCTI P4(a) e (c)                                                             |
| NOV-D2 | O projeto descreve o **estado da arte no início**: as alternativas conhecidas, como era feito e o **modo de falha específico de cada uma** no problema estudado; a novidade é a diferença do mecanismo frente a esse limite. Se só lista ferramentas ou catálogos, sem dizer onde falham, a novidade fica indeterminada | seção de estado da arte / `metodo.md#1` com alternativa + limitação, datada | Guia MCTI 2020 §6.2 (último parágrafo); IT MIMIT §1.1.3.1; IE TDM §8.1(e); Históricos PRJ02, 03, 05, 06, 13–16, 18 (demonstrada) × PRJ08 (indeterminada) |
| NOV-D3 | A novidade é de **conhecimento/técnica** (o "como"), não de funcionalidade, negócio ou mercado                                                                                                                                                         | trechos que explicam o problema técnico e a abordagem   | FAQ MCTI P4; Frascati §2.16 e Tab. 2.1(a); Guia MCTI 2020 §6.1                                                       |
| NOV-D4 | Não é cópia, imitação, engenharia reversa, compra de tecnologia nem nacionalização/adaptação sem barreira técnica                                                                                                                                      | origem da solução; contratos de licença ou aquisição    | Frascati §2.15; UK DSIT ¶12, ¶22, ¶24; Guia ANPEI 2017 pp. 19 e 26; Guia MCTI 2020 Ap. B.3                           |
| NOV-D5 | Software: não cai nas exclusões (sistema de negócio com métodos conhecidos, funcionalidade de usuário, site com ferramentas prontas, criptografia padrão, customização, depuração rotineira). Usar software numa aplicação nova, sozinho, não é avanço | técnica/arquitetura descrita vs. lista de exclusões     | Frascati §2.70–2.72 (pp. 65–66); IPCTN 2020 Anexo I                                                                  |
| NOV-D6 | A melhoria é **substancial e objetiva**: há comparação qualitativa ou quantitativa com a linha de base; mudar só layout/design não conta                                                                                                               | métricas antes/depois, benchmark                        | Decreto 5.798 art. 2º II "c" ("evidente aperfeiçoamento"); Guia MCTI 2020 Ap. B.1; UK DSIT ¶23–25; IT MIMIT §1.1.3.1 |
| NOV-D7 | *Absorvida → T2 (08/10/2026)* | — | — |
| NOV-D8 | Patente, registro de software, artigo ou aprovação por agência de fomento são **indícios** — não obrigatórios                                                                                                                                          | nº do pedido/registro, DOI, termo de outorga            | IT MIMIT §1.1.3.1; Frascati Tab. 2.1(d); Guia ANPEI 2017 Fig. 1                                                      |

## Regras derivadas dos históricos

Extraídas dos 20 projetos classificados do pacote — ver [[Padrão de Análise dos Históricos]]. Na massa,
a prova de novidade sempre veio de `metodo.md#1` (Referência anterior).

| ID | Regra (o que verificar) | Evidência que sustenta | Fontes |
|---|---|---|---|
| NOV-D9 | *Absorvida → NOV-D2 (08/10/2026)* | — | — |
| NOV-D10 | Se a referência anterior — manual, catálogo, dicionário ou produto **contratado**, datado antes do projeto — **já fornece a função aplicada**, a novidade não está demonstrada | referência anterior + data (cronologia) + mecanismo de `metodo.md#2` | Históricos PRJ01 (BARR-2), 04 (VIS-3), 09 (GATE-4), 11 (DIC-11), 12 (COF-2), 19 (OCR-5), 20 (SIM-4); Frascati §2.72 |
| NOV-D11 | A novidade vale **no recorte ensaiado** (perfis, cenários, cargas); afirmações gerais além dele não são cobertas — o estado é "demonstrada no recorte" | seção "Limite da conclusão" (`metodo.md#6`) | Históricos PRJ02, 05, 07, 14; LEIA_ME ("P&D no escopo explicitamente definido") |
| NOV-D12 | Título ou adjetivo comercial ("adaptativo", "inteligente") **não** prova novidade — decide o mecanismo documentado (ver também T13). Adotar técnica genérica (grafo, OCR, modo sombra) só conta se houver elemento técnico próprio testado contra o comparador | mecanismo de `metodo.md#2` vs. título do dossiê | Históricos PRJ09 ("adaptativo" = rota por versão), PRJ19 (OCR), PRJ02 (grafo + restrição e abstenção) |

### Revisão das regras A e B para a massa do hackathon

- **Busca na internet (NOV-W1…W8):** continua válida para projetos reais, mas na massa as referências
  anteriores são **fictícias** (BARR-2, VIS-3…) e não existem na web. A busca é **complementar**: pode
  levantar alerta, mas não substitui a comparação com a referência anterior do próprio projeto, e achar
  a técnica *genérica* na web não derruba a novidade se o mecanismo específico do recorte não estiver
  descrito (NOV-W3 já exige isso).
- **NOV-D6 (métricas antes/depois):** precisa de ressalva — rotina também melhora entre versões (PRJ01 foi
  de 8/12 para 12/12 só mudando a retenção). Melhora numérica sozinha não demonstra novidade.
- **Fora do escopo da massa:** NOV-D8 (não há patentes ou artigos); plurianual agora é a T2.
- **Fusões de 08/10:** NOV-D7 → T2, NOV-D9 → NOV-D2; NOV-D12 perdeu a metade que repetia a T13.

## Sinais de alerta

- Novo "para o banco", sem prova de que é novo no setor — FAQ MCTI P4(a)
- Desafio descrito em termos de mercado ou cliente — FAQ MCTI P4(b)
- Lista de funcionalidades em vez de explicar como foi feito — FAQ MCTI P4
- Compra de máquinas/software, réplica de produto existente — Guia ANPEI 2017 Fig. 1 ("não beneficiável")
- Mesmo texto do ano anterior — FAQ MCTI P4; Guia MCTI 2020 Ap. B.4

## Ponto em aberto

> [!warning] Divergência: novidade para quem?
> - **Setor:** Frascati §2.15; FAQ MCTI P4(a) ("ainda que constituam uma novidade para a empresa" é
>   listado como inconsistência); UK DSIT ¶6; IE TDM §3.4; IT MIMIT §1.1.3.1.
> - **Empresa também vale:** Guia ANPEI/MCTIC 2017, pp. 18 e 24 — mas o texto está numa seção sobre
>   *inovação* (definições da PINTEC e do Manual de Oslo), não sobre P&D.
> - **Mais permissivo ainda:** EUA, 26 CFR §1.41-4(a)(3)(ii) — não exige superar o conhecimento comum
>   dos profissionais da área. Não usar como referência.
>
> **Sugestão:** adotar "setor" (mais conservador e alinhado ao FAQ do MCTI) e levar a pergunta à banca.
>
> **Atualização (08/10):** o [[GUIA_DO_PARTICIPANTE|Guia do Participante]] manda "diferenciar novidade para
> a instituição de progresso tecnológico" e diz que "inovação para a empresa" não basta, por si só — o
> desafio segue a linha do setor/progresso técnico.

Relacionadas: [[Criatividade — Regras de Validação]] · [[Prova de Não Rotina]] ·
[[Atividades Elegíveis vs Não Elegíveis]]

## Fontes desta nota

Detalhes, links e forma de leitura em [[Regras de Validação — Referências]].

- Frascati 2015 §2.14–2.16, Tab. 2.1, §2.70–2.72 — [[Frascati Manual 2015 - OECD.pdf]]
- Decreto 5.798/2006 art. 2º — [[Decreto 5.798-2006 - Planalto.pdf]]
- Guia Prático MCTI 2020 §6.1–6.2, Ap. B.1, B.3, B.4 — [[Guia Pratico da Lei do Bem 2020 - MCTI.pdf]]
- FAQ MCTI P4 — [[Lei do Bem FAQ - MCTI.pdf]]
- Guia ANPEI/MCTIC 2017 pp. 18, 19, 24, 26 — [[Guia da Lei do Bem 2017 - ANPEI-MCTI.pdf]]
- LPI 9.279/1996 art. 11 — <https://www.planalto.gov.br/ccivil_03/leis/l9279.htm>
- INPI Res. 169/2016 (Diretrizes Bloco II) — <https://www.wipo.int/wipolex/en/legislation/details/16927>
- EPO Guidelines 2025 G-VII 5 — <https://www.epo.org/en/legal/guidelines-epc/2025/g_vii_5.html>
- WIPO Pub. 946 (2015) — <https://tind.wipo.int/record/28858>
- UK DSIT Guidelines — <https://assets.publishing.service.gov.uk/media/5a7952ce40f0b676f4a7d80c/rd-tax-purposes.pdf>
- HMRC GfC3 parte 2 — <https://www.gov.uk/government/publications/help-to-see-if-your-work-qualifies-as-research-and-development-for-tax-purposes-gfc3/expectations-of-claimants-part-2>
- AU R&DTI — <https://business.gov.au/grants-and-programs/research-and-development-tax-incentive/check-if-you-are-eligible-for-the-randd-tax-incentive/conducting-core-activities>
- 26 CFR §1.41-4 — <https://www.law.cornell.edu/cfr/text/26/1.41-4>
- IE Revenue TDM 29-02-03 — <https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-29/29-02-03.pdf>
- IT MIMIT Linee guida 2024 — <https://www.mimit.gov.it/images/stories/normativa/LineeguidacreditoRS-4luglio2024.pdf>
- IPCTN 2020 Anexo I — <https://www.fct.pt/wp-content/uploads/2022/09/ipctn20i_Pag_16-20.pdf>
- Rethlefsen et al. 2021 (PRISMA-S) — <https://doi.org/10.1186/s13643-020-01542-z>
- Verhoeven et al. 2016 — <https://doi.org/10.1016/j.respol.2015.11.010>
- Arts et al. 2021 — <https://doi.org/10.1016/j.respol.2020.104144>
- Uzzi et al. 2013 — <https://doi.org/10.1126/science.1240474>
- Shibayama et al. 2021 — <https://doi.org/10.1371/journal.pone.0254034>
- Wang et al. 2017 — <https://doi.org/10.1016/j.respol.2017.06.006>
