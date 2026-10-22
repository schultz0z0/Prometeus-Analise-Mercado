# Pacote da aplicação

Este é o namespace técnico do **Prometeus — Inteligência para Produtos Educacionais** ([ADR-0006](../../docs/architecture/adr/0006-python-namespace.md)). Estrutura planejada para desenvolvimento a partir da Fase 01.

- `domain/`: regras puras e contratos.
- `application/`: casos de uso e orquestração.
- `infrastructure/`: adapters de fornecedores e persistência.
- `entrypoints/`: REST, MCP, CLI e worker.
- `workers/`: steps e consumers assíncronos.
- `observability/`: logs, métricas e tracing.
