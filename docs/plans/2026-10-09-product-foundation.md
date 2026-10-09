# Prometeus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir um serviço headless, auditável e white-label para análise de viabilidade de produtos educacionais, começando pela ENS.

**Architecture:** Monólito modular Python com entrypoints REST, MCP e CLI, processamento Celery/Redis e persistência PostgreSQL. JEV realiza decisões atômicas; código calcula score e controla estado; uma LLM generativa produz o dossiê a partir de fatos aprovados.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Celery, httpx, TypeSafe SDK/HTTP, MCP Python SDK, pytest, Ruff, mypy, OpenTelemetry e Docker Compose.

---

## Pré-condições

Execute primeiro a [Fase 00](../implementation/phase-00-validation.md). Não crie integrações reais com schemas inventados.

### Task 1: Inicializar qualidade e pacote

**Files:**
- Create: `pyproject.toml`
- Create: `src/course_market_intelligence/__init__.py`
- Create: `tests/unit/test_package.py`

**Steps:**

1. Escrever um teste que importa o pacote e falha.
2. Executar `pytest tests/unit/test_package.py -v` e confirmar falha.
3. Criar o pacote mínimo e configurações de Ruff/mypy/pytest.
4. Executar `ruff check .`, `mypy src` e `pytest -q`.
5. Commit: `chore: initialize python project quality gates`.

### Task 2: Implementar máquina de estados

**Files:**
- Create: `src/course_market_intelligence/domain/analyses.py`
- Create: `tests/unit/domain/test_analysis_state.py`

**Steps:**

1. Escrever casos de transições válidas e inválidas.
2. Confirmar falha porque o modelo não existe.
3. Implementar enum, política de transição e erros de domínio.
4. Rodar o teste isolado e depois toda a suíte.
5. Commit: `feat: add analysis state machine`.

### Task 3: Adicionar persistência e migrations

**Files:**
- Create: `src/course_market_intelligence/infrastructure/db/models.py`
- Create: `src/course_market_intelligence/infrastructure/db/repositories.py`
- Create: `alembic.ini`
- Create: `migrations/versions/*_create_analysis_tables.py`
- Create: `tests/integration/test_analysis_repository.py`

**Steps:**

1. Escrever teste de persistência, idempotência e snapshot.
2. Executar e confirmar falha.
3. Implementar models, repository e migration mínima.
4. Testar upgrade, downgrade e suíte.
5. Commit: `feat: persist analyses and audit events`.

### Task 4: Criar API e fila mínimas

**Files:**
- Create: `src/course_market_intelligence/entrypoints/rest/app.py`
- Create: `src/course_market_intelligence/application/create_analysis.py`
- Create: `src/course_market_intelligence/workers/tasks.py`
- Create: `tests/contract/api/test_create_analysis.py`

**Steps:**

1. Escrever teste para `POST /v1/analyses` e idempotency key.
2. Confirmar falha.
3. Implementar caso de uso, endpoint e enfileiramento fictício.
4. Confirmar resposta 202 e job único.
5. Commit: `feat: accept and queue course analyses`.

### Task 5: Containerizar foundation

**Files:**
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `tests/e2e/test_foundation_flow.py`

**Steps:**

1. Criar E2E de criação e conclusão de job fictício.
2. Subir stack e observar falha esperada antes da configuração.
3. Adicionar API, worker, PostgreSQL e Redis com health checks.
4. Executar `docker compose up -d --build` e testes.
5. Commit: `build: add local docker stack`.

## Continuação obrigatória

Após a foundation, executar os planos detalhados em `docs/implementation/phase-02-ens-adapter.md` até `phase-09-whitelabel.md`, respeitando cada gate. Cada tarefa deve seguir red-green-refactor, revisão e commit pequeno.

## Verificação final do plano

```bash
ruff check .
ruff format --check .
mypy src
pytest -q
docker compose config --quiet
```

O desenvolvimento só está completo quando os Gates A–F de `docs/roadmap/release-gates.md` possuem evidência registrada.
