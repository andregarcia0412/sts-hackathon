# Como rodar o projeto — Lei do Bem (STS 2026)

Guia completo das formas de subir o app. Escolha pelo cenário:

| Cenário | Modo | Precisa de backend? | Dados |
|---|---|---|---|
| Demo com os casos já analisados (PRJ01, PRJ02…), sem nada rodando | **static** | ❌ só o front | JSONs exportados do MongoDB |
| Aplicação completa: upload, análise, decisões, chatbot | **api** | ✅ uvicorn na 8000 | Tudo real, no banco |
| Demonstração fictícia de design (400 projetos fake) | **mock** (default) | ❌ | Em memória |

## Pastas (worktrees)

Este repo usa git worktrees — cada branch tem sua pasta:

```
~/personal/sts-hackathon-repos/
├── feature-front-static-data/      → backend  (branch feature/front-static-data)
├── feature-frontend-static/        → frontend (branch feature/frontend-static-provider)
├── feature-backend-merge/           → backend original (branch feature/backend-merge)
└── feature-models-and-modules/      → versão antiga
```

> No texto abaixo: `BACKEND` = `~/personal/sts-hackathon-repos/feature-front-static-data/backend`
> e `FRONTEND` = `~/personal/sts-hackathon-repos/feature-frontend-static/frontend`.

---

## 0) Pré-requisitos (uma vez)

```bash
# MongoDB (docker compose na raiz do worktree do backend)
cd ~/personal/sts-hackathon-repos/feature-front-static-data
docker compose up -d mongo

# backend: ambiente + .env
cd backend
cp .env.example .env        # e edite OLLAMA_API_KEY, OLLAMA_MODEL etc.
uv sync

# frontend: dependências
cd ~/personal/sts-hackathon-repos/feature-frontend-static/frontend
npm install
```

Senhas dos analistas de demonstração (seeds criados no 1º startup do backend):
`user1@sts.com` … `user5@sts.com`, senha `senha12345` (configurável em `SEED_PASSWORD`).

---

## 1) Modo STATIC — front sozinho sobre os dados reais exportados

O front carrega um JSON por rota, extraído **direto do MongoDB** (os casos já
analisados pelo pipeline). Sem backend, sem LLM, funciona offline.

**1.1. Gerar o export** (sempre que rodar novas análises no banco):

```bash
cd BACKEND
uv run backend-export-frontend --include-benchmark \
  --out /home/jvbarr/personal/sts-hackathon-repos/feature-frontend-static/frontend/static-api
```

- `--include-benchmark` traz os casos das rodadas de benchmark (é onde vivem
  PRJ01/PRJ02 — sem a flag eles ficam ocultos, como na rota real).
- `--owner <id>` / `--project <id>` filtram; sem flags exporta tudo.
- A saída é confidencial (trechos do pacote): a pasta `static-api/` é gitignored.

**1.2. Subir o front:**

```bash
cd FRONTEND
VITE_DATA_SOURCE=static npm run dev
```

**1.3. Usar:** abra http://localhost:5173 — F12 → `localStorage.clear()` → F5 →
login **Analista 1** (`user1@sts.com`), **qualquer senha** (login é mock, lê
`users.json` do export). A lista mostra PRJ01, PRJ02 e PRJ90; "Abrir análise"
carrega a árvore, o grafo de evidências e o parecer reais do pipeline.

**Dica:** para não depender da env no comando, crie `FRONTEND/.env` (gitignored):

```
VITE_DATA_SOURCE=static
VITE_STATIC_API_DIR=/static-api
```

Aí basta `npm run dev` — sempre sobe no modo demo.

---

## 2) Modo API — aplicação completa integrada ao backend

Tudo real: login com JWT, upload de pacote (dispara o pipeline), árvore/gráfo
de evidências, decisões, contestações, reanálise e chatbot. Se o backend cair,
o front degrada para os mocks automaticamente (a demo nunca quebra).

**2.1. Subir o backend** (terminal 1):

