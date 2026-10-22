# Pacote da aplicação

Este é o namespace técnico planejado do **Prometeus — Inteligência para Produtos Educacionais**. Estrutura planejada; a implementação ainda não começou.

- `domain/`: regras puras e contratos.
- `application/`: casos de uso e orquestração.
- `infrastructure/`: adapters de fornecedores e persistência.
- `entrypoints/`: REST, MCP, CLI e worker.
- `workers/`: steps e consumers assíncronos.
- `observability/`: logs, métricas e tracing.
