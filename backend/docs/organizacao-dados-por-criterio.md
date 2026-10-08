---
title: STS 2026 — Organização dos Dados de Projeto por Critério
created: 2026-10-07
updated: 2026-10-08
tags: [sts-2026, lei-do-bem, frascati, criterios, dados, pipeline]
status: draft
---

# STS 2026 — Organização dos Dados de Projeto por Critério

Como organizar os dados do [[STS 2026 Lei do Bem MOC|pacote de participantes]] para analisar e validar
os critérios de acordo com as regras de [[Regras de Validação dos Critérios de Frascati]]. A anatomia do
pacote é 100% uniforme (mesmos 14 artefatos nos 40 projetos) e já embute rastreabilidade — o gabarito
cita `metodo.md#2` e o `resultados.csv` aponta para `medicoes.csv` — então a organização segue a
granularidade que o pacote estabelece. Calibração pelos 20 históricos em
[[Padrão de Análise dos Históricos]].

> [!info] Cobertura auditada programaticamente (08/10/2026)
> Todos os IDs de regra foram extraídos por regex das notas em `hackathons/sts-2026/criterios/` e
> conferidos contra esta nota: **75 IDs de regra de critério**, dos quais **66 ativos** (17 web + 49
> documentais) e **9 absorvidos** na revisão de redundância (não executados), mais **15 transversais**
> (T1–T15). Cada regra ativa está mapeada abaixo com dado do pacote e modo (REGRA / LLM / WEB), ou
> classificada como **N/A no pacote** ou **parcial**, com o motivo explícito. Sobreposições entre
> critérios viram **checagens compartilhadas** (`CHK-*`), executadas uma vez.

## Parte 1 — Organização dos dados (4 camadas)

**Camada 0 — Ingestão imutável.** O pacote nunca é alterado; a ferramenta gera por projeto um manifest
(caminho + hash de cada artefato) e **âncoras de citação** no mesmo idioma do pacote: `metodo.md#2`,
`medicoes.csv#PRJ21-S01`, linha N do CSV, página M do PDF. Toda evidência no grafo aponta para âncora —
é o que a coluna `fonte_N` do gabarito espera.

**Camada 1 — Normalização em 5 tabelas internas** (é isto que "organiza os dados para analisar"):

| Tabela interna | Vem de | Servir para |
|---|---|---|
| **Linha do tempo** | `cronologia.csv` (evento, data, versão) + datas em `medicoes`/`configuracao` | Âncora temporal: qual registro precede qual (CHK-TEMPO) |
| **Alegações** | `metodo.md` §1–§7 (uma alegação por seção) + `dossie_projeto.pdf` + `atividades.csv` + transcrição | O que a equipe *afirma* (hipótese, barreira, novidade, limite) — sempre com citação verbatim; a transcrição entra marcada como **depoimento** (T9) |
| **Registros numéricos** | `medicoes.csv`, `resultados.csv`, `entradas.csv`, `observacoes.csv`, `configuracao.json` | O que *aconteceu* — recalculável, verificado por regra (CHK-RECALC, CHK-VERSOES) |
| **Divergências** | cruzamento transcrição × registros | Evidência contrária qualificada (o gabarito tem coluna própria para isso — CHK-DIVERG) |
| **Disponibilidade probatória** | `inventario_evidencias.csv` × presença real + conteúdo esperado × conteúdo real | "Localizada ≠ comprovada" (T12) |

> [!warning] Campo que não serve de sinal
> `natureza_informada_pela_equipe` (atividades) tem a mesma distribuição em todos os projetos e não
> distingue classes ([[GUIA_DO_PARTICIPANTE]]). Entra no JSON como autodeclaração, mas **nenhuma regra o
> usa como fonte** (T13).

**Camada 2 — Checagens compartilhadas + execução das regras.** Primeiro rodam as checagens `CHK-*`
(uma vez por projeto); depois cada regra (IDs `NOV/CRI/INC/SIS/REP-Wn/Dn`) lê 1–2 tabelas da camada 1
e/ou o resultado de uma `CHK`, aplica **a sua** polaridade e emite um nó de evidência
`{regra_id, chk_id?, artefato#âncora, quote, polaridade, modo}`.

