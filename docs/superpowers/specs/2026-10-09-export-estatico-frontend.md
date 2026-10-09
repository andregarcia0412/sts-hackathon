# Spec 13 — Export estático para o frontend: `backend-export-frontend`

Data: 2026-10-09
Status: planejada (test-first; implementação após aprovação)
Branch: `feature/front-static-data` (derivada de `feature/backend-merge` @ 2c3a1f2)
Skill-gates: brainstorm (decisões antes de arquivos) · claude-superpowers (plan → isolate → test-first → double review)

## 1. Contexto

O front hifi (`origin/feature/frontend-hifi`) é um app Vite 8 + React 19 que hoje carrega
tudo de mocks em `src/services/api.ts` (banco no localStorage, ~400 projetos gerados).
A API real já existe no backend desta branch e está **alinhada por design** com o front:
`frontend_api/` (projection + schemas camelCase) foi escrito contra o
`frontend/src/domain/types.ts` ("o frontend é a fonte de verdade do contrato" — AGENTS.md).

Duas formas de consumir:

1. **Modo API** (spec 14): front chama o backend com JWT.
2. **Modo estático** (esta spec): subir **só o front** sobre JSONs extraídos do banco —
   medida de contingência para demonstrações sem backend (juiz/notebook/pitch).

O que já existe e é **reutilizado, não duplicado**:
- `delivery/export.py::frontend_payloads()` grava `PRJxx/api.json` (rotas por projeto) e
  `frontend/api_mock.json` — mas só dentro do fluxo de **entrega de benchmark**
  (`backend-entrega export`), que exige benchmark fechado, parecer e pasta fora de repo git.
- A projeção hifi (`project_analysis`), `summarize`, `ProjectQuery`/`apply_project_query`
  e o catálogo (`get_catalog`) — todos com testes em `tests/unit/`.

O gap: não há comando que extraia **direto do Mongo** o conjunto consumível pelo front
(sem rodar pipeline, sem benchmark, sem exigir decisão do analista) e o valide contra o
contrato do `types.ts`.

## 2. Objetivo

Um CLI novo, `backend-export-frontend`, que lê o banco e escreve uma pasta
`frontend-static/` que o front consegue consumir como fonte de dados completa
(para leitura), sem backend no ar.

## 3. Brainstorm — decisões

