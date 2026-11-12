# Evolução Codex CLI + Scrapling

**Atualizado:** 12/11/2026. **Estado:** CS-00 em implementação parcial; demais fases planejadas. O usuário autorizou iniciar CS-00 após o planejamento; isso não ativa Codex CLI ou Scrapling.

Esta trilha preserva as fases históricas 00–09 do produto. Seus identificadores **CS-00 a CS-06** representam a substituição progressiva da execução de IA e do crawler, mantendo os 15 checkpoints, os seis módulos de viabilidade e o CMS de nove páginas.

## Documentos de execução

- [Avaliação do código e arquitetura de partida](../../plans/2026-11-11-codex-cli-scrapling-assessment.md).
- [ADR-0012 — Direção arquitetural](../../architecture/adr/0012-codex-cli-and-provider-neutral-collection.md).
- [Plano de implementação em tarefas](../../plans/2026-11-12-codex-cli-scrapling-implementation.md).
- [Contratos propostos](../../integrations/codex-scrapling-contracts.md).
- [Configuração, migração e reversão planejadas](../../operations/codex-scrapling-rollout.md).

## Fases e dependências

| Fase | Resultado | Depende de | Status |
|---|---|---|---|
| [CS-00 — Baseline e reconciliação](phase-cs-00-baseline.md) | Causa do erro atual reproduzida; dados existentes recuperáveis | Código vigente | Parcial; causa original pendente |
| [CS-01 — Contratos e roteamento](phase-cs-01-contracts.md) | Separação entre capability, provider e artefato | CS-00 | Planejada |
| [CS-02 — Runtime Codex](phase-cs-02-codex-runtime.md) | CLI real com configuração e sessões isoladas | CS-01 | Planejada |
| [CS-03 — Aquisição Scrapling](phase-cs-03-scrapling.md) | HTTP/browser com retenção e retomada | CS-01 | Planejada |
| [CS-04 — Pesquisa assistida](phase-cs-04-research-tools.md) | Codex solicita ações por ferramentas auditadas | CS-02 + CS-03 | Planejada |
| [CS-05 — Dossiê e CMS](phase-cs-05-dossier-cms.md) | Conteúdo do Codex chega às nove páginas verificadas | CS-04 | Planejada |
| [CS-06 — Homologação e substituição](phase-cs-06-homologation.md) | Ativação explícita para novas análises com reversão comprovada | CS-05 | Planejada |

CS-02 e CS-03 podem ser desenvolvidas independentemente após os contratos, mas integram a mesma versão somente em CS-04. Documentar paralelismo não instrui o executor a criar subagentes automaticamente. A migração nunca deve mudar o provider de uma análise já em execução.

## Divisão de responsabilidades

- **Prometeus:** estado, autorização, fila/lease, tentativas, acervo, deduplicação, fórmulas, scoring, gates, persistência e publicação.
- **Codex CLI:** entendimento, planejamento, julgamentos, leitura analítica, aprofundamento por ferramentas, síntese e revisão dentro de cada etapa autorizada.
- **Apify:** descoberta e fontes especializadas homologadas, incluindo Google Search, Trends, anúncios, vagas e fontes sociais.
- **Scrapling:** provider proposto para `web_crawler`, com HTTP e browser para páginas acadêmicas e seus documentos relevantes.
- **CMS:** apresentação do contrato canônico verificado, preservando revisões humanas.

Firecrawl é alternativa futura, sem dependência ou instalação nesta trilha. Hospedar Codex em um Actor Apify próprio não faz parte do desenho inicial.

## Critério de conclusão

Cada fase exige testes relevantes e relatório com commit, versões, procedimentos, resultados e limites. A conclusão da trilha exige coletar, analisar e exibir evidências suficientes para os cinco módulos externos em amostra real; o histórico sintético ENS permanece identificado e pode ficar sem base. Ausência de evidência não autoriza fabricar nota. Conclusões desfavoráveis têm o mesmo valor de homologação que favoráveis, desde que sustentadas.

Sucesso de software não demonstra calibração comercial do perfil de scoring, nem disponibilidade universal de dados. Economia em Apify e ganho de qualidade são hipóteses a medir, não critérios já cumpridos.
