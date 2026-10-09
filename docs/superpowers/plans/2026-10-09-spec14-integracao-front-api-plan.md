# PLAN + Quality Gates — Spec 14: front hifi × API (3 etapas)

Data: 2026-10-09 · Spec: `2026-10-09-integracao-front-api.md` · Branch: `feature/front-static-data` (docs) + `feature/frontend-hifi` (código front)
Skill: claude-superpowers (Plan → Isolate → Test First → Double Review)

## TASK

Fazer o `api.ts` do front hifi servir 3 fontes comutáveis por env (`mock` | `static` | `api`)
sem tocar nas telas: E1 provider estático (JSONs da spec 13), E2 HTTP real de leitura
com JWT + refresh, E3 HTTP real de escrita (upload multipart, decisões, contestações,
reanálise, assistant) — sempre com fallback mock.

## APPROACH

Despacho por fonte SÓ dentro de `services/` (regra 1 do AGENTS.md do front): `api.ts`
continha a mesma assinatura das 17 funções; cada leitura pergunta a `dataSource.ts`
e delega a `mocks` (hoje), `staticProvider.ts` (E1) ou `http.ts`+rotas (E2/E3).
Fallback mock em cada função de dados (backend fora → demo segue, com banner).
Cada etapa fecha verde (testes + lint + build) antes da próxima; trabalho isolado em
`feature/front-static-data` para docs e branch derivada da `frontend-hifi` para o código.

## ARQUIVOS POR ETAPA

### E1 — estático

| Arquivo | Ação | Motivo |
|---|---|---|
| `frontend/src/services/__fixtures__/static-export/` | NOVO (primeiro) | export sintético mínimo (2 projetos: 1 com análise+grafo, 1 sem) p/ testes |
| `frontend/src/services/staticProvider.test.ts` | NOVO | 6 testes E1 (spec §4-E1) |
| `frontend/src/services/dataSource.ts` | NOVO | lê envs, tipa fonte, `dataSourceLabel()` |
| `frontend/src/services/staticProvider.ts` | NOVO | carrega JSONs, indexa, `applyProjectQuery` local |
| `frontend/src/services/api.ts` | PATCH | leituras despacham; mutations → mock; export do label |
| `frontend/src/features/analysis/AnalysisWorkspace.tsx` | PATCH | banner da fonte (D8) |
| `frontend/.env.example` | PATCH | `VITE_DATA_SOURCE`, `VITE_STATIC_API_DIR`, `VITE_API_URL` |

### E2 — HTTP leitura + JWT

| Arquivo | Ação | Motivo |
|---|---|---|
| `frontend/src/services/http.test.ts` | NOVO (primeiro) | 5 testes E2 |
| `frontend/src/services/auth.ts` | NOVO | storage de tokens, `refreshAccessToken()`, `logout()` |
| `frontend/src/services/http.ts` | NOVO | fetch base: Bearer, `ApiError`, timeout 10 s, refresh 1× em 401 |
| `frontend/src/services/api.ts` | PATCH | `login` real; 7 leituras via http; fallback mock |

### E3 — HTTP escrita + assistant

| Arquivo | Ação | Motivo |
|---|---|---|
| `frontend/src/services/api.writes.test.ts` | NOVO (primeiro) | 5 testes E3 |
| `frontend/src/services/http.ts` | PATCH | helper `postForm` (multipart) |
| `frontend/src/services/api.ts` | PATCH | 8 mutations reais com fallback; `askAssistant`/`openDebate` via `POST /assistant/*` |

## ORDEM (test-first, por etapa)

**E1:** fixtures + `staticProvider.test.ts` → RED → `dataSource.ts` + `staticProvider.ts`
→ GREEN → patch `api.ts` + banner + `.env.example` → lint/build. Commit `feat(frontend): provider estático (spec 14 E1)`.
**E2:** `http.test.ts` → RED → `auth.ts` + `http.ts` → GREEN → patch leituras `api.ts`
→ lint/build → prova manual com uvicorn (login seed, lista real). Commit `feat(frontend): API de leitura com JWT (spec 14 E2)`.
**E3:** `api.writes.test.ts` → RED → `postForm` + mutations → GREEN → fluxo completo
no navegador (decisão aparece no Mongo; reanálise cria v2). Commit `feat(frontend): API de escrita e assistant (spec 14 E3)`.

## EDGE CASES TRATADOS

