# Índice da documentação

Esta pasta é a fonte canônica do produto. O PRD original na raiz é mantido como artefato de origem; decisões posteriores vivem aqui.

## Produto

- [PRD canônico](product/PRD.md)
- [Nome e identidade](product/brand-and-naming.md)
- [Manual e diretrizes de marca](product/brand-guidelines.md)
- [Design System Prometeus UI](product/design-system.md)
- [Visão e escopo](product/vision-and-scope.md)
- [Personas e Jobs to Be Done](product/personas-and-jtbd.md)
- [Casos de uso](product/use-cases.md)
- [Requisitos](product/requirements.md)
- [Glossário](product/glossary.md)

## Arquitetura

- [Visão do sistema](architecture/system-overview.md)
- [Fronteiras dos módulos](architecture/module-boundaries.md)
- [Fluxo de dados](architecture/data-flow.md)
- [Deployment](architecture/deployment.md)
- [Stack tecnológica](architecture/technology-stack.md)
- [Estrutura do repositório](architecture/repository-structure.md)
- [Registros de decisão](architecture/adr/README.md)

## Inteligência e scoring

- [Workflow do agente](agent/workflow.md)
- [Catálogo de ferramentas](agent/tools-catalog.md)
- [Contratos de decisão JEV](agent/jev-decision-contracts.md)
- [Política da LLM generativa](agent/llm-generation-policy.md)
- [Estratégia de skills](agent/skills-strategy.md)
- [Modelo de scoring](scoring/scoring-model.md)
- [Confiança e cobertura](scoring/confidence-and-coverage.md)
- [Calibração e backtest](scoring/calibration-and-backtest.md)

## Dados, integrações e segurança

- [Modelo canônico](data/canonical-model.md)
- [Evidências e proveniência](data/evidence-and-provenance.md)
- [Retenção e qualidade](data/retention-and-quality.md)
- [Adaptadores institucionais](integrations/institutional-adapters.md)
- [Fontes externas](integrations/external-sources.md)
- [REST, MCP e webhooks](integrations/rest-mcp-webhooks.md)
- [Exemplos de contratos](integrations/contracts-examples.md)
- [Segurança e LGPD](security/security-and-lgpd.md)
- [Modelo de ameaças](security/threat-model.md)

## Entrega

- [Configuração](operations/configuration.md)
- [Observabilidade](operations/observability.md)
- [Backup e recuperação](operations/backup-and-recovery.md)
- [Runbooks](operations/runbooks.md)
- [Implantação em staging e operação do piloto](operations/staging-and-pilot-deployment.md)
- [Onboarding institucional](operations/institutional-onboarding.md)
- [Estratégia de testes](testing/test-strategy.md)
- [Capacidade do time e processo](engineering/team-and-delivery.md)
- [Roadmap](roadmap/roadmap.md)
- [Gates de release](roadmap/release-gates.md)
- [Planos por fase](implementation/README.md)
- [Prompt reutilizável para executar uma fase](prompt-fase-template.md)
- [Relatórios de conclusão](implementation/reports/README.md)
- [Plano mestre de implementação](plans/2026-10-09-product-foundation.md)

## Convenções de status

- **DECIDIDO:** aprovado e obrigatório.
- **HIPÓTESE:** precisa de experimento ou dados.
- **DEPENDÊNCIA EXTERNA:** depende de acesso, contrato ou fornecedor.
- **VALIDADO:** possui evidência verificável e data da validação.
- **ADIADO:** fora da fase atual, mas preservado na visão.
