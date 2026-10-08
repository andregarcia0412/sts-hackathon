# Design — Pipeline de Agentes de Evidências (STS 2026)

Data: 2026-10-08
Status: aprovado em brainstorming (abordagem A — loop de agente próprio sobre o client `ollama`)
Branch alvo: `feature/models-and-modules`

## 1. Contexto e objetivo

O produto final do backend é o **grafo de evidências**: a memória do sistema onde toda
análise de projeto (critérios Frascati / Lei do Bem) acumula evidências ligando
`projeto → critério → regra → evidência → fonte`. Esta iteração implementa o
**pipeline de agentes** que gera essas evidências e as incrementa no grafo, mais um
frontend mínimo de visualização para testar o fluxo ponta a ponta.

Base normativa e de dados (fonte de verdade, já existente em `backend/docs/`):

- `Fluxo do Backend.md` — módulos 1 (extração), 2 (web), 3 (documento), 4 (grafo),
  5 (orquestrador), 8 (catálogo de regras).
- `organizacao-dados-por-criterio.md` — 66 regras ativas (17 web + 49 documentais),
  9 absorvidas (não executam), 15 transversais (T1–T15), 7 checagens compartilhadas
  (`CHK-*`), modos REGRA/LLM/WEB, mapa dado → regra.
- `regras-criterios/*.md` — notas de critério (NOV, CRI, INC, SIS, REP) com o
  conteúdo de cada regra, e transversais com fontes normativas.
- Casos de teste: `backend/data/casos_test/PRJ01…PRJ20` (pacote uniforme de 14
  artefatos por projeto, com gabarito nos históricos).

### Decisões já tomadas (aprovadas)

| Decisão | Escolha |
|---|---|
| Persistência do grafo | Arquivos JSON agora, atrás de interface `GraphStore` — `MongoGraphStore` entra depois sem tocar no resto |
| Cobertura de regras | Catálogo completo: 66 regras ativas executam; absorvidas ficam como marcador; N/A/parciais saem com motivo |
| Teste do fluxo | 1 projeto (PRJ01 — caso "não elegível/rotina", bom teste negativo) |
| Framework de agentes | Nenhum: loop de agente próprio (~100 linhas) sobre o client Python `ollama` + `asyncio` |
| Gate de citação | Quote precisa existir literalmente (substring) no fragmento de origem; senão a evidência é descartada e o agente tenta uma vez mais |
| Reprodutibilidade | temperature 0; manifest com hash por arquivo; versões de catálogo/modelo/prompt registradas por análise |
| Segurança da key | `.env` (gitignored); key rotacionável sem mudar código |

### Fora do escopo desta iteração

- Geração de parecer (módulo 6), chatbot (módulo 7) e cálculo de estado/classe
  (a pontuação por regra aparece como indicador no grafo; a classe não sai da média).
- MongoDB de fato (só a interface).
- Reanálise incremental e lote (a estrutura de versões do grafo já suporta; o
  disparo automático não é implementado).
- Calibração contra o gabarito PRJ01–20 (comparação classe × gabarito).
- Frontend principal da pasta `frontend/` (usamos uma página de teste própria).

## 2. Modelos e configuração

`.env` (gitignored) na raiz do `backend/`:

```
OLLAMA_API_KEY=<key>
OLLAMA_BASE_URL=https://ollama.com
MODEL_EXTRACTOR=gemma4:31b     # interpretação de arquivos → manifest
MODEL_ANALYST=gpt-oss:120b     # especialistas por critério + orchestrator
ANALYZE_CONCURRENCY=5          # especialistas simultâneos (rate limit)
```

Verificado em 08/10/2026 com a key fornecida: `gemma4:31b`, `gpt-oss:120b`,
`gpt-oss:20b` disponíveis em `https://ollama.com`; `POST /api/web_search` e
`POST /api/web_fetch` respondem com a mesma key. O client Python `ollama` expõe
`web_search` e `web_fetch` como tools passáveis ao loop de chat; como a execução
acontece no nosso processo, toda query é interceptável e loggável antes de sair
(requisito T6 — sanitização — e NOV-W8 — log de busca).

## 3. Estrutura de código

```
backend/
├── .env
├── catalog/
│   ├── rules.yaml                # catálogo de regras (dado versionado)
│   └── handbooks/
│       ├── NOV.md  CRI.md  INC.md  SIS.md  REP.md   # item 5: como encontrar cada evidência
└── src/ai_microservice/
    ├── main.py                   # FastAPI + rotas + montagem de /viz
    ├── config.py                 # env → settings (pydantic-settings)
    ├── llm.py                    # client Ollama + AgentLoop (tool-calling) + retry/backoff
    ├── catalog.py                # loader + validação do rules.yaml
    ├── extraction/
    │   ├── parsers.py            # csv/xlsx/pdf/md/json → fragmentos com âncora estável
    │   ├── manifest.py           # hash + manifest por arquivo (imutabilidade do pacote)
    │   └── interpreter.py        # agente gemma4:31b: interpreta cada arquivo → manifest
    ├── tools/
    │   ├── file_search.py        # busca em fragmentos (artefato, seção, substring)
    │   └── web.py                # web_search/web_fetch com sanitização + log de query
    ├── checks/
    │   ├── recalculo.py           # CHK-RECALC
    │   ├── tempo.py               # CHK-TEMPO
    │   ├── versoes.py             # CHK-VERSOES
    │   └── ...                    # pre-pass das demais CHK
    ├── agents/
    │   ├── criterion.py          # agente especialista genérico, parametrizado pelo catálogo
    │   └── orchestrator.py        # paraleliza os 5 especialistas, agrega evidências
    ├── graph/
    │   ├── schema.py             # nós/arestas (pydantic)
    │   ├── builder.py            # upsert idempotente, ID determinístico, versões + diff
    │   └── store.py              # GraphStore (interface) + JSONFileGraphStore
    └── api/
        ├── analyze.py            # POST /analyze, GET /status/{id}
        └── graph.py              # GET /graph/{project_id}
    └── static/viz/index.html     # página de teste (vanilla JS/SVG)
tests/                           # unitários + e2e
```

## 4. Catálogo de regras (item 5)

`catalog/rules.yaml` — uma entrada por regra. Fonte do conteúdo: as notas de
critério em `docs/regras-criterios/` e o mapa de `organizacao-dados-por-criterio.md`.

```yaml
catalog_version: 1.0.0
rules:
  - id: NOV-D1
    criterion: novidade
    block: documento            # documento | web | transversal
    mode: llm                   # regra | llm | web | combinações (regra+llm)
    what: "declara elemento novo"
    evidence: "o §2 do metodo.md descreve o mecanismo/hipótese que o projeto afirma como novo"
    sources: ["Frascati 2015 §2.63", "Guia MCTI 2020 §6"]
    routing: ["metodo.md#2"]     # artefatos/seções que a regra lê
    polarity_hint: positive      # ou negative, ou por caso (ex.: CRI-D6 positiva)
    scoring_role: mean           # mean | informativa | gate
    status: aplicavel           # aplicavel | parcial | na | absorvida
    status_reason: "..."         # obrigatório quando parcial/na
    absorbed_into: null          # ex.: CRI-D9 → CRI-D5
    prompt: |                    # "como essa evidência pode ser encontrada" (regras LLM/WEB)
      ...
  - id: CHK-RECALC
    block: shared
    mode: regra
    ...
transversais: [T1 … T15]          # mesmos campos; design → entram como constraints do sistema
```

Regras cobertas: 66 ativas (executam), 9 absorvidas (marcador, não executam),
T1–T15 (as de `mode: design` viram constraints implementadas no código, não
agentes), 7 `CHK-*` (implementadas como funções determinísticas).

`catalog/handbooks/{NOV,CRI,INC,SIS,REP}.md` — um documento por critério, em
linguagem de instrução ao especialista: para cada regra do critério, o que
verificar, **como encontrar** (artefato + âncora + família de query, quando web),
polaridade e armadilhas do pacote (ex.: "texto sozinho alcança no máximo
indeterminada"; "repetição de número em PDF não é confirmação"). Servem de base
para o system prompt dos especialistas e do orchestrator, e são legíveis por
humano (revisáveis em PR junto com o YAML).

### Validação do catálogo (loader)

- Todo ID presente nas notas de critério está no catálogo; nenhum duplicado ou órfão.
- Toda regra `mode: llm|web` tem `prompt`; toda `mode: regra` aponta função existente.
- Todo artefato do `routing` existe no schema do pacote.

## 5. Pipeline dos agentes

`POST /analyze { project_path }` → `analise_id` imediato, execução em background
(in-process; fila assíncrona simples). `GET /status/{id}` expõe etapa por etapa
(`pendente · rodando · concluída · falhou · não executada`).

### 5.1 Ingestão determinística (código, sem LLM)

- Pacote imutável: manifest por projeto com caminho + hash de cada arquivo.
- Cada arquivo vira **fragmentos** com âncora estável: `metodo.md#2` (seção),
  `medicoes.csv#PRJ01-S01` (ID de linha/ensaio), `dossie_projeto.pdf#p3` (página),
  linha N de CSV. Fragmento guarda: arquivo, âncora, texto literal, natureza
  (registro primário, derivado, síntese, **depoimento** — transcrição).
- Parser CSV/XLSX: célula vazia = `null`, nunca `0` (vazio ≠ zero); XLSX com
  cabeçalho na linha 5. PDF: extração por página. MD: por seção §. JSON: inteiro.
- Identificação de tipo pelo conteúdo (cabeçalho/título), validada contra o
  `inventario_evidencias.csv`; divergência vira flag, não erro.

### 5.2 Agente intérprete (gemma4:31b)

Por arquivo: recebe o conteúdo extraído e produz, em JSON de schema fixo, o que o
arquivo é, do que trata, natureza e seções reconhecidas → enriquece o manifest.
A LLM só rotula, nunca reescreve o conteúdo.

### 5.3 Checagens compartilhadas (determinísticas, antes de qualquer especialista)

Roda uma vez por projeto; resultado exposto aos agentes via tool `chk_resultado(chk_id)`
e injetado no contexto das regras cujo roteamento as referencia.

| CHK | Implementação nesta iteração |
|---|---|
| CHK-TEMPO | Total: linha do tempo (`cronologia.csv` + datas de `medicoes`/`configuracao`), data de referência, ordem hipótese→ensaios, datas progressivas |
| CHK-RECALC | Total: recompute `medicoes` → `resultados` (contagem, diferenca_maior_menor, percentil_95 pelo histograma, indicador_precalculado, valor_observado); saída batendo/não batendo/vazio; soma só no mesmo ensaio |
| CHK-VERSOES | Total: consistência cronologia ↔ medicoes ↔ configuracao.json; parâmetros-chave não nulos; comparadores do §1 |
| CHK-CONFIG | Pre-pass determinística (tipo da referência do §1, flags) + classificação final por LLM no especialista |
| CHK-FALHAS | Pre-pass (linhas de falha/piora por versão) + classificação do tipo (operacional × experimental) por LLM no especialista |
| CHK-ESCOPO | Pre-pass (flags `..._executado: false`) + leitura LLM do §6/§7 no especialista |
| CHK-DIVERG | Extração de números da transcrição por LLM + match determinístico contra `resultados`/`medicoes` (mesma versão, ensaio, denominador) |

### 5.4 Orchestrator (gpt-oss:120b)

- Carrega o catálogo e o manifest, monta o contexto (sumário do projeto), e
  instancia **os 5 especialistas em paralelo** (`asyncio.gather` + semáforo
  `ANALYZE_CONCURRENCY`).
- O papel de LLM do orchestrator é limitado e auditável: distribuir as regras,
  decidir ordem/dependências simples (ex.: CRI-W1 reaproveita achado do NOV-W3
  quando disponível) e agregar. A execução das regras é determinística a partir
  do catálogo — o orchestrator não inventa regra nem pula regra.
- Falha de um especialista não derruba a análise: o critério sai "falhou", as
  regras ficam "não executadas" com motivo, os demais seguem.

### 5.5 Agente especialista por critério (gpt-oss:120b)

- Um agente por critério (NOV, CRI, INC, SIS, REP), instanciado do mesmo código,
  parametrizado com: handbook do critério (system prompt), as regras do catálogo
  do seu critério, manifest + fragmentos roteados, e as tools.
- Tools disponíveis:
  - `buscar_em_arquivos(artefato, secao?, termo)` → fragmentos com âncora;
  - `chk_resultado(chk_id)` → resultado da checagem compartilhada;
  - `web_search(query)` e `web_fetch(url)` — só habilitadas para regras de
    `block: web`; toda query passa pela sanitização (blocklist `PRJxx`, nomes de
    equipe, códigos internos) e é **guardada** como nó de query (original ×
    sanitizada); cada resultado relevante vira nó de fonte (URL, data de
    captura, trecho citado).
- Para cada regra do seu critério o especialista produz de 0..n **evidências**
  em JSON de schema fixo: `{regra_id, fonte (âncora ou URL), quote, polaridade
  (sustenta/contraria/neutra), natureza, justificativa}`.
- **Gate de citação**: o quote deve existir literalmente no fragmento/fonte
  (checagem substring no nosso código). Falhou → descarta e o agente refaz a
  regra uma vez; falhou de novo → evidência rejeitada registrada como gap.
- Depoimento (transcrição) nunca pontua: entra como contexto/divergência
  (`natureza: depoimento`, polaridade não conta).
- Regra sem evidência sai como "sem evidência" com o motivo — nunca zero, nunca
  silêncio. Regras N/A/parciais saem com `status_reason` do catálogo.

### 5.6 Grafo (produto final)

- `graph/schema.py` (pydantic): nós `projeto · criterio · regra · evidencia ·
  fonte · query · gap`; arestas `sustenta · contraria · cita · retornou · compoe`.
- `builder.py`: upsert idempotente com **ID determinístico**
  `hash(regra_id + fonte + quote)`; nova análise → nova versão
  `data/graphs/{project}/v{n}/`, nunca sobrescreve; `meta.json` registra
  catálogo, modelo, prompts, manifest e timestamp (rastreabilidade).
- `store.py`: interface `GraphStore` (`add_nodes`, `add_edges`, `save_version`,
  `get_graph`, `diff_versions`); implementação `JSONFileGraphStore`
  (`nodes.json`, `edges.json` por versão). `MongoGraphStore` fica como stub
  documentado (mesma interface, coleções `nodes`/`edges`).

## 6. API

| Rota | Função |
|---|---|
| `POST /analyze` | `{project_path}` → `{analise_id}`; roda o pipeline em background |
| `GET /status/{analise_id}` | etapas, status, início/fim/duração por etapa |
| `GET /graph/{project_id}` | grafo da versão mais recente (JSON único para o viz) |
| `GET /regras`, `GET /regras/{id}` | lê o catálogo (o front usa ao clicar num nó) |
| `GET /viz` | página de teste estática |

## 7. Frontend de teste

Página única em vanilla JS + SVG (sem build, sem CDN), servida pelo FastAPI:

- Layout em camadas: projeto → 5 critérios → regras → evidências → fontes/queries.
- Cor por polaridade: verde (sustenta), vermelho (contraria), cinza (neutra,
  sem evidência, N/A/não executada).
- Clique no nó → painel lateral com quote, âncora, justificativa, e o texto da
  regra vindo de `GET /regras/{id}`.
- Clique em nó de query → query original × sanitizada.
- Botão "analisar projeto" chama `POST /analyze` e faz polling de status.

## 8. Testes

- **Unitários**
  - Parsers sobre os arquivos reais do PRJ01: âncora estável, célula vazia →
    `null`, cabeçalho XLSX na linha 5, seções do `metodo.md`.
  - Gate de citação: aceita literal, rejeita paráfrase.
  - CHK-RECALC: recompute batendo/não batendo/vazio com valores conhecidos do PRJ01.
  - ID determinístico do builder: mesma entrada → mesmo ID; versão nova não sobrescreve.
  - Loader do catálogo: validações da seção 4.
  - Sanitização de query: blocklist aplicada, log original × sanitizada.
- **E2E**: rodar o pipeline completo no **PRJ01** e visualizar o grafo em `/viz`.
  Critério de sucesso: as 5 camadas povoadas, evidências com citações válidas
  (gate), queries web logadas, regras N/A com motivo, grafo versionado em `v1`.
- **Smoke de LLM**: um teste marcado como "requer OLLAMA_API_KEY" cobre o loop de
  agente com uma tool fake, sem depender da web.

## 9. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Custo/latência de 66 regras × gpt-oss:120b | Paralelismo com semáforo; prompts curtos (só fragmentos roteados); regras REGRA não chamam LLM; informativas em 1 chamada |
| Alucinação de citação | Gate de citação obrigatório + 1 retry + gap registrado |
| Prompt injection via conteúdo web | Conteúdo tratado como dado (tools devolvem texto entre delimitadores; instrução do system prompt) |
| Rate limit do Ollama Cloud | Semáforo + retry com backoff exponencial |
| Web fora do ar | Regras W "não executadas", análise segue (nunca zero) |
| Key exposta | `.env` gitignored + `.env.example`; recomendação de rotação já comunicada |

## 10. Critérios de aceite da iteração

1. `POST /analyze` no PRJ01 conclui com grafo `v1` completo em JSON.
2. Toda evidência no grafo tem citação literal válida no fragmento/fonte.
3. Toda query web está persistida (original + sanitizada) e ligada aos achados.
4. Regras N/A, parciais e absorvidas aparecem no grafo com o motivo, sem execução silenciosa.
5. `/viz` renderiza as 5 camadas com interação de clique funcional.
6. Reexecutar a análise gera `v2` sem duplicar nós (ID determinístico).
7. Testes unitários verdes; e2e do PRJ01 documentado com o resultado no grafo.