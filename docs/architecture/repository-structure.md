# Estrutura do repositório

```text
.
├── AGENTS.md / CLAUDE.md   # regras para agentes de desenvolvimento
├── CHANGELOG.md            # mudanças relevantes por fase
├── README.md
├── .env.example            # inventário de variáveis, sem segredos
├── pyproject.toml          # (Fase 01) pacote, Ruff, mypy, pytest
├── compose.yaml            # (Fase 01) stack local: api, worker, postgres, redis
├── Dockerfile              # (Fase 01) imagem única para api/mcp/worker/scheduler
├── .github/workflows/      # (Fase 01) CI no GitHub Actions
│
├── src/prometeus/
│   ├── domain/             # entidades, políticas, fórmulas e portas (sem frameworks)
│   ├── application/        # casos de uso e orquestração do workflow
│   ├── infrastructure/     # banco, filas, JEV, LLM, Apify, Google, CRM
│   ├── entrypoints/        # rest/, mcp/, cli/
│   ├── workers/            # tasks Celery e steps do workflow
│   └── observability/      # logs, métricas e traces
│
├── config/
│   ├── tenants/            # white-label sem segredos
│   ├── scoring/            # perfis imutáveis/versionados
│   ├── decision-packs/     # perguntas e rubricas JEV (Fase 03)
│   └── prompts/            # prompts e schemas da LLM (Fases 04 e 06)
│
├── migrations/             # Alembic (Fase 01)
├── deploy/docker/          # overlays e hardening de produção (Fase 08)
├── scripts/                # validação, avaliação, backtest, operação
├── skills/                 # skills de domínio versionadas
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── evaluation/
│   └── e2e/
│
└── docs/                   # fonte canônica do produto
```

Itens marcados com fase ainda não existem; são o destino planejado.

## Convenções

- Imports usam o namespace `prometeus` ([ADR-0006](adr/0006-python-namespace.md)).
- `compose.yaml` na raiz atende desenvolvimento local; ajustes de produção ficam em `deploy/docker/` como overlay, sem duplicar a stack.
- Um módulo de infraestrutura implementa uma porta de domínio/aplicação.
- Arquivos específicos da ENS vivem no adapter/configuração, nunca em regras genéricas.
- Testes espelham os módulos do código.
- Fixtures reais devem ser sanitizadas e aprovadas.
- Artefatos de avaliação não entram no Git quando contêm dados institucionais; `/artifacts/` na raiz é ignorado.
