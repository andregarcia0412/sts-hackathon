# Spec 15 — Merge das integrações na `development`

Data: 2026-10-09
Status: planejada (execução após aprovação)
Branch: `merge/dev-integration` (criada de `origin/development` @ 1322872) — worktree `~/personal/sts-hackathon-repos/development`
Skill-gates: brainstorm (decisões antes de arquivos) · claude-superpowers (plan → isolate → test-first → double review)

## 1. Contexto — o que existe em cada lado

Topologia verificada com git (merge-bases e diffs reais):

| Branch | Base | Conteúdo |
|---|---|---|
| `origin/development` (1322872) | merge do `frontend-hifi` | **Front NOVO e diferente** do nosso: `NewProjectPage` (upload como tela própria), `UploadTable`+`uploadQueue` (fila animada), `domain/documents.ts` (tipos de doc por conteúdo), `decisionCsv`/`report` (exportar decisão PDF/CSV), `ProjectSearch`, `ResendFileDialog`, login redesenhado. **Backend ANTIGO** (ad9b037: sem specs 01–12 — sem rejudge, entrega, checagens CHK, gates de coerência) |
| `feature/front-static-data` (0c0d933) | `backend-merge` @ 2c3a1f2 | **Backend NOVO**: specs 01–12 (pipeline V9: gates, handbooks, questionário, coerência, benchmark/rejudge, entrega, CHK) + spec 13 (`backend-export-frontend`) + specs 13/14 + COMO-RODAR |
| `feature/frontend-static-provider` (d3195f5) | `frontend-hifi` @ ca48b46 | **Nossa integração front**: 3 modos (`VITE_DATA_SOURCE` mock/static/api), `http.ts` (JWT+refresh), `staticProvider.ts`, upload aceita todo tipo de arquivo, COMO-RODAR |

**A development NÃO contém nenhuma das nossas branches** (merge-bases distintos; 56 commits exclusivos dela).

### Front novo × nosso front: o que colide

Conflitos diretos (arquivos tocados dos dois lados, 3 apenas):
1. `frontend/src/services/api.ts` — development adicionou `hashId`, `toDocument`/`recognizeDocumentKind`, `decisionCsv`, `pendenciesOf`, usuários mock extras, `STORAGE_KEY v6`; nós adicionamos `dataSource`/static/api dispatch, `http.ts` imports, `adoptStaticProject`, mapeamento de outcomes
2. `frontend/src/features/projects/FileDropzone.tsx` — development refatorou para `domain/documents.ts`+`acceptedFiles.ts` (aceita pdf/docx/txt/md/csv/xlsx/json via `isAcceptedFile`); nós removemos o filtro accept por completo
3. `frontend/src/pages/projects/ProjectsPage.tsx` — development trocou `NewProjectDialog`→`ProjectSearch`/`ResendFileDialog` e reescreveu a página; nós adicionamos o import `dataSourceLabel` + banner

Nossos arquivos que NÃO existem na development (entram limpos): `http.ts`, `staticProvider.ts`, `dataSource.ts`, `staticProvider.test.ts`, `staticProvider.integration.test.ts`, `http.test.ts`, `__fixtures__/static-export/`, `__fixtures__/static-api/`, `.env.example` (front), `COMO-RODAR.md`.

Backend: **nenhum conflito** — a development não tocou em `backend/` desde ad9b037 (diff vazio entre merge-base e development), então o merge do backend é fast-forward-like (só entradas).

## 2. Objetivo

`development` final com: front novo da development **+** nossos 3 modos de dados (mock/static/api) **+** upload sem restrição de tipo **+** backend novo (specs 01–13) — tudo verde (testes das duas pontas).

## 3. Brainstorm — decisões

