# Prometeus

**Inteligência para Produtos Educacionais**

Prometeus é um serviço headless de inteligência para avaliar a viabilidade de novos produtos educacionais. O produto combina dados históricos da instituição, sinais externos de mercado, decisões tipadas do JEV, cálculo determinístico de score e síntese por LLM generativa.

Produto desenvolvido e mantido pela **Agência Prometeus**.

O primeiro deployment será dedicado à ENS (Escola de Negócios e Seguros). O mesmo código-base poderá ser configurado e implantado separadamente para outras instituições.

## Estado atual

O sistema possui implementação funcional e testes automatizados. A revisão de 04/11/2026 corrige integridade de dossiês, economia, controle de acesso, concorrência, fila, MCP e recuperação; consulte o [plano](docs/plans/2026-11-04-audit-remediation.md) e o [guia operacional das correções](docs/operations/audit-remediation.md). A homologação manual com a ENS e a calibração comercial permanecem pendentes. O histórico sintético ENS é preservado para testes.

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

- Sem JEV, a LLM tradicional assume planejamento, julgamentos semânticos delimitados e redação, inclusive via ChatGPT OAuth. O modo híbrido explícito exige credencial JEV, conforme ADR-0008.
- Fórmulas, permissões e regras invariáveis são implementadas em código.
- A LLM generativa não altera scores nem evidências.
- Toda recomendação relevante deve ser rastreável até suas fontes.
- Cada instituição recebe deployment, banco, segredos e configuração isolados.
- Integrações externas são adaptadores substituíveis e nunca fatos presumidos.

## Operação

A stack usa Python, FastAPI, PostgreSQL, Redis, Celery, MCP stdio e Docker Compose. A interface e a API exigem credencial própria do Prometeus, independente do OAuth ChatGPT. Consulte [.env.example](.env.example), o [guia de acesso e migração](docs/operations/audit-remediation.md) e a [arquitetura de deployment](docs/architecture/deployment.md).
