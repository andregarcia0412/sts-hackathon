# API (FastAPI + uvicorn). Deploy with backend/ as the build context (root directory)
FROM ghcr.io/astral-sh/uv:0.12.23-python3.13-trixie-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code changes do not reinstall them
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Code, catalog and normative PDFs (data/normas, indexed for the chatbot on the first start)
COPY README.md ./
COPY src ./src
COPY data ./data
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# PORT is set by the hosting platform (8000 locally); trust the platform proxy's X-Forwarded-* headers
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
