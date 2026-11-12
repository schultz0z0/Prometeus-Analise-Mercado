# Roadmap

O roadmap preserva a visão expandida e reduz risco por ordem de validação.

| Fase | Resultado | Gate principal |
|---|---|---|
| 00 — Validação | Premissas, contratos e dados conhecidos | ENS e fornecedores confirmados |
| 01 — Fundação | Serviço executável localmente | CI, estado, fila e observabilidade básicos |
| 02 — ENS | Histórico institucional normalizado | Reconciliação aprovada |
| 03 — JEV | Decision packs avaliados | Qualidade e confiança medidas |
| 04 — Mercado | Coleta externa com evidências | Cobertura, custo e termos aprovados |
| 05 — Scoring | Score reproduzível e calibrado | Backtest + shadow mode |
| 06 — Dossiê | Síntese factual e recomendações | Claims verificadas |
| 07 — Integração | REST, MCP e webhooks completos | E2E com chatbot |
| 08 — Piloto | Produção ENS operável | Segurança, restore e runbooks |
| 09 — White-label | Segunda instituição sem fork | Adapter/config onboarding comprovado |

## Evolução de execução — Codex CLI + Scrapling (12/11/2026)

Trilha **planejada, ainda não implementada**, complementar às fases 00–09. O [índice CS](../implementation/codex-scrapling/README.md) e o [plano de tarefas](../plans/2026-11-12-codex-cli-scrapling-implementation.md) são as referências de desenvolvimento.

| Marco | Entrega | Gate |
|---|---|---|
| CS-00 | Baseline e correção da reconciliação Google Search | Causa reproduzida e datasets existentes recuperados sem nova compra |
| CS-01 | Contratos neutros e roteamento | Providers reais, recuperação e snapshots compatíveis |
| CS-02 | Runner Codex CLI | Inferência real, schemas, sessões e cancelamento comprovados |
| CS-03 | Scrapling HTTP/browser | Conteúdo adquirido preservado, higienizado e lido integralmente |
| CS-04 | Pesquisa assistida com MCP/skills | Trajetória real auditável e sem duplicação de operações |
| CS-05 | Síntese e cadastro no CMS | Nove páginas verificadas e preservadas após reload |
| CS-06 | Homologação e substituição gradual | Comparação real, cinco módulos externos nos casos aptos e reversão testada |

Dependências: CS-00 → CS-01 → (CS-02 e CS-03) → CS-04 → CS-05 → CS-06. Sem prazo prometido antes dos spikes. Codex assume trabalhos semânticos no fluxo existente, Scrapling assume páginas web, Apify continua com fontes especializadas; nenhuma alteração automática em análises em curso. Firecrawl não é dependência inicial.

## Princípio de avanço das fases

Uma fase pode desenvolver mocks da seguinte, mas não declarar capacidade concluída sem cumprir seu gate. Integrações externas e scores permanecem hipóteses até evidência.

## Marcos de produto

- M1: proposta entra e job é rastreável.
- M2: comparáveis históricos da ENS reconciliados.
- M3: JEV classifica com performance conhecida.
- M4: fontes externas sustentáveis e auditáveis.
- M5: score supera baseline em backtest.
- M6: dossiê factual consumido pelo chatbot.
- M7: shadow mode e piloto controlado.
- M8: onboarding de nova instituição sem alterar core.
