# Spec 14 — Front hifi × API real: integração em 3 etapas (mock → estático → API)

Data: 2026-10-09
Status: planejada (test-first por etapa; cada etapa fecha verde antes da próxima)
Branch: `feature/front-static-data` (spec 13: extrator) + `feature/frontend-hifi` (front)
Skill-gates: brainstorm (decisões antes de arquivos) · claude-superpowers (plan → isolate → test-first → double review)

## 1. Contexto

O front hifi (`frontend/` da branch `feature/frontend-hifi`) fala SÓ com
`src/services/api.ts` (regra do AGENTS.md: telas nunca chamam fetch). Hoje 100% mock.
O backend desta branch já expõe o contrato completo que o front declara em
`src/domain/types.ts` — com extensões documentadas (state, counts, status, sources,
suggestedClass, inconsistent, caveat, missingLink, divergences, versions).

Rotas reais (FastAPI, camelCase, JWT):

| Rota do front (`api.ts`) | Rota real | Observação |
|---|---|---|
| `listProjects(query)` | `GET /projects?search=&statuses=&weakestBand=&outcome=&from=&to=&sort=&page=&pageSize=` | `ProjectPage` camelCase idêntico; filtros server-side |
| `getProject(id)` | `GET /projects/{id}` | `ProjectRead` |
| `createProject(input, ownerId)` | `POST /projects` (multipart: files, name, company, freeText) | dispara análise em background; `201` + `ProjectRead` |
| `getAnalyses(projectId)` | `GET /projects/{id}/analyses` | `Analysis[] \| null` (null = nada concluído) |
| `listDecisions` / `saveDecision` | `GET\|POST /projects/{id}/decisions` | append-only; `DecisionRead` |
| `listContestations` / `createContestation` | `GET\|POST /projects/{id}/contestations` | `ContestationRead` |
| `requestReanalysis(contestationId)` | `POST /contestations/{id}/reanalysis` | nova versão da análise |
| `listRuleDecisions` / `createRuleDecision` | `GET\|POST /projects/{id}/rule-decisions` | |
| `listEvidenceReviews` / `createEvidenceReview` | `GET\|POST /projects/{id}/evidence-reviews` | |
| `askAssistant` / `openDebate` | `POST /assistant/ask` · `POST /assistant/debate` | body `{question, context}`; `AssistantAnswer` = `blocks[] + sources[]` (mesma forma do `domain/assistant.ts`) |
| `login` / `listDemoUsers` | `POST /auth/login` → `{accessToken, refreshToken, tokenType: "bearer"}` · seeds em `users.json` do export | JWT access 15 min + refresh 7 d |
| (status do processamento) | `GET /analyses/{id}/status` | o front já faz polling com `refetchInterval` |
| (grafo React Flow) | `GET /analyses/{id}/graph` | `GraphRead {analysisId, nodes[], edges[]}`; o front hifi já monta o layout com dagre |

CORS já configurado no backend: `CORS_ORIGINS` (default `http://localhost:5173`),
`allow_credentials=True` (main.py:65-70).

## 2. Objetivo

O `api.ts` passa a ter **três fontes** comutáveis sem tocar nas telas:
(1) mocks atuais, (2) JSONs estáticos da spec 13, (3) API real — sempre com
**fallback mock** (demo nunca quebra sem backend).

## 3. Brainstorm — decisões