```bash
cd BACKEND
uv run backend          # uvicorn com reload em http://127.0.0.1:8000 (docs em /docs)
```

**2.2. Subir o front** (terminal 2):

```bash
cd FRONTEND
VITE_DATA_SOURCE=api VITE_API_URL=http://127.0.0.1:8000 npm run dev
```

⚠️ **Portas fixas:** o front TEM que estar na `5173` (o CORS do backend aceita
apenas `http://localhost:5173` — configurável em `CORS_ORIGINS` no `.env`).

**2.3. Usar:** login `user1@sts.com` / `senha12345` (verificação real de senha).
"Novo projeto" faz o upload multipart real → o pipeline roda em background →
o projeto aparece como "Processando" e a análise abre quando conclui.

> O pipeline usa LLM em nuvem (Ollama cloud): precisa de internet e de
> `OLLAMA_API_KEY` no `.env`. Uma análise completa leva ~4–6 min.

---

## 3) Modo MOCK — dados fictícios (default)

Nenhum backend, nenhum export. ~400 projetos fictícios gerados em memória,
login com qualquer analista fictício. É o modo de design/apresentação da UI.

```bash
cd FRONTEND
npm run dev             # sem VITE_DATA_SOURCE → mock
```

Login: qualquer analista listado (ana@exemplo.com…), qualquer senha.
`resetMockData()` no console do navegador volta aos dados iniciais.

---

## 4) Backend sozinho (API direto, sem front)

Útil para testar o pipeline, rodar a entrega dos 20 casos, benchmarks:

```bash
cd BACKEND
docker compose up -d mongo      # na raiz do worktree
uv run backend                  # API em http://127.0.0.1:8000/docs

# analisar todos os casos da pasta oficial como lote
uv run backend-import "<PACKAGE_DIR>/01_projetos/01_historico"

# benchmark dos casos (métricas: acurácia, tempo, tokens)
uv run backend-benchmark --projects PRJ01,PRJ02

# entrega dos 20 casos (pareceres, CSVs, JSONs) — pasta FORA do repo
uv run backend-entrega run [--resume <id>] [--yes]
uv run backend-entrega export <benchmark_id> --out ~/Downloads/entrega

# checagens determinísticas sobre análises salvas (zero tokens)
uv run backend-checks <benchmark_id>
```

## Testes

```bash
# backend (precisa do Mongo no ar)
cd BACKEND && uv run pytest                 # unit + api (362 testes)
uv run pytest -m live                       # opt-in: e2e com Ollama real

# frontend
cd FRONTEND && npm test                     # vitest (90 testes)
npm run lint                                # oxlint
npm run build                               # tsc -b && vite build
```

## Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| Lista vazia no static | Export antigo ou sem `--include-benchmark` | Regenerar o export (passo 1.1) |
| "Não é possível logar" no static | Sessão antiga no localStorage | F12 → `localStorage.clear()` → F5 |
| Login errado no api | Senha real é exigida | `senha12345` (ou `SEED_PASSWORD` do `.env`) |
| Erro de CORS no api | Front fora da porta 5173 | Subir o front na 5173 ou ajustar `CORS_ORIGINS` |
| Projeto travado em "Processando" | Pipeline usa LLM em nuvem | Conferir `OLLAMA_API_KEY` e internet; ver estágios em `GET /analyses/{id}/status` |
| Vite abriu na 5174/5175 | Porta 5173 já ocupada por outro dev server | Fechar o server antigo (Ctrl+C) e rodar de novo |
| Mongo não sobe | Imagem `mongo:8` ausente | `docker pull mongo:8` antes do `docker compose up` |

## Resumo dos modos em uma linha

```bash
npm run dev                                   # mock  (fictício, default)
VITE_DATA_SOURCE=static npm run dev            # static (dados reais exportados do Mongo)
VITE_DATA_SOURCE=api npm run dev              # api    (backend de verdade; suba o uvicorn antes)
```