**Camada 3 — Grafo e veredito:** evidências → critério → **estado** (vocabulário do gabarito, abaixo) →
classe pela [[#Estados e classe|tabela estado → classe]].

**Camada 4 — Parecer no schema do gabarito** (27 colunas), pronto para comparação com `PRJ01–20`.

### Estados e classe

Vocabulário dos estados por critério, tirado do gabarito dos históricos:

| Critério | P&D | Rotina | Insuficiente |
|---|---|---|---|
| Novidade | DEMONSTRADA NO RECORTE | NÃO DEMONSTRADA | INDETERMINADA |
| Criatividade técnica | DEMONSTRADA NO RECORTE | NÃO DEMONSTRADA | INDETERMINADA |
| Incerteza tecnológica | INVESTIGADA | NÃO CARACTERIZADA | ALEGADA, NÃO VERIFICÁVEL |
| Sistematicidade | DOCUMENTADA | DOCUMENTADA COMO ACEITE | PARCIAL |
| Transferência/reprodução | DOCUMENTADA NO ESCOPO · DOCUMENTADA COM LIMITE | DOCUMENTADA PARA A CONFIGURAÇÃO | INSUFICIENTE PARA O NÚCLEO ALEGADO |

Classe pela combinação (determinística nos 20 históricos):

| Classe | Combinação |
|---|---|
| **Elegível** | coluna P&D nos 5, reprodução **no escopo** |
| **Com ressalvas** | coluna P&D nos 5, reprodução **com limite** → exige recorte + limitação + evidência necessária |
| **Não elegível** | coluna Rotina nos 5 |
| **Evidência insuficiente** | coluna Insuficiente nos 5 → exige o elo ausente + evidências a solicitar |

> [!note] Combinação que não aparece nos históricos
> Se os estados saírem misturados entre colunas, a ferramenta **não escolhe sozinha**: mostra a
> combinação ao analista, com as evidências de cada critério, e segue a árvore de decisão de
> [[Padrão de Análise dos Históricos#Árvore de decisão equivalente]] como sugestão (T7).

## Parte 2 — Fluxo de execução (a ordem importa)

1. **Parse + linha do tempo** → extrai datas de todos os artefatos (REGRA)
2. **CHK-RECALC** → o "livro-caixa da verdade": cada linha de `resultados.csv` recalculada de
   `medicoes.csv` (contagem, taxa, mediana, p95 conforme o [[LEIA_ME]]). Divisão: batendo / não batendo /
   vazio ≠ zero; marca **entrega × desempenho** (REGRA)
3. **CHK-TEMPO** → data do primeiro evento da cronologia = data de referência do projeto
   (NOV-W1, T3). Toda busca e toda comparação usa *essas* datas (REGRA)
4. **Extração de alegações** → LLM por seção do `metodo.md` e campos do dossiê, com gate de citação (LLM)
5. **Checagens compartilhadas** → CHK-VERSOES, CHK-FALHAS, CHK-CONFIG, CHK-ESCOPO (REGRA + LLM)
6. **CHK-DIVERG** → números da transcrição contra `resultados`; divergido = evidência contrária
   registrada, com o registro prevalecendo (T10; REGRA + LLM)
7. **Web** só para os blocos com regras `-W`: NOV-W1…W8, CRI-W1…W5, INC-W1…W4 — queries sanitizadas
   (T6), log PRISMA-S (NOV-W8). Na massa, a web é **complementar**: as referências anteriores dos projetos
   são fictícias e não existem na internet
8. **Estados por critério** → vocabulário da tabela acima
9. **Classe** → tabela estado → classe; combinação mista vai para o analista

## Checagens compartilhadas (sobreposições entre critérios)

Cada `CHK` roda **uma vez** e alimenta várias regras; a polaridade é decidida pela regra que lê.

| CHK | O que computa | Dados | Regras que leem |
|---|---|---|---|
| **CHK-TEMPO** | Linha do tempo, data de referência, ordem (hipótese/plano antes dos ensaios), datas progressivas | `cronologia.csv`, datas em `medicoes`/`configuracao`, cabeçalho do dossiê (corte − semanas) | NOV-W1, T3, T5, CRI-D1, SIS-D1, SIS-D2, INC-D8 |
| **CHK-RECALC** | Recálculo `medicoes` → `resultados`; operação, base, unidade; **entrega × desempenho** | `medicoes.csv`, `resultados.csv` | REP-D9, SIS-D14, T11, T9, NOV-D6 |
| **CHK-VERSOES** | Versões da cronologia ↔ `ensaio_id` em `medicoes` ↔ `configuracao.json`; parâmetros-chave **não nulos**; quais versões são os **comparadores** nomeados no §1; critérios fixados antes da rodada (§3) | `cronologia.csv`, `medicoes.csv`, `configuracao.json`, `metodo.md` §1–§4 | CRI-D4, CRI-D8, CRI-D10, INC-D12, SIS-D5, SIS-D12, REP-D6 |
| **CHK-FALHAS** | Versões com falha ou piora e o **tipo**: operacional (parâmetro, permissão, cadastro, receita do fornecedor) × experimental (hipótese não confirmada, critério prévio não atingido) | `resultados.csv` por versão, `observacoes.csv`, `metodo.md` §2/§6 | INC-D4, INC-D9, CRI-D4, SIS-D7, REP-D3, T4 |
| **CHK-CONFIG** | A referência anterior (manual, catálogo, dicionário, produto **contratado**, datado antes) já fornece a função? O mecanismo é configurar/ativar/mapear/ajustar dentro da faixa suportada? | `metodo.md` §1 e §2, `configuracao.json`, `cronologia.csv` | NOV-D4, NOV-D10, CRI-W2, CRI-D5, INC-D9, REP-D8 |
| **CHK-ESCOPO** | Limite da conclusão: o que foi excluído **desde o início** × lacuna **dentro da pretensão** (flags `..._executado: false`, hipótese do protocolo não ensaiada, critério prévio não atingido) | `metodo.md` §6/§7, `revisao_tecnica.md`, `configuracao.json` | NOV-D11, REP-D7 |
| **CHK-DIVERG** | Números e afirmações da entrevista × registros, com versão e denominador | transcrição, `resultados.csv`, `medicoes.csv` | T9, T10, T11 |

Polaridades que a revisão dos históricos fixou:

- **CHK-FALHAS:** falha **experimental** conta a favor de INC-D4, CRI-D4, SIS-D7 e REP-D3. Falha
  **operacional** conta **contra** INC-D9 (rotina) e é neutra para as demais. "v1 falhou → v2 corrigiu",
  sozinho, **não** prova incerteza: os 7 não elegíveis têm esse padrão.
- **CHK-CONFIG:** "sim" conta contra NOV-D4/D10, CRI-W2/D5, INC-D9 e leva REP-D8 a "documentada para a
  configuração".
- **CHK-ESCOPO:** limite excluído desde o início é **neutro** (não gera ressalva); lacuna dentro da pretensão
  leva REP-D7 a "documentada com limite".

## Parte 3 — Qual dado alimenta qual critério

### Critério 1 — Novidade (internet + documentos; 18 regras ativas)

| Regra                                                         | Dado do pacote                                                                                                                          | Modo         |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| NOV-W1 (data de referência)                                   | CHK-TEMPO: cronologia `data` do evento inicial                                                                                          | REGRA        |
| NOV-W2 (três frentes de busca)                                | plano de busca por frente: patentes (INPI BuscaWeb/Espacenet/PATENTSCOPE), literatura (OpenAlex/Crossref/arXiv), mercado (buscador)     | WEB          |
| NOV-W3 (documento mais próximo)                               | achado web mais próximo do elemento declarado + quadro "o que o projeto tem que o achado não tem"                                       | WEB          |
| NOV-W4 (setor, não a empresa)                                 | ausência de uso da solução por outros atores do setor nos achados                                                                       | WEB          |
| NOV-W5 (segredo industrial preserva novidade)                 | achado de concorrente: verificar se o *método* está público, ou só o resultado                                                          | WEB          |
| NOV-W6 (trabalho simultâneo não elimina)                      | datas de publicação dos achados vs. data de referência                                                                                  | WEB          |
| NOV-W7 (página conta se achável e acessível)                  | snapshot com URL + data — define a **admissibilidade** da evidência web no grafo                                                        | WEB          |
| NOV-W8 (busca reproduzível)                                   | log de busca (base, string, filtros, nº de resultados, selecionados e por quê) como nó do grafo                                         | WEB+REGRA    |
| NOV-D1 (declara elemento novo)                                | `metodo.md` **§2 Mecanismo e hipótese**                                                                                                 | LLM+citação  |
| NOV-D2 (estado da arte com o modo de falha de cada alternativa) | `metodo.md` **§1 Referência anterior**: alternativas conhecidas **e onde cada uma falha**; só lista de ferramentas → indeterminada    | LLM+citação  |
| NOV-D3 (novidade de conhecimento/técnica, não funcionalidade) | §1/§2: o elemento novo declarado é o "como", não uma lista de features                                                                  | LLM          |
| NOV-D4 (não é cópia/compra de tecnologia)                     | CHK-CONFIG                                                                                                                              | LLM          |
| NOV-D5 (exclusões de software)                                | §1+§2 contra a lista de exclusões (Frascati §2.70–2.72; IPCTN Anexo I: sistema de negócio, ferramenta pronta, customização, depuração)  | LLM          |
| NOV-D6 (melhoria substancial com baseline)                    | CHK-RECALC: comparações entre versões — **melhora entre versões sozinha não basta** (rotina também melhora: PRJ01 8/12 → 12/12)         | REGRA        |
| NOV-D8 (patente/artigo = indício)                             | **N/A no pacote** — não há patentes, registros ou artigos nos artefatos                                                                 | —            |
| NOV-D10 (referência anterior já fornece a função)             | CHK-CONFIG: §1 é manual/catálogo/produto contratado, datado antes do início (CHK-TEMPO), e o §2 aplica a função dele                   | REGRA (data) + LLM |
| NOV-D11 (novidade vale no recorte)                            | CHK-ESCOPO: `metodo.md` §6 Limite da conclusão — afirmações além do recorte ficam fora                                                  | LLM          |
| NOV-D12 (título/adjetivo não prova; técnica genérica precisa de elemento próprio) | título do dossiê × mecanismo do §2; elemento próprio testado contra o comparador (CHK-VERSOES)                       | LLM          |

Absorvidas: NOV-D7 → T2 · NOV-D9 → NOV-D2.

### Critério 2 — Criatividade (internet + documentos; 14 regras ativas)

| Regra | Dado | Modo |
|---|---|---|
| CRI-W1 (roteiro problema-solução EPO) | achado mais próximo (do NOV-W3) + problema técnico derivado dele + justificativa de não-obviedade | WEB+LLM |
| CRI-W2 (prática padrão/tutorial) | CHK-CONFIG + busca web: a configuração do §2 aparece em doc oficial? (na massa, o manual citado no §1 é fictício e a própria referência já responde) | WEB+LLM |
| CRI-W3 (combinação além da soma dos efeitos) | §2 vs. comparadores isolados — `medicoes` registra as estratégias alternativas medidas | LLM+REGRA |
| CRI-W4 (conhecimento de outro campo) | §1/§2: origem do conhecimento + o que precisou ser adaptado | LLM |
| CRI-W5 (problema em aberto / contra o consenso) | literatura ou relatórios mostrando o problema sem solução | WEB |
| CRI-D1 (hipótese explícita registrada **antes** dos testes) | `metodo.md` §2 **com data** cruzada (CHK-TEMPO: documento-inicial precede ensaios?) | REGRA (datas) + LLM (conteúdo) |
| CRI-D2 (barreira técnica concreta) | `dossie_projeto.pdf` (pergunta) + `atividades.csv` fase "Caracterização" | LLM |
| CRI-D3 (pesquisador) | **parcial**: `atividades.csv` só traz `responsavel_por_funcao` (função, sem titulação) — limitação registrada no parecer | REGRA (parcial) |
| CRI-D4 (alternativas consideradas/abandonadas) | CHK-VERSOES (comparadores rodados) + CHK-FALHAS (versões abandonadas) + `observacoes.csv` | LLM+REGRA |
| CRI-D5 (mudança não rotineira — inclui configurar/ajustar dentro da faixa) | CHK-CONFIG + §2 ("nenhum algoritmo foi modificado") + `configuracao.json` | LLM+REGRA |
| CRI-D6 (método novo para tarefa comum **conta**) | §2 — polaridade **positiva**; evita viés de rejeição | LLM |
| CRI-D7 (quem afirma é profissional competente) | **parcial**: mesma limitação da CRI-D3; `revisao_tecnica.md` dá só a função "revisão técnica" | LLM (limitado) |
| CRI-D8 (regra de decisão com parâmetros concretos) | §2 + §4 + `configuracao.json`: parâmetros-chave **não nulos** (CHK-VERSOES); `null` → indeterminada | REGRA (null) + LLM |
| CRI-D10 (combinação original testada; renomear não conta) | CHK-VERSOES (testada contra os conhecidos do §1) + §2 | LLM+REGRA |

Absorvida: CRI-D9 → CRI-D5.

### Critério 3 — Incerteza (internet + documentos; 15 regras ativas)

| Regra | Dado | Modo |
|---|---|---|
| INC-W1 (solução já disponível/dedutível?) | busca sobre a **barreira** (não o produto) com data | WEB |
| INC-W2 (não saber internamente não conta) | busca sobre a barreira: solução publicada, consultoria ou especialista acessível? | WEB |
| INC-W3 (problema relatado como em aberto) | trechos de artigos/issues descrevendo a limitação | WEB |
| INC-W4 (TRL como indício) | maturidade da técnica nos achados (heurística, não regra) | WEB |
| INC-D1 (incerteza técnica — não comercial nem de política) | §2 + origem das divergências (`revisao_tecnica.md`, `observacoes`); a transcrição só como contexto (T9) | LLM |
| INC-D2 (pergunta técnica específica) | `atividades.csv` coluna `resultado_ou_saida` (padrão "Pergunta: …") + pergunta registrada no dossiê + §2 | REGRA (existe?) + LLM (é técnica?) |
| INC-D3 (por que competente não resolveria) | §1 + §2 | LLM |
| INC-D4 (resultado não previsível) | CHK-FALHAS: **só falha experimental** conta; v1 → v2 corrigido por configuração não conta | REGRA + LLM |
| INC-D5 (enfrentada, não contornada) | `observacoes` + §2 | LLM |
| INC-D6 (integração só se não dedutível combinar) | §2 de projetos de integração (ex.: gateway, sincronização) | LLM |
| INC-D7 (protótipo testa conceito, não homologa) | §3 Protocolo + natureza dos cenários (pouco aplicável: quase não há protótipos físicos) | LLM |
| INC-D8 (delimitar início/fim da P&D) | CHK-TEMPO: cronologia min/max + versões de ensaio | REGRA |
| INC-D9 (bug/ajuste/falha operacional não é incerteza) | CHK-CONFIG + CHK-FALHAS (tipo operacional) — **não** usa `natureza_informada_pela_equipe` | LLM+REGRA |
| INC-D10 (custo/tempo quando decorre da técnica) | §2 + §3 (meta técnica como critério prévio, ex.: PRJ18 latência ≤ 10 %) | LLM |
| INC-D12 (investigada = hipótese executada contra comparadores, com registro) | CHK-VERSOES: hipótese do §2 tem versão com ensaio em `medicoes`, ao lado dos comparadores; só plano/diagrama/memorando → alegada | REGRA + LLM |

Absorvidas: INC-D11 → INC-D9 · INC-D13 → INC-D1.

### Critério 4 — Sistematização (só documentos; 10 regras ativas)

| Regra | Dado | Modo |
|---|---|---|
| SIS-D1 (projeto com objetivo, escopo, início/fim) | `projetos.csv` (duração) + CHK-TEMPO (cronologia min/max) | REGRA |
| SIS-D2 (plano datado **antes**) | CHK-TEMPO: evento "Registro do problema e das referências" **anterior** aos ensaios | REGRA |
| SIS-D3 (recursos próprios: equipe adequada, orçamento) | **parcial**: orçamento/dispêndios fora do escopo do guia; equipe só por função (`responsavel_por_funcao`), sem titulação | REGRA (parcial) |
| SIS-D4 (dispêndios rastreáveis) | **N/A** — o guia do desafio exclui explicitamente horas/despesas/requisitos fiscais | — |
| SIS-D5 (metodologia experimental, **nem gestão nem aceite**) | CHK-VERSOES: §3 Protocolo — comparadores nas mesmas entradas, referência fixada antes, critérios prévios × roteiros com resultado esperado repetidos até passar. **Não** usa `natureza_informada_pela_equipe` | LLM+REGRA |
| SIS-D7 (desvios registrados) | CHK-FALHAS + `observacoes` (v1→v2) + §6 Limite | LLM |
| SIS-D10 (documentação guardada no prazo prescricional) | **N/A como input do pacote**; satisfeita no **output**: dossiê versionado com autor/data (efeito do design da ferramenta) | design |
| SIS-D12 (execução registrada por versão) | CHK-VERSOES: cada versão alegada tem `ensaio_id` em `medicoes`; parâmetros `null` / só entrega → parcial | REGRA |
| SIS-D13 (controles de desenho experimental) | §3 + `configuracao.json`: estratos, repetições, ordem contrabalançada, atraso de rótulo (indício, não obrigatório) | LLM |
| SIS-D14 (entrega ≠ desempenho) | CHK-RECALC: coluna `natureza` e `taxa_percentual` vazia | REGRA |

Absorvidas: SIS-D6 → T5 · SIS-D8 → T2 · SIS-D9 → CRI-D3 + SIS-D3 · SIS-D11 → SIS-D5.

### Critério 5 — Reprodutibilidade (só documentos; 9 regras ativas)

| Regra | Dado | Modo |
|---|---|---|
| REP-D1 (conhecimento codificado) | `metodo.md` **§4 Parâmetros, versões e execução** + `configuracao.json` presente e completo | REGRA (existe?) + LLM (basta para repetir?) |
| REP-D2 (detalhe: método+dados+config+resultados) | §4 + §5 Leitura e reconstrução + base de cálculo recalculável (CHK-RECALC) | LLM+REGRA |
| REP-D3 (resultados **negativos** documentados) | CHK-FALHAS: linhas de falha **experimental** no `medicoes`/`resultados` (ex.: PRJ05 banco-v1 2/8; PRJ18 96% < meta de 100%) | REGRA |
| REP-D4 (artefatos preservados/versionados) | **parcial**: o pacote não tem código executável; o artefato é especificação + `configuracao.json` + registros por versão (consistência cronologia ↔ medicoes ↔ configuracao) | REGRA (parcial) |
| REP-D5 (mecanismo de transferência) | **N/A no pacote** — não há patentes, registros ou publicações; a "Continuidade" (§7) existe nos 20 históricos e não é transferência | — |
| REP-D6 (cadeia plano→resultado rastreável) | CHK-VERSOES: grafo de referências nativo (cronologia.fonte → `metodo.md#1`, resultados.fonte → `medicoes.csv#S01`) — **a regra verifica se a cadeia fecha** | REGRA |
| REP-D7 (limite de escopo: excluído × lacuna na pretensão) | CHK-ESCOPO | LLM+REGRA (flags) |
| REP-D8 (documentação de configuração não é conhecimento novo) | CHK-CONFIG | LLM |
| REP-D9 (números recalculáveis do registro primário) | CHK-RECALC | REGRA |

### Regras transversais (T1–T15)

| ID | Regra | Como fica na ferramenta | Modo |
|---|---|---|---|
| T1 | Cumulativos, verificados **por projeto** | unidade = pasta do projeto; classe pela tabela estado → classe (não por "mínimo") | REGRA |
| T2 | Plurianual: cada ano-base separado (absorve NOV-D7, SIS-D8) | **N/A no pacote** (janela única por projeto) — flag se a cronologia atravessar mais de um ano-base | REGRA (flag) |
| T3 | Comparação sempre na data de início | CHK-TEMPO (passo 3 do fluxo) | REGRA |
| T4 | Resultado negativo não desqualifica | CHK-FALHAS: falha **experimental** com polaridade positiva; meta não atingida não rebaixa a classe sozinha (PRJ18) | REGRA |
| T5 | Contemporâneo > reconstruído (absorve SIS-D6) | CHK-TEMPO: datas progressivas; documento reconstruído no fim → flag | REGRA |
| T6 | Query web sem dado sigiloso | sanitização no módulo web (passo 7): termos abstraídos, nunca verbatim do dossiê — **pendente**: confirmar com a organização se a busca web é permitida na massa | design |
| T7 | Ferramenta sinaliza, analista decide | o LLM nunca atribui estado final: nó de evidência sempre com citação; estado forte exige join numérico; combinação mista vai ao analista | design |
| T8 | Software só é P&D com avanço + incerteza sistemática | gate de domínio: todos os 40 projetos são software — NOV-D5 (exclusões) + INC-D9 (rotina) implementam | LLM |
| T9 | Hierarquia de prova; entrevista nunca sustenta sozinha | nós vindos da transcrição levam `natureza = depoimento` e não fecham critério sozinhos | REGRA |
| T10 | Divergência entrevista × registro registrada | CHK-DIVERG → campo `divergencia_depoimento` do parecer, no formato do guia | REGRA+LLM |
| T11 | Versão, escopo, unidade, denominador; operação e base explícitas | CHK-RECALC + CHK-DIVERG antes de qualquer comparação numérica | REGRA |
| T12 | "Localizada" = presente, não provado | tabela de disponibilidade probatória (camada 1) | REGRA |
| T13 | Aceite perfeito pode ser rotina; IA/complexidade/testes/natureza declarada não decidem | nenhuma regra usa `natureza_informada_pela_equipe`, nº de testes ou taxa de aprovação como sinal de P&D | design |
| T14 | Evidências favoráveis, contrárias, ausentes e contraditórias | cada nó do grafo tem polaridade; regra sem evidência sai como "ausente", nunca some | design |
| T15 | Históricos = calibração, não gabarito por semelhança | PRJ01–20 servem para testar a ferramenta contra o gabarito, não como vizinhos para copiar a classe | design |

## Síntese da cobertura (auditada)

- **66 regras de critério ativas**: 58 mapeadas com dado do pacote + modo; **4 N/A** (NOV-D8, SIS-D4,
  SIS-D10, REP-D5) com motivo; **4 parciais** (CRI-D3, CRI-D7, SIS-D3, REP-D4) com a limitação de dado
  explícita. As 17 regras web estão mapeadas, mas na massa são só complementares.
- **9 absorvidas** (NOV-D7, NOV-D9, CRI-D9, INC-D11, INC-D13, SIS-D6, SIS-D8, SIS-D9, SIS-D11): ficam
  como marcador nas notas de critério e **não são executadas**.
- **15 transversais**: 14 mapeadas; T2 N/A (janela única).
- **7 checagens compartilhadas** cobrem as sobreposições entre critérios.
- As N/A e parciais **entram no parecer como campo com motivo** — não como silêncio (regra "vazio ≠ zero"
  aplicada à própria cobertura).

## Por que essa organização "trava" as regras do guia

"Travar" = as regras do guia deixam de ser conselhos que o analista precisa lembrar e passam a ser
consequência mecânica do formato dos dados. O guia (e o GUIA_DO_PARTICIPANTE) lista erros clássicos
para *evitar*; a organização transforma cada aviso num **check automático** — a ferramenta ou satisfaz
a regra por construção, ou dispara um flag. Violação silenciosa fica impossível.

| Regra do guia (aviso) | Sem essa organização (o erro) | Com a organização (a "trava") |
|---|---|---|
| **"Localizada" ≠ comprovada** | Evidência presente na pasta conta como prova do que se alega sobre ela | Tabela de disponibilidade compara *conteúdo esperado × conteúdo real*; a alegação só entra no grafo se a evidência passa nessa checagem — arquivo vazio/divergente gera flag "localizada mas não comprova" |
| **intenção ≠ execução registrada** | LLM lê uma hipótese bonita no `metodo.md` e concede crédito por ela | Estados fortes (DEMONSTRADA/INVESTIGADA) exigem *join* com registros numéricos por versão (CHK-VERSOES); o texto do §2 sozinho alcança no máximo INDETERMINADA/ALEGADA — o join é obrigatório, não opcional |
| **vazio ≠ zero** | Parse ingênuo converte célula vazia em 0; o recompute então "reprova" 8 vs 0 e o motor conclui divergência falsa | Parser trata vazio como ausente (null), exclui do cálculo e marca a linha — a célula vazada nunca vira 0 nem vira ponto |
| **repetição de números em PDF não é confirmação independente** | Dossiê e entrevista dizem o mesmo número → "verificado" | O único validador aceito é **recompute da base de cálculo** (CHK-RECALC); concordância entre PDFs soma zero na verificação — o `resultados.csv` carrega `base_de_calculo` + `fonte` justamente para viabilizar só esse tipo de confirmação |
| **resultado negativo não desqualifica (T4)** | Falha registrada (v1 falhou) tratada como red flag genérica — ou, no erro oposto, qualquer "v1 falhou → v2 corrigiu" tratado como incerteza | CHK-FALHAS classifica o **tipo** da falha: experimental conta a favor (INC-D4, REP-D3); operacional, resolvida por configuração, conta a favor de rotina (INC-D9) — polaridade definida pela regra, não pelo sentimento do leitor |
| **aceite perfeito pode ser rotina (T13)** | 100% de aprovação nos roteiros lido como sucesso de P&D | SIS-D5 separa experimento de aceite; taxa de aprovação e nº de testes não entram como sinal; CHK-CONFIG pergunta se a referência anterior já fazia a função |
| **divergência entrevista × registro (T10)** | O número lembrado na entrevista entra no parecer, ou a divergência some | CHK-DIVERG registra as duas versões com ID e o registro primário prevalece |

No guia essas regras são **texto normativo** — dependem de o avaliador ter lido e lembrado. Na
organização proposta viram **restrições estruturais** — o tipo de dado que cada regra aceita é fixado
no schema (registros recalculáveis em vez de PDFs repetidos; null explícito em vez de zero; alegação
com anexo numérico para estado forte), então o erro clássico do guia ou não cabe nos dados ou é
detectado na hora.

A ordem de execução importa: o recompute **vem antes** da extração de evidência, porque os números
recalculados são o substrato contra o qual toda alegação vai ser testada — inverter a ordem reabriria
a porta para o erro "intenção ≠ execução".

Relacionadas: [[Regras de Validação dos Critérios de Frascati]] · [[rubrica-subcriterios-frascati]] ·
[[lei-do-bem-criterios-e-evidencias]] · [[lei-do-bem-solucao-hackathon]] ·
[[Reprodutibilidade — Regras de Validação]] · [[Padrão de Análise dos Históricos]]
