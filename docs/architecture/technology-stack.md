# Stack tecnológica

## Escolhas baseline

| Área | Tecnologia | Motivo |
|---|---|---|
| Linguagem | Python 3.12 | Ecossistema de dados/IA e produtividade |
| API | FastAPI + Pydantic v2 | Contratos tipados e OpenAPI |
| Persistência | PostgreSQL + SQLAlchemy 2 | Transações, JSON e maturidade |
| Migração | Alembic | Integração natural com SQLAlchemy |
| Fila | Celery + Redis | Retries, workers e operação conhecida |
| HTTP | httpx | Clientes sync/async e testes |
| MCP | SDK Python oficial/FastMCP compatível | Servidor de tools para o chatbot |
| CLI | Typer + Rich | Operação e diagnóstico local |
| Qualidade | pytest, Ruff, mypy | Feedback rápido para equipe pequena |
| Telemetria | OpenTelemetry | Logs, métricas e traces portáveis |
| Runtime | Docker Compose | VPS e isolamento por instituição |

## Política de dependências

- Fixar versões em lockfile.
- Renovar deliberadamente, com testes.
- Evitar framework agentic central; o workflow pertence à aplicação.
- SDKs de fornecedores ficam atrás de portas.
- Não adicionar banco vetorial antes de provar necessidade e baseline superior ao PostgreSQL.

## Capacidade

O desenho prioriza operação por dois desenvolvedores com apoio de Codex/Claude Code. Microserviços, Kubernetes e múltiplos bancos ficam adiados até métricas demonstrarem necessidade.