| # | Questão | Decisão | Por quê |
|---|---|---|---|
| D1 | Ordem do merge | **(1) backend** `front-static-data` → **(2) front** `frontend-static-provider`, nessa ordem, um merge commit cada | Backend sem conflitos destrava o export; front por cima, com os conflitos resolvidos de olho no contrato |
| D2 | Backend na development | Merge full (specs 01–13). A development usava backend antigo; o novo é retrocompatível no contrato (rotas iguais + extensões aditivas) | Sem isso o modo api não tem pipeline de verdade; o backend antigo não tem CHK/entrega |
| D3 | Conflito `FileDropzone` | **Ficar com a versão da development** (usa `domain/documents.ts` + `acceptedFiles.ts`) e **estender `acceptedFiles.ts`** para o espírito do nosso fix: manter os tipos documentados, mas o dropzone NÃO recusa desconhecidos — `isAcceptedFile` vira warning visual, não bloqueio | O front novo tem UX própria (UploadTable, ícones por tipo); replicar nosso fix por cima da refatoração deles quebraria `recognizeDocumentKind`. Um arquivo não listado sobe como "outro" — coerente com o backend, que aceita tudo e sinaliza pendência |
| D4 | Conflito `api.ts` | Merge manual **union**: manter TUDO que a development adicionou (hashId, toDocument, decisionCsv, users mock, v6) e enxertar nosso bloco por função (dispatch `dataSource()`, login/getUser por modo, mutations com mapeamento, assistant) | As duas evoluções são aditivas por função; o dispatch é o padrão já testado (90 testes nossos) |
| D5 | Conflito `ProjectsPage` | Ficar com a **página nova da development** e **reaplicar** o banner (`dataSourceLabel`) na nova descrição do `PageHeader` | Banner é 1 linha; a página mudou demais para patch direto |
| D6 | `STORAGE_KEY` | `v6` (da development) — **bump para `v7`** pois nosso merge muda o shape do db (projetos adotados do export) | Regra do AGENTS.md: mudou mocks/db → bump |
| D7 | Outcomes 3×4 | Manter nosso mapeamento (`needs_review`↔`insufficient_evidence`) no dispatch api | Contrato hifi é 3; backend 4; o mapeamento é nosso e testado |
| D8 | `NewProjectDialog` (nosso worktree) × `NewProjectPage` (development) | **Página da development**; nosso `api.ts` despacha `createProject` igual (o payload não muda) | O fluxo novo de upload chama o mesmo `useCreateProject`→`createProject` |
| D9 | Testes | Suíte da development (`npm test`) + **nossos 3 arquivos de teste** (static/http/integration) entram juntos; qualquer teste da development que dependa do `FileDropzone` restritivo é atualizado para o novo comportamento | As duas suítes têm que passar no resultado |
| D10 | `docker-compose.yml`, `backend/AGENTS.md` | Versão da nossa branch (backend novo precisa do compose; AGENTS descreve o pipeline atual) | A development deletou/antigou esses no diff base→development? Não: development só está atrás. Merge normal resolve |
| D11 | Execução | Merge na `merge/dev-integration` (worktree próprio), testes das duas pontas, **só depois** push + PR para `development` | Isolamento superpowers; nada vai para a development sem verde |

## 4. Arquivos

| Arquivo | Ação | Detalhe |
|---|---|---|
| (merge 1) `backend/**`, `docs/**`, `COMO-RODAR.md` | MERGE de `feature/front-static-data` | sem conflitos previstos |
| (merge 2) `frontend/src/services/api.ts` | MERGE MANUAL (union por função) | o coração da integração |
| (merge 2) `frontend/src/features/projects/acceptedFiles.ts` | PATCH | tipos conhecidos + aceitar não-listados como "outro" (D3) |
| (merge 2) `frontend/src/domain/documents.ts` | PATCH (se necessário) | `recognizeDocumentKind` cobre "outro" |
| (merge 2) `frontend/src/features/projects/FileDropzone.tsx` | RESOLVE → versão development + drop de `accept` | D3 |
| (merge 2) `frontend/src/pages/projects/ProjectsPage.tsx` | RESOLVE → development + banner `dataSourceLabel` | D5 |
| (merge 2) `frontend/src/services/{dataSource,http,staticProvider}.ts` + testes + fixtures + `.env.example` | ENTRAM LIMPOS | nossos |
| (merge 2) `frontend/src/services/api.ts` | bump `STORAGE_KEY` v7 | D6 |
| `docs/superpowers/specs/2026-10-09-merge-development.md` | NOVO | esta spec |

## 5. Testes (antes de declarar o merge pronto)

1. Backend: `cd backend && uv run pytest -q` — 362+10 testes verdes (suíte nova maior: specs 01–13).
2. Front: `npm test` — suíte da development + nossos 10 testes static/http + integration.
3. `npm run lint` + `npm run build` sem erros.
4. **Prova smoke dos 3 modos** (a mesma sequência das specs 13/14):
   - `npm run dev` (mock): lista fictícia carrega;
   - static: `backend-export-frontend --include-benchmark --out frontend/static-api` + `VITE_DATA_SOURCE=static` → lista PRJ01/PRJ02, análise abre;
   - api: uvicorn + `VITE_DATA_SOURCE=api` → login `user1@sts.com`/`senha12345`, upload de um pacote csv/xlsx/md/json (antes bloqueados), análise conclui.
5. Prova do upload sem restrição: arrastar um arquivo `.zip`/`.xml` (não listado) → entra na fila como "outro", sem rejeição.

## 6. Fora de escopo

- Resolver divergências de UX da development (não mexemos no design novo).
- `frontend-hifi` → development (a development JÁ tem o merge e06c05c do hifi).
- Apagar a pasta `frontend/` legada dentro da branch do backend (fica como está).
- CI (não existe); o "verde" é local.

## 7. Aceite

1. `merge/dev-integration` com os dois merges, zero conflito remanescente, `git log` mostrando ambas as linhagens.
2. Todos os testes das duas pontas verdes + lint/build + smoke dos 3 modos (§5).
3. A development resultante sobe o front NOVO (NewProjectPage, upload queue) com nossos 3 modos de dados por trás — modo api com upload irrestrito funcionando de ponta a ponta.
4. PR aberto de `merge/dev-integration` → `development` com o resumo do merge e os passos de smoke para o revisor.