- `VITE_DATA_SOURCE` ausente/inválida → mock (comportamento atual, zero regressão).
- Export incompleto (projeto da lista sem pasta): provider devolve `null`/404-equivalente, não crasha.
- `getAnalyses` com projeto em processamento → `null` (polling segue; contrato).
- 401 no meio de sessão → refresh 1× → refaz; refresh falho → `AuthError` → login; sem loop.
- Refresh expirado E access expirado → logout limpo, sem dado órfão no localStorage.
- Timeout/abort do fetch → `ApiError` amigável + fallback mock em leituras.
- Score `null` (regra sem evidência) → chip "sem evidência", nunca 0 (D7).
- Multipart grande (.zip) → `postForm` sem JSON intermediário; erro 4xx legível.
- `requestReanalysis` com contestação já resolvida → erro do backend propagado como `ApiError`, sem duplicar.
- Vitest em node puro: stubs de `window`/`localStorage`/`crypto.randomUUID` renovados no `beforeEach` (regra do skill — stub no corpo do describe vaza).
- React Query cache de query falhada: e2e faz hard-refresh; gate G14 cobre.

## EDGE CASES FORA DE ESCOPO

- Escrita persistida no modo estático (spec 13 §6 / decisão do usuário).
- Registro de usuário pelo front; `GET /regras`; PDF do parecer no front (spec 14 §5).
- Streaming/SSE (polling atual); multi-abas sincronizadas.

## SUPORTE/SUPOSIÇÕES

- Backend desta branch no ar (`uv run backend`) para E2/E3 manuais e e2e.
- Seeds `user1..5@sts.com` / `senha12345` (`.env` do backend) p/ login demo.
- `frontend/` da `frontend-hifi` com `npm install` feito; vitest/oxlint/tsc configurados.
- Contrato de extensões conforme AGENTS.md do backend (status, counts, suggestedClass,
  inconsistent, caveat, missingLink, divergences, versions) — tipos TS estendem, nunca estreitam (D6).

# QUALITY GATES — Spec 14 (por etapa; todos verdes antes de "pronto" da etapa)

## E1 — estático

- **G1 RED→GREEN**: `npm test` com `staticProvider.test.ts` RED antes do provider, GREEN depois.
- **G2 Suíte**: `npm test` integral verde (regressão: mocks atuais intactos).
- **G3 Lint/build**: `npm run lint` zero avisos; `npm run build` verde.
- **G4 Prova manual**: `VITE_DATA_SOURCE=static npm run dev` com export real (spec 13)
  → lista com scoreSummary, árvore com citações, grafo animando; console sem erros;
  sem a env → demo atual idêntica.
- **G5 Sem vazamento de camada**: `grep -rn "fetch(" src/features src/pages 2>/dev/null`
  → 0 matches (só `services/` fala HTTP).

## E2 — HTTP + JWT

- **G6 RED→GREEN**: `http.test.ts` RED→GREEN (login, refresh-1×, `ApiError`, null-safe).
- **G7 Suíte + lint + build** (idem G2/G3).
- **G8 Prova real**: uvicorn no ar + login `user1@sts.com` → projetos reais do banco
  (não-benchmark) na lista; árvore/grafo com dados do PRJ01; matar uvicorn → fallback
  mock + banner, sem crash.
- **G9 Refresh**: access expirado (mock de 15 min no teste) → 1 refresh → requisição
  original refeta; segundo 401 → `AuthError`; nenhuma chamada em loop (assert no teste).
- **G10 Tokens**: localStorage nunca expõe senha; logout remove tokens; teste cobre.

## E3 — escrita + assistant

- **G11 RED→GREEN**: `api.writes.test.ts` RED→GREEN (FormData, Reads com id/decidedAt,
  reanalysis, assistant, fallback por mutation).
- **G12 Suíte + lint + build** (idem G2/G3).
- **G13 Fluxo completo**: login → upload → polling → árvore → decisão → contestação →
  reanálise (v2 no Mongo: `db.analyses.countDocuments({project_id})` sobe) → assistant
  com citações. Evidência: prints + query Mongo anexados ao PR.
- **G14 E2E**: `npm run test:e2e` verde com backend no ar (hard-refresh onde o cache
  do React Query puder servir resposta antiga).
- **G15 Sem vazamento**: idem G5 após E3.
- **G16 Double review 1 (correto)**: 17 funções de `api.ts` despacham por fonte;
  fallback em TODAS; banner nas 3 fontes; score null ≠ 0; contract types.ts estendido
  sem quebrar tela existente.
- **G17 Double review 2 (qualidade)**: sem dead code/imports; erros sempre com
  mensagem legível; segredos nunca em código (envs); tokens fora do bundle; componentes
  intactos (só `services/` mexeu, exceto o banner); commits pequenos com escopo
  `feat(frontend)`.

## Geral (fechamento das 3 etapas)

- **G18**: aceites 1–5 da spec §6 verificados um a um no PR final.
- **G19**: `uv run pytest tests/unit -q` verde no backend (specs não quebram nada).