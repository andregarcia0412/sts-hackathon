# Design — Integração do frontend com a API do ai-microservice

Data: 2026-10-08
Status: aprovado no fluxo (spec → implementação)
Branch alvo: `feature/models-and-modules`

## 1. Contexto

O frontend (`frontend/`) é um app Vite 8 + React 19 que hoje carrega TUDO de mocks
(`src/services/api.ts` → `src/mocks/*`, banco no localStorage). O backend
(`backend/` ai-microservice, FastAPI) já expõe o pipeline de agentes de evidências:

| Rota | Contrato |
|---|---|
| `POST /analyze {project_path}` | `{analise_id, project_id}` — enfileira análise |
| `GET /status/{analise_id}` | etapas, status, `version` quando concluída |
| `GET /graph/{project_id}` | `{version, nodes[], edges[], meta}` (novo: `meta.consistencia`, `manifest_hash`) |
| `GET /regras`, `/regras/{id}` | catálogo de regras (97+1) |

O grafo tem nós `projeto · criterio · regra · evidencia · fonte · web_source ·
query · gap` e arestas `compoe · sustenta · contraria · neutra · cita · retornou`.
**Sem CORS configurado** no backend.

O `frontend/PENDENCIAS.md` lista como essencial: "Trocar os mocks pela API real em
`src/services/api.ts`". A arquitetura já prepara o ponto de troca: telas só falam
com `services/api.ts`; tipos do contrato provisório em `domain/types.ts`.

## 2. O que NÃO dá para integrar ainda (lacunas do backend)

O frontend espera uma API de análise em árvore (`Analysis`: Critério→Regra→Evidência
com score 0–100), projetos, decisões, contestações e chatbot. O backend ainda não tem:
módulo 6 (parecer/score), CRUD de projetos, decisões/contestações, endpoint de chat.

**Decisão**: integração **incremental e aditiva** — o frontend ganha um cliente HTTP
e um adapter do grafo real, e `api.ts` tenta o backend primeiro com **fallback para
os mocks** (demo ininterrupta). Decisões/contestações/upload/chat permanecem mockados,
reservados na spec para a próxima iteração.

## 3. Decisões

| # | Decisão | Escolha |
|---|---|---|
| 1 | Onde troca acontece | SÓ em `services/` (api.ts + novos http.ts/aiAdapter.ts); telas intactas |
| 2 | Descoberta de análises do backend | `GET /regras` (lista regras do catálogo) NÃO lista projetos; backend expõe grafo por `project_id` — o front descobre via endpoint NOVO `GET /projects` (aditivo, ~20 linhas, lista `data/graphs/*`) |
| 3 | Score 0–100 | Função determinística por regra derivada do estado: evidências (1 sustenta=+15, 1 contraria=−15, neutra=0, base 50, clamp 0–100; gate contraria=0; sem evidência=50 e marcada "sem evidência"; N/A/parcial/absorvida=0 com reason). Nunca probabilidade — "força da evidência" |
| 4 | Critério → score | Média ponderada das regras (scoring_role `gate` e `mean` contam; `informativa` não), média simples + arredondamento |
| 5 | Fallback | `getAnalyses(projectId)`: backend primeiro (por project_id presente em `GET /ai-projects`), erro/404 → mocks; banner na tela indica a fonte (dados reais do pipeline vs EXEMPLO FICTÍCIO) |
| 6 | CORS | `CORSMiddleware` allow_origins=[`http://localhost:5173`,`http://127.0.0.1:5173`]; sem credenciais |
| 7 | Auth | Mock do front permanece (sessão localStorage); a API da AI é pública em dev (hackathon); sem token no fetch |
| 8 | Tipos | Adapter converte `graph` → `Analysis`; tipos do grafo no adapter (não poluem `domain/types.ts`) |

## 4. Formato do mapeamento (aiAdapter)

- `projeto:PRJxx` → raiz; `criterio:<nome> → Criterion` (score médio das regras);
  `regra:<ID> → Rule` (code=ID, score da função, evidências dos nós apontados
  pelas arestas `sustenta/contraria/neutra` vindas de `evidencia`);
- Evidência: `polaridade` sustenta→"positive", contraria→"negative", neutra→"positive
  (fraca)" na explicação, `explanation`=justificativa (ou motivo do gap),
  `projectExcerpt.excerpt`=quote, `projectExcerpt.fileName`=fonte, `references` =
  normative sources da regra (`GET /regras/{id}`) + âncora do fragmento;
- gaps: viram evidência neutra com explanation="gap" e polarity negativa quando da
  regra exigida;
- Regras `na/parcial/absorvida` viram regra com score 0 + explanation(status_reason) —
  rastreáveis;
- `suggestedCategory` fica ausente (módulo 6, fora do escopo).

## 5. Arquivos

| Arquivo | Mudança |
|---|---|
| `backend/src/ai_microservice/api/projects.py` | NOVO — `GET /ai-projects` (lista project_ids com grafo) + `GET /regras` reuso |
| `backend/src/ai_microservice/main.py` | PATCH — CORSMiddleware + include do router novo |
| `frontend/src/services/http.ts` | NOVO — fetch base, `ApiError`, timeout 10 s, `VITE_API_URL` (default 127.0.0.1:8000) |
| `frontend/src/services/aiAdapter.ts` | NOVO — graph→Analysis (função pura) + score |
| `frontend/src/services/aiAdapter.test.ts` | NOVO — testes do adapter + score |
| `frontend/src/services/http.test.ts` | NOVO — base URL, ApiError, timeout |
| `frontend/src/services/api.ts` | PATCH — `listAiProjects`, `fetchAiAnalysis`; `getAnalyses` = backend→mock fallback; lista de projetos ganha externos |
| `frontend/src/services/queries.ts` | PATCH — `useAiProjects`, `useAiGraph` |
| `frontend/src/pages/analysis/AnalysisPage.tsx` | PATCH — banner de fonte (real × fictícia) |
| `frontend/.env.example` | NOVO — `VITE_API_URL=http://127.0.0.1:8000` |
| `docs/superpowers/specs/2026-10-08-integracao-front-ai.md` | NOVO — esta spec |

## 6. Fora do escopo (próxima iteração)

- Decisões/contestações/reanálise reais (módulo 6 não existe).
- Upload real de arquivos (backend lê do disco do servidor).
- Chatbot real (não há endpoint de chat; formato `AssistantAnswer` reservado).
- Login real, permissões, MongoDB do GraphStore.

## 7. Aceite

1. `npm test`, `npm run lint` e `npm run build` verdes no frontend.
2. Backend com CORS: request do origin 5173 passa (curl com Origin).
3. `npm run dev` + uvicorn: abrir um projeto PRJxx mostra a árvore REAL do grafo
   (Critério→Regra→Evidência com quotes do pacote); projetos mockados seguem
   funcionando inalterados (fallback).
4. Banner identifica "Análise do pipeline de agentes (grafo vX)" vs "EXEMPLO FICTÍCIO".
5. Score 0–100 derivado da polaridade (nunca "probabilidade") — faixas de
   `domain/score.ts` continuam válidas.