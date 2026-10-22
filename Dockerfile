# Multi-stage Dockerfile para o monólito Prometeus
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONPATH=/app/src

WORKDIR /app

# Instalação de utilitários e gerenciador uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Instala dependências a partir do pyproject.toml e uv.lock
COPY pyproject.toml uv.lock README.md /app/
RUN uv pip install --system -e ".[dev]"

# Copia código fonte, migrações e configurações
COPY src/ /app/src/
COPY config/ /app/config/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY scripts/ /app/scripts/
COPY web/ /app/web/

EXPOSE 8000

CMD ["uvicorn", "prometeus.entrypoints.rest.app:app", "--host", "0.0.0.0", "--port", "8000"]
