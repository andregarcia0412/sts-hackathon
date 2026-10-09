# Backend — STS 2026 (Lei do Bem)

FastAPI + MongoDB service that analyses a project package against the five Frascati criteria and
produces a traceable, defensible recommendation for the R&D analyst. The system suggests; the analyst
decides. Architecture, principles and conventions: [AGENTS.md](AGENTS.md).

## Run

```bash
docker compose up -d mongo          # from the repo root
cp .env.example .env                # set OLLAMA_API_KEY and OLLAMA_MODEL (per-role overrides optional)
uv sync
uv run backend                      # http://127.0.0.1:8000/docs
```

Switching models only touches `.env`: `OLLAMA_MODEL` is the default of every role and
`OLLAMA_MODEL_{EXTRACTION,DOC,SEARCH,JUDGE,REPORT,CHAT}` override one role each. Every analysis records
the model of each role, the prompt hashes, the catalog version and the sha256 of every file.

## Batch and calibration

```bash
uv run backend-import "$PACKAGE_DIR/01_projetos/01_historico"     # PRJ01–20, progress in the terminal
# download GET /batches/{id}/report.csv, then:
uv run backend-calibrate historicos_classificados.csv lote.csv     # class and state hits, confusion matrix
uv run backend-import "$PACKAGE_DIR/01_projetos/02_casos_para_analise"
```

## Tests

```bash
uv run pytest            # unit + API (needs Mongo; LLM and web are faked)
uv run pytest -m live    # opt-in: PRJ21 end to end with the real Ollama, reads backend/.env
```