| # | Questão | Decisão | Por quê |
|---|---|---|---|
| D1 | De onde vêm os dados | **Direto do Mongo** (beans Beanie: Project, Analysis, GraphNode/Edge, Decision, Contestation, User), NÃO re-executando o pipeline | O usuário pediu "extrai direto do banco"; zero tokens, determinístico, rápido (segundos) |
| D2 | Shape da saída | **Por rota**, mesmos payloads das rotas reais: `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/analyses`, `GET /projects/{id}/decisions`, `GET /analyses/{id}/graph`, `GET /analyses/{id}/status`, `GET /analyses/{id}/report.json` — dict `"GET <rota>": payload` (idêntico ao `api_mock.json` do delivery) | Front consome sem adapter novo; mesmo formato já testado; paridade delivery↔extractor é critério de aceite |
| D3 | Quem projeta os dados | **Reusar `project_analysis`, `summarize`, `GraphRead`** (funções que as rotas usam) — o CLI não projeta nada próprio | Garante que o JSON estático = resposta da API; um só lugar de verdade para o contrato |
| D4 | Login no modo estático | `users.json` com os usuários **seed** (`user{n}@sts.com`, `Analista {n}`) para o login mock do front (qualquer senha aceita — regra do mock hifi) | Decisão do usuário: modo estático mantém login mock do front; nenhuma credencial real sai do banco |
| D4b | `GET /users/me` no modo estático | Fica **fora**: o front mantém a sessão em localStorage; o modo estático não valida token | Idem D4 — sem backend não há `CurrentUser` |
| D5 | Escrita (decisões/contestações/revisões) | **Fora do escopo do estático**: JSONs só de leitura; o front em modo estático mantém o comportamento mock atual para escrita (não persiste) | Decisão do usuário: "só o extrator + estáticos consumíveis" |
| D6 | Benchmark/projetos ocultos | Reproduz a regra das rotas: `Project.benchmark_id == None` (projetos de benchmark NÃO aparecem) | Paridade com `GET /projects` real |
| D7 | Projetos sem análise | Saem na lista com `status` real (processing/ready/decided/error) e `scoreSummary: null`; `analyses` = `null` (o front já trata: "null while processing") | `getAnalyses` retorna `Analysis[] | null` no contrato hifi |
| D8 | Report JSON | `GET /analyses/{id}/report.json` sai do campo persistido `Analysis.report` (estágio "parecer"); se `None` (estágio falhou), a rota sai **ausente** do JSON, não vazia | Vazio ≠ zero (AGENTS.md nº4); o front não deve ver um parecer fantasma |
| D9 | Onde o front acha os JSONs | `VITE_STATIC_API_DIR` (default `./static-api`): `import.meta.glob` dos JSONs da pasta → `staticProvider.ts`. Sem dependência nova, sem fetch | Vite serve a pasta em dev; build continua funcionando (JSONs entram no bundle) |
| D9b | `GET /projects` com filtros no estático | O `staticProvider` aplica **em memória** o `ProjectQuery` real (o front já envia o mesmo `ProjectQuery`; o backend tem `apply_project_query` — no estático, o front filtra localmente) | Sem backend não há query string; o front hifi já tem `applyProjectQuery` mockado em `src/mocks/projectQuery.ts` — reuso |
| D10 | Validação da saída | Validação **no extrator** (fail fast): para cada projeto com análise concluída, o JSON de `analyses` deve parsear como `frontend_api.schemas.Analysis` e o de `graph` como `GraphRead`; senão `ExportError` com o caminho do arquivo | O dado estático é o contrato; erro de projeção não pode vazar silencioso para o demo |
| D10b | Manifest | `manifest.json` com `gerado_em`, contagens, versão do catálogo, modelos, sha256 dos arquivos (mesma ideia do delivery) | Reprodutibilidade (princípio 11) |
| D11 | Como rodar | `uv run backend-export-frontend --out <pasta>` (default `<repo>/frontend-static`, permitida; dentro do repo, a pasta entra no `.gitignore`) | Mesmo padrão dos outros CLIs; `.env` já tem MONGODB_URI |
| D12 | Projetos com donos distintos | Exporta TODOS os projetos não-benchmark de TODOS os donos (sem `owner_id` no filtro) e inclui `users.json` com os seeds — o login mock escolhe o analista | Demo multiusuário; sem vazar hashes (só id/name/email) |

## 4. Arquivos

Backend (branch `feature/front-static-data`):

| Arquivo | Mudança |
|---|---|
| `backend/src/backend/frontend_api/exporter.py` | NOVO — leitura do Mongo + montagem dos payloads por rota (reusa `project_analysis`, `summarize`, `GraphRead`, `apply_project_query`) + validação pydantic |
| `backend/src/backend/frontend_api/cli.py` | NOVO — argparse (`--out`, `--owner`, `--project`, `--format`), `init_db`, saída em JSON/CSV resumo |
| `backend/pyproject.toml` | PATCH — `[project.scripts] backend-export-frontend = "backend.frontend_api.cli:main"` |
| `backend/.env.example` | PATCH — nada novo a declarar (usa MONGODB_URI existente); documentar o destino default no docstring do CLI |
| `backend/tests/unit/test_exporter.py` | NOVO — testes (abaixo) |
| `frontend-static/.gitignore` | NOVO — ignora o conteúdo (JSONs são artefato local, confidenciais: contêm trechos do pacote) |

Especificação dos payloads (o `staticProvider` do front — spec 14 — é quem lê):

```
frontend-static/
  manifest.json
  users.json                      # [{id, name, email}] — seeds, para o login mock
  projects.json                   # "GET /projects" completo (todos, page 1, sem filtro)
  <projectId>/
    project.json                  # "GET /projects/{id}"
    analyses.json                 # "GET /projects/{id}/analyses" → Analysis[] | null
    decisions.json                # "GET /projects/{id}/decisions" → Decision[]
    contestations.json            # "GET /projects/{id}/contestations" → Contestation[]
    rule-decisions.json           # "GET /projects/{id}/rule-decisions" → RuleDecision[]
    evidence-reviews.json         # "GET /projects/{id}/evidence-reviews" → EvidenceReview[]
    analysis/
      <analysisId>/
        status.json               # "GET /analyses/{id}/status"
        graph.json                # "GET /analyses/{id}/graph"
        report.json               # "GET /analyses/{id}/report.json" (ausente se estágio falhou)
```

