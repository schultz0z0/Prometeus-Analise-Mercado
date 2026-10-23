# Multi-stage Dockerfile endurecido para produção do Prometeus
# -------------------------------------------------------------
# Estágio 1: Builder com dependências e compilação
# -------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /build/
COPY src/ /build/src/
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e ".[dev]"

# -------------------------------------------------------------
# Estágio 2: Imagem final mínima e segura (Non-root user)
# -------------------------------------------------------------
FROM python:3.11-slim AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src

WORKDIR /app

# Instala apenas dependências mínimas de runtime (libpq5 para postgres e curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário sem privilégios de root (princípio do menor privilégio)
RUN groupadd -g 10001 prometeus && \
    useradd -u 10001 -g prometeus -s /bin/sh -m prometeus

# Copia ambiente virtual compilado do builder
COPY --from=builder /opt/venv /opt/venv

# Copia código da aplicação com propriedade do usuário não-root
COPY --chown=prometeus:prometeus src/ /app/src/
COPY --chown=prometeus:prometeus web/ /app/web/
COPY --chown=prometeus:prometeus config/ /app/config/
COPY --chown=prometeus:prometeus migrations/ /app/migrations/
COPY --chown=prometeus:prometeus alembic.ini /app/alembic.ini
COPY --chown=prometeus:prometeus scripts/ /app/scripts/
COPY --chown=prometeus:prometeus web/ /app/web/
COPY --chown=prometeus:prometeus deploy/docker/docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

USER prometeus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "prometeus.entrypoints.rest.app:app", "--host", "0.0.0.0", "--port", "8000"]
