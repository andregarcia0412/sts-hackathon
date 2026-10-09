# PLAN + Quality Gates — Spec 13: export estático (`backend-export-frontend`)

Data: 2026-10-09 · Spec: `2026-10-09-export-estatico-frontend.md` · Branch: `feature/front-static-data`
Skill: claude-superpowers (Plan → Isolate → Test First → Double Review)

## TASK

CLI `backend-export-frontend` que lê o Mongo e escreve `frontend-static/` (payloads por
rota, mesmos shapes da API) + validação pydantic fail-fast + manifest com sha256.

## APPROACH

Reuso máximo: `project_analysis`, `summarize`, `GraphRead/GraphNodeRead/GraphEdgeRead`,
`ProjectQuery/apply_project_query` e `get_catalog` — o exporter não projeta nada próprio,
só consulta o banco e serializa como as rotas fazem. O CLI é fino (argparse + init_db +
loop de projetos). Test-first: os 8 testes da spec antes do exporter; validação pydantic
da saída é parte do código (fail fast), não só do teste.

## ARQUIVOS

| Arquivo | Ação | Motivo |
|---|---|---|
| `backend/tests/unit/test_exporter.py` | NOVO (primeiro) | 8 testes da spec §5, RED antes do exporter |
| `backend/src/backend/frontend_api/exporter.py` | NOVO | consulta Mongo → payloads por rota + validação + manifest |
| `backend/src/backend/frontend_api/cli.py` | NOVO | argparse (`--out`, `--owner`, `--project`), `init_db`, resumo |
| `backend/pyproject.toml` | PATCH | `[project.scripts] backend-export-frontend = "backend.frontend_api.cli:main"` |
| `frontend-static/.gitignore` | NOVO | conteúdo confidencial (trechos do pacote) nunca versionado |

## ORDEM (test-first)

1. `test_exporter.py`: testes 1–8 da spec (pacote sintético via `factories.py` +
   `FakeLLM(full_handlers())` + `InlineRunner`, padrão `test_delivery.py`). Rodar → RED.
2. `exporter.py`: `export_frontend(out, owner=None, project=None) -> ExportResult`;
   payloads por rota (spec §4), validação `frontend_api.schemas.Analysis` +
   `analyses.schemas.GraphRead` por projeto, `manifest.json` (contagens, catálogo,
   modelos, sha256). Rodar → GREEN.
3. `cli.py` + `pyproject.toml` → `uv run backend-export-frontend --out <pasta>`.
4. Regressão: `test_delivery.py` + suíte unit inteira.
5. Run real na base atual (PRJ01/PRJ02 concluídos, benchmark 6ac8cb2300861ec8bad60b02)
   → inspecionar pasta, conferir manifest.
6. Paridade delivery (gate G5).

## EDGE CASES TRATADOS

- Projeto sem análise: lista com `scoreSummary: null`; `analyses.json` = `null`; sem grafo.
- Estágio parecer falhou (`Analysis.report is None`): `report.json` ausente (não vazio).
- Projetos de benchmark: fora da lista e sem pasta (`benchmark_id == None`).
- `users.json`: só `id/name/email` — nunca `password_hash`/argon2.
- Payload que não valida: `ExportError` com caminho do arquivo (fail fast, sem arquivo órfão).
- `--owner`/`--project`: filtram pastas e payloads por projeto; `projects.json` reflete o filtro.
- Base vazia: exporta só `users.json` + `manifest.json` com contagens 0 (não crasha).

## EDGE CASES FORA DE ESCOPO

- Análise ainda `rodando` no momento do export (snapshot: sai como está, status real).
- Corrida concorrente export × pipeline (aviso no manifest: `gerado_em` é o corte).
- Re-execução do pipeline pelo CLI (spec 13 §6).

## SUPORTE/SUPosiÇÕES

- Mongo no ar (docker compose) e `backend/.env` com `MONGODB_URI` — já configurado.
- `conftest.py` provê o fixture `db` (mesmo do `test_delivery.py`).
- Catálogo via `get_catalog()` (sync já feito pelo app; CLI chama `sync_catalog_to_db`
  como os outros CLIs).

# QUALITY GATES — Spec 13

Executáveis; todos devem estar verdes antes de "pronto".

- **G1 RED→GREEN**: `uv run pytest tests/unit/test_exporter.py -q` falha com os 8
  testes antes do exporter e passa depois (arquivo de teste commitado ANTES do código).
- **G2 Regressão delivery**: `uv run pytest tests/unit/test_delivery.py -q` verde.
- **G3 Suíte**: `uv run pytest tests/ -q` verde (unit+api; Mongo de teste).
- **G4 Run real**: `uv run backend-export-frontend --out /tmp/frontend-static` na base
  atual → exit 0; `manifest.json` com 2 projetos, contagens por rota batendo com
  `mongosh` (`db.analyses.countDocuments({status:"concluida"})`); pastas de projeto
  com `analyses.json` não-nulo, `graph.json`, `report.json`.
- **G5 Paridade delivery**: `uv run backend-entrega export 6ac8cb2308861ec8bad60b02
  --out <fora do repo>` → `json.dumps(sort_keys=True)` de `GET /projects/{id}/analyses`
  e `GET /analyses/{id}/graph` idêntico entre `frontend/api_mock.json` (delivery) e os
  arquivos do exporter, projeto a projeto.
- **G6 Sem segredos**: `grep -riE 'password_hash|argon2|ollama_api_key|jwt_' /tmp/frontend-static/`
  sem matches (o teste 8 cobre `users.json`; o gate cobre tudo).
- **G7 Fail fast**: teste 2 prova que JSON inválido aborta com `ExportError` + caminho.
- **G8 Double review 1 (correto)**: cobre os 8 testes da spec §5; sem análise = null
  (não 0 nem exceção); benchmark oculto; report ausente quando falhou; filtros funcionam.
- **G9 Double review 2 (qualidade)**: sem dead code; `exporter.py` sem query N+1
  (projetos agrupados por batch de ids); erros de banco viram mensagem clara (não stack
  crua); nomes em inglês, vocabulário de domínio em pt-BR; nenhum print fora do CLI.
- **G10 Lint/type**: `uv run pytest tests/unit/test_exporter.py -q` já cobre; adicional:
  `uv run python -m compileall backend/src/backend/frontend_api` (ou ruff se configurado).
- **G11 Commit**: testes primeiro, implementação depois; mensagem
  `feat(frontend_api): export estático para o front (spec 13)`.