| # | Questão | Decisão | Por quê |
|---|---|---|---|
| D1 | Onde troca a fonte | SÓ em `services/` (`api.ts` + `http.ts` + `staticProvider.ts`); telas, hooks (`queries.ts`), domain intactos | Regra 1 do AGENTS.md do front; mesmo desenho da spec de integração antiga (2026-10-08) |
| D2 | Seleção da fonte | `VITE_DATA_SOURCE = "mock" \| "static" \| "api"` (default `mock`): `static` lê `VITE_STATIC_API_DIR`; `api` usa `VITE_API_URL`. Sem a env → mock (atual) | Uma env, zero código; demo nunca quebra |
| D3 | Auth em modo API | `login()` real → guarda `{user, accessToken}` em localStorage; `http.ts` injeta `Authorization: Bearer` e **renova via `/auth/refresh`** em 401 (1 tentativa, depois `AuthError` → tela de login); `listDemoUsers` em modo API lê os seeds (`GET /projects` é autenticado, os e-mails seed vêm do `.env` do backend — o front lista via `users.json` do export ou mantém o mock) | Backend exige JWT em tudo; 15 min de access exige refresh transparente |
| D4 | Auth em modo estático | Login **mock do front** mantido (qualquer senha), sessão em localStorage; `users.json` (se existir) substitui `mockUsers` | Decisão do usuário (spec 13 D4); sem backend não há token |
| D5 | Escrita em modo estático | Mutations (`saveDecision`, `createContestation`, …) seguem **mock** (in-memory, localStorage) mesmo em `static`; leituras vêm dos JSONs | Modo estático é leitura (decisão do usuário); o front já persiste mocks no localStorage |
| D6 | Divergência de contrato | Onde a extensão do backend difere do `types.ts` (ex.: `Rule.status`, `counts`, `suggestedClass`), o **TS estende os tipos** (`interface` nova `Rule` com campos opcionais), nunca estreita; `score: number \| null` no lugar de `number` (backend: sem evidência = null) | O `types.ts` é fonte da verdade, mas as extensões do AGENTS.md do backend já são o contrato documentado |
| D7 | Score null | `getScore(rule)` trata `null` como "sem evidência" (chip neutro), não como 0 | Vazio ≠ zero (AGENTS.md backend nº4) |
| D8 | Banner de fonte | Tela de análise mostra a fonte: "Dados do pipeline (API)" / "Dados estáticos extraídos em `<manifest.gerado_em>`" / "EXEMPLO FICTÍCIO" | Mesma prática da integração anterior; transparência para o juiz |
| D9 | Assistant em modo estático | `askAssistant`/`openDebate` seguem mock (o motor de resposta precisa de LLM) | Sem backend não há /assistant |
| D10 | Upload real | `createProject` em modo API envia `multipart/form-data` (arquivos + campos); em mock/static, comportamento atual | `POST /projects` real aceita multipart e .zip |
| D11 | Polling | Modo API: `useAnalyses`/`useProject` mantêm os `refetchInterval` atuais; `getAnalyses` retorna `null` enquanto não há análise concluída (contrato) | O `queries.ts` já faz isso |
| D12 | Ordem das etapas | **E1 (estático)** → **E2 (API leitura)** → **E3 (API escrita + assistant)** | Cada etapa entrega valor sozinha; E1 destrava o demo sem backend; E2/E3 só fazem sentido com backend no ar |

## 4. Etapas (cada uma = branch/commit próprio, test-first)

### Etapa 1 — Provider estático (consome a spec 13)

**Arquivos (front, `feature/frontend-hifi`):**

| Arquivo | Mudança |
|---|---|
| `frontend/src/services/dataSource.ts` | NOVO — lê `VITE_DATA_SOURCE`/`VITE_STATIC_API_DIR`/`VITE_API_URL`; tipa a fonte |
| `frontend/src/services/staticProvider.ts` | NOVO — carrega os JSONs (`fetch` em dev, `import.meta.glob` no build), indexa por projectId/analysisId, aplica `ProjectQuery` local (reusa `applyProjectQuery` de `src/mocks/projectQuery.ts`) |
| `frontend/src/services/api.ts` | PATCH — leituras despacham por fonte; mutations → mock; export `dataSourceLabel()` p/ banner |
| `frontend/src/features/analysis/AnalysisWorkspace.tsx` (ou header da análise) | PATCH — banner da fonte (D8) |
| `frontend/.env.example` | PATCH — `VITE_DATA_SOURCE=mock`, `VITE_STATIC_API_DIR=./static-api`, `VITE_API_URL=http://127.0.0.1:8000` |
| `frontend/src/services/staticProvider.test.ts` | NOVO — testes E1 |

**Testes E1 (vitest, node puro — stubs de `window`/`localStorage`/`crypto.randomUUID` no `beforeEach`, regra do skill):**
1. carrega pasta de export sintética (fixture mínima em `src/services/__fixtures__/static-export/`) e `listProjects` devolve a página com scoreSummary real;
2. `getAnalyses(pid)` devolve a árvore com score `null` em regra sem evidência (D7) e o grafo indexado;
3. filtros `ProjectQuery` aplicados localmente batem com a página esperada;
4. projeto sem análise → `null` (não lança);
5. mutations em `static` continuam mockadas (não chamam fetch);
6. `dataSourceLabel()` retorna o rótulo certo para as 3 fontes.

