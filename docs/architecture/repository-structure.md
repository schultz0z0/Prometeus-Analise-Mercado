# Estrutura do repositório

```text
src/course_market_intelligence/
├── domain/          # entidades, políticas, fórmulas e portas
├── application/     # casos de uso e orquestração
├── infrastructure/  # banco, filas e fornecedores
├── entrypoints/     # REST, MCP e CLI
├── workers/         # consumers e steps
└── observability/   # logs, métricas e traces

config/
├── tenants/         # white-label sem segredos
├── scoring/         # perfis imutáveis/versionados
├── decision-packs/  # perguntas e rubricas JEV
└── prompts/         # prompts e schemas da LLM

tests/
├── unit/
├── integration/
├── contract/
├── evaluation/
└── e2e/
```

## Convenções futuras

- Um módulo de infraestrutura implementa uma porta de domínio/aplicação.
- Arquivos específicos da ENS vivem no adapter/configuração, nunca em regras genéricas.
- Testes espelham os módulos do código.
- Fixtures reais devem ser sanitizadas e aprovadas.
- Artefatos de avaliação não entram no Git quando contêm dados institucionais.