## 5. Testes (escritos ANTES da implementação — test-first)

`backend/tests/unit/test_exporter.py` (padrão do repo: fakes + `factories.py`, sem rede,
`pytest-asyncio` auto, Mongo de teste já em conftest):

1. `test_export_writes_route_payloads_for_synthetic_project` — pacote sintético
   analisado com `FakeLLM(full_handlers())` + `InlineRunner` (padrão `test_delivery.py`);
   export roda; asserts: `projects.json` contém o projeto; `<pid>/project.json`,
   `analyses.json` (lista com 1 `Analysis`), `decisions.json` (lista), `graph.json`
   (`nodes`+`edges`), `status.json`, `report.json` existem; `users.json` tem os seeds.
2. `test_graph_and_analyses_validate_against_frontend_schemas` — os JSONs gravados
   re-parseiam com `frontend_api.schemas.Analysis` e `analyses.schemas.GraphRead`
   (fail fast do D10).
3. `test_projects_without_analysis_export_with_null_analyses` — projeto criado sem
   análise: aparece na lista com `scoreSummary: null`; `analyses.json` == `null`;
   `graph.json` não existe (D7).
4. `test_benchmark_projects_are_hidden` — projeto com `benchmark_id` setado não sai
   na lista nem ganha pasta (D6).
5. `test_failed_report_stage_omits_report_json` — análise com `report=None`:
   `report.json` ausente, `status.json` presente com estágio "parecer" = "falhou" (D8).
6. `test_manifest_has_counts_and_sha256` — `manifest.json` tem `gerado_em`, contagens
   por rota, `catalog_version`, `models`, e `sha256` de cada arquivo (D10b).
7. `test_owner_filter_and_single_project` — `--owner` exporta só projetos do dono;
   `--project PRJxx` exporta só a pasta dele; lista global continua completa no
   `projects.json` do export completo.
8. `test_users_json_has_no_password_hash` — `users.json` não contém `password_hash`
   nem `argon2` em nenhum valor (D4, segurança).

Critério de não-regressão: `uv run pytest tests/unit/test_delivery.py -q` continua verde
(o exporter não pode mexer no fluxo do delivery).

## 6. Fora do escopo

- Camada de escrita estática (decisões/contestações persistidas no front) — decidido fora.
- Chatbot/assistant em modo estático (precisa de LLM; fica mock).
- `GET /analyses/{id}/graph/trace/{node}` (o front não usa no hifi).
- PDF do parecer no estático (o front hifi não renderiza parecer em tela; o
  `AnalysisReport` usa a árvore).
- Re-execução do pipeline pelo CLI (extrator lê o que já está no banco).

## 7. Aceite

1. `uv run backend-export-frontend --out frontend-static` numa base com as 20 análises
   concluídas exporta: 20 pastas de projeto + `projects.json` + `users.json` + `manifest.json`,
   com validação pydantic verde em todas as `analyses`/`graph`.
2. `uv run pytest tests/unit/test_exporter.py -q` verde; `tests/unit/test_delivery.py` verde.
3. **Paridade delivery**: rodar `backend-entrega export` no mesmo benchmark e o
   `frontend/api_mock.json` resultante tem, para cada projeto exportado, os mesmos
   valores nas rotas em comum (`GET /projects/{id}/analyses` byte-idêntico após
   `json.dumps(sort_keys=True)`).
4. O front hifi consumindo `frontend-static/` (spec 14, etapa 2) renderiza a lista,
   a árvore de análise e o grafo sem erro de console, com os dados reais extraídos.
5. Nenhum segredo no export: sem hashes de senha, sem `OLLAMA_API_KEY`, sem conteúdo
   de `.env` (grep de aceitação no teste 8).