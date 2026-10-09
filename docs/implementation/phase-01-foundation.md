# Fase 01 — Fundação do serviço

## Objetivo

Criar uma aplicação mínima executável com domínio, persistência, fila, configuração e telemetria, sem integração real.

## Arquivos principais previstos

- `pyproject.toml`
- `compose.yaml`
- `Dockerfile`
- `src/course_market_intelligence/domain/analyses.py`
- `src/course_market_intelligence/application/create_analysis.py`
- `src/course_market_intelligence/infrastructure/db/`
- `src/course_market_intelligence/entrypoints/rest/app.py`
- `src/course_market_intelligence/workers/tasks.py`
- `tests/unit/domain/test_analysis_state.py`
- `tests/integration/test_analysis_persistence.py`

## Tarefas

1. Inicializar pacote Python 3.12, Ruff, mypy e pytest.
2. Escrever testes de transição de estados e fazê-los falhar.
3. Implementar máquina de estados mínima e passar testes.
4. Modelar tabelas de analysis, step, config snapshot e audit event.
5. Criar migrations e testar upgrade/downgrade.
6. Criar `POST /v1/analyses` com idempotência e teste contratual.
7. Configurar Celery/Redis e job fictício retomável.
8. Adicionar health/readiness checks.
9. Adicionar logs estruturados, correlation IDs e métricas básicas.
10. Criar Compose local e executar E2E do job fictício.

## Comandos de verificação planejados

```bash
docker compose up -d --build
docker compose exec api pytest -q
docker compose exec api ruff check .
docker compose exec api mypy src
curl -f http://localhost:8000/health/ready
```

## Gate

Job criado uma vez para idempotency key, retomado após worker restart e auditado sem segredo em logs.
