# Fase 01 — Fundação do serviço

## Objetivo

Criar uma aplicação mínima executável com domínio, persistência, fila, configuração, CLI, CI e telemetria, sem integração real.

## Dependências

Nenhuma dependência externa. Pode ser executada em paralelo com a [Fase 00](phase-00-validation.md); ver [Dependências e paralelismo](README.md#dependências-e-paralelismo).

## Gate de release relacionado

[Gate A — Foundation ready](../roadmap/release-gates.md#gate-a--foundation-ready).

## Arquivos principais previstos

- `pyproject.toml` e lockfile
- `compose.yaml` (raiz, desenvolvimento local)
- `Dockerfile`
- `.github/workflows/ci.yaml`
- `alembic.ini` e `migrations/versions/*_create_analysis_tables.py`
- `src/prometeus/__init__.py`
- `src/prometeus/domain/analyses.py`
- `src/prometeus/domain/configuration.py`
- `src/prometeus/application/create_analysis.py`
- `src/prometeus/infrastructure/db/`
- `src/prometeus/entrypoints/rest/app.py`
- `src/prometeus/entrypoints/cli/main.py`
- `src/prometeus/workers/tasks.py`
- `tests/unit/test_package.py`
- `tests/unit/domain/test_analysis_state.py`
- `tests/unit/domain/test_configuration.py`
- `tests/integration/test_analysis_repository.py`
- `tests/contract/api/test_create_analysis.py`
- `tests/e2e/test_foundation_flow.py`

## Tarefas

1. Inicializar pacote `prometeus` em Python 3.12 com Ruff, mypy e pytest. Escolher gerenciador de dependências com lockfile (ex.: uv) e registrar a escolha no relatório.
2. Escrever testes de transição de estados conforme [ADR-0005](../architecture/adr/0005-status-vs-recommendation.md) e fazê-los falhar.
3. Implementar a máquina de estados de `status` e os invariantes do ADR-0005; `recommendation` existe como campo nulo.
4. Implementar carregamento e validação de configuração (tenant, scoring profile, env), incluindo pesos somando 1,0, pilares obrigatórios existentes e proibição de `jev-latest` em produção.
5. Modelar tabelas `analysis`, `analysis_step`, `config_snapshot` e `audit_event`.
6. Criar migrations Alembic e testar upgrade/downgrade.
7. Criar `POST /v1/analyses` com `Idempotency-Key`, resposta 202 e teste contratual.
8. Configurar Celery/Redis e job fictício retomável com checkpoint por step.
9. Adicionar `/health/live` e `/health/ready`.
10. Adicionar logs JSON estruturados, correlation IDs, redação de segredos e métricas básicas.
11. Criar CLI operacional mínima: `prometeus config validate` e `prometeus analyses create --file <proposal.json>`.
12. Criar workflow de CI no GitHub Actions executando Ruff, format check, mypy, pytest e `python scripts/validate_docs.py`.
13. Criar Compose local e executar E2E do job fictício, incluindo restart do worker.

## Comandos de verificação planejados

```bash
docker compose up -d --build
docker compose exec api pytest -q
docker compose exec api ruff check .
docker compose exec api ruff format --check .
docker compose exec api mypy src
docker compose exec api prometeus config validate
curl -f http://localhost:8000/health/ready
python scripts/validate_docs.py
```

## Gate

Job criado uma vez por idempotency key, retomado após restart do worker, auditado sem segredo em logs, configuração inválida impede o startup e CI verde no GitHub Actions.
