# Prometeus

**Inteligência para Produtos Educacionais**

Prometeus é um serviço headless de inteligência para avaliar a viabilidade de novos produtos educacionais. O produto combina dados históricos da instituição, sinais externos de mercado, decisões tipadas do JEV, cálculo determinístico de score e síntese por LLM generativa.

O primeiro deployment será dedicado à ENS (Escola de Negócios e Seguros). O mesmo código-base poderá ser configurado e implantado separadamente para outras instituições.

## Estado atual

O projeto está na fase de documentação e validação. Ainda não existe implementação funcional. Não confunda a estrutura de diretórios com funcionalidades concluídas.

## Ordem de leitura

1. [Índice da documentação](docs/README.md)
2. [PRD canônico](docs/product/PRD.md)
3. [Nome e identidade do produto](docs/product/brand-and-naming.md)
4. [Visão de arquitetura](docs/architecture/system-overview.md)
5. [Workflow do agente](docs/agent/workflow.md)
6. [Modelo de scoring](docs/scoring/scoring-model.md)
7. [Roadmap](docs/roadmap/roadmap.md)
8. [Planos de implementação](docs/implementation/README.md)

## Princípios

- JEV é obrigatório para julgamentos semânticos delimitados.
- Fórmulas, permissões e regras invariáveis são implementadas em código.
- A LLM generativa não altera scores nem evidências.
- Toda recomendação relevante deve ser rastreável até suas fontes.
- Cada instituição recebe deployment, banco, segredos e configuração isolados.
- Integrações externas são adaptadores substituíveis e nunca fatos presumidos.

## Desenvolvimento futuro

A stack planejada é Python, FastAPI, PostgreSQL, Redis, workers assíncronos, MCP e Docker Compose. Consulte [.env.example](.env.example) e a [arquitetura de deployment](docs/architecture/deployment.md).