**Aceite E1:** `npm test`, `npm run lint`, `npm run build` verdes; `VITE_DATA_SOURCE=static npm run dev` renderiza lista + árvore + grafo com dados do export; sem a env, comportamento atual inalterado.

### Etapa 2 — API real, leitura (JWT)

**Arquivos (front):**

| Arquivo | Mudança |
|---|---|
| `frontend/src/services/http.ts` | NOVO — fetch base: `VITE_API_URL`, `ApiError`, timeout 10 s, `Authorization: Bearer`, refresh em 401 (1×) via `/auth/refresh`, `credentials: "include"` não (usa header) |
| `frontend/src/services/api.ts` | PATCH — em `api`: `login` real (`POST /auth/login`, guarda tokens), leituras (`listProjects`, `getProject`, `getAnalyses`, `listDecisions`, `listContestations`, `listRuleDecisions`, `listEvidenceReviews`) via `http.ts`; mutations ainda mock até E3 |
| `frontend/src/services/auth.ts` | NOVO — storage dos tokens, `refreshAccessToken()`, `logout()` |
| `frontend/src/services/http.test.ts` · `api.auth.test.ts` | NOVOS — testes E2 |

**Testes E2:**
1. `login` real troca email/senha por tokens e persiste; senha errada → `AuthError` (401 do backend);
2. 401 em `listProjects` dispara refresh 1× e refaz; refresh falho → `AuthError`;
3. `getAnalyses` parseia `Analysis[] | null` com extensões (status, counts, suggestedClass);
4. timeout/abort → `ApiError` com mensagem amigável;
5. `VITE_DATA_SOURCE=api` sem backend no ar → **fallback mock** silencioso (demo não quebra) + banner.

**Aceite E2:** idem E1 + com uvicorn no ar e login seed (`user1@sts.com` / `senha12345`), a lista mostra os projetos reais do banco (não-benchmark), a árvore renderiza com citações do pacote e o grafo anima; matar o uvicorn cai no mock com banner.

### Etapa 3 — API real, escrita + assistant

**Arquivos (front):**

| Arquivo | Mudança |
|---|---|
| `frontend/src/services/api.ts` | PATCH — mutations reais: `createProject` (multipart), `saveDecision`, `createContestation`, `requestReanalysis`, `createRuleDecision`, `createEvidenceReview`, `askAssistant`, `openDebate`; fallback mock em cada um |
| `frontend/src/services/http.ts` | PATCH — helper `postForm` (multipart) |
| `frontend/src/services/api.writes.test.ts` | NOVO — testes E3 |

**Testes E3:**
1. `createProject` monta `FormData` com arquivos + campos e recebe `201 ProjectRead`;
2. `saveDecision`/`createContestation` retornam o `Read` com `id`/`decidedAt`/`createdAt`;
3. `requestReanalysis` devolve a contestação resolvida e o front invalida as queries (já faz via `queries.ts`);
4. `askAssistant` em modo API posta `{question, context}` e recebe `AssistantAnswer` (blocks/sources) — tipos de `domain/assistant.ts` inalterados;
5. cada mutation com backend fora → fallback mock (demo segue).

**Aceite E3:** fluxo completo no navegador: login real → upload de pacote (ou `backend-import`) → processamento (polling) → árvore/grafo reais → decisão salva no banco (visível no Mongo) → contestação → reanálise (nova versão) → assistant respondendo com citações. `npm run test:e2e` verde com backend no ar (login `user1@sts.com`).

## 5. Fora do escopo

- Modo estático com escrita persistida (decidido fora).
- `GET /regras` no front (catálogo puro; o hifi não usa).
- Relatório PDF no front (hifi não renderiza parecer em tela).
- Registro de usuário pelo front (`POST /auth/register` existe; login seed basta p/ demo).
- Streaming/SSE (o front usa polling).

## 6. Aceite geral (as 3 etapas fechadas)

1. Front roda em **qualquer** das 3 fontes sem mudar telas: `mock` (default, atual),
   `static` (JSONs da spec 13), `api` (backend no ar) — troca só por env.
2. Nenhuma tela chama fetch fora de `services/` (grep `fetch(` em `src/features` = 0).
3. Sem backend e sem export: comportamento atual idêntico (zero regressão de demo).
4. `npm test`, `npm run lint`, `npm run build`, `npm run test:e2e` verdes no front;
   `uv run pytest tests/unit -q` verde no backend (specs 13 e 14 não quebram nada).
5. Banner sempre visível na análise indicando a fonte dos dados.