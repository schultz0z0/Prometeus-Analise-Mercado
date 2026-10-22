# Planos de implementação

Os planos definem a evolução faseada do produto. Cada fase possui escopo delimitado, dependências, arquivos previstos, comandos de verificação e gate objetivo.

- [Fase 00 — Validação de premissas e contratos](phase-00-validation.md)
- [Fase 01 — Fundação do serviço](phase-01-foundation.md)
- [Fase 02 — Adaptador institucional ENS](phase-02-ens-adapter.md)
- [Fase 03 — Integração JEV e decision packs](phase-03-jev.md)
- [Fase 04 — Dados externos de mercado](phase-04-market-data.md)
- [Fase 05 — Motor de scoring e calibração](phase-05-scoring.md)
- [Fase 06 — Dossiê e síntese generativa](phase-06-dossier.md)
- [Fase 07 — REST, MCP, webhook e chatbot](phase-07-integration.md)
- [Fase 08 — Produção e piloto ENS](phase-08-production-pilot.md)
- [Fase 09 — Expansão white-label](phase-09-whitelabel.md)

## Dependências e paralelismo

```text
[Fase 00: Validação de premissas / spike] ──────────────┐
                                                       ▼
[Fase 01: Fundação local (CI, DB, fila, estado)] ──► [Fases 02, 03, 04] ──► [Fase 05] ──► [Fase 06] ──► [Fase 07] ──► [Fase 08] ──► [Fase 09]
```

- **Paralelismo inicial:** a Fase 00 (validação de APIs externas, contratos da ENS e spike do JEV) e a Fase 01 (fundação interna em código: máquina de estados, persistência, fila Celery/Redis, CLI e CI) podem ser desenvolvidas em paralelo porque a Fase 01 não consome nenhuma API externa.
- **Bloqueio obrigatório:** as Fases 02 (adaptador ENS), 03 (JEV) e 04 (coleta externa) estão bloqueadas até que a Fase 00 obtenha aprovação do seu gate (acessos, OpenAPI da ENS e feasibility comprovados).
- **Sequência posterior:** as Fases 05 a 09 seguem estritamente em ordem, cada uma exigindo o cumprimento do gate anterior.

## Etapas do workflow por fase

Mapeamento entre as 15 etapas do [workflow do agente](../agent/workflow.md) e as fases de implementação:

| Etapa | Nome | Implementada na | Descrição |
|---|---|---|---|
| 01 | Contexto institucional | Fase 01 | Carregamento e congelamento da configuração do tenant |
| 02 | Intake | Fase 01 / Fase 07 | Validação de schema da proposta recebida via API/CLI |
| 03 | Readiness | Fase 01 (regras) / Fase 03 (JEV) | Gatekeeper semântico de completude da proposta |
| 04 | Keywords | Fase 04 | Candidatos via LLM (`TOOL-01`) + ranking via JEV (`TOOL-02`) |
| 05 | Research plan | Fase 04 | Seleção de fontes, orçamento e chaves de cache |
| 06 | Histórico interno | Fase 02 | Adaptador CRM da ENS (`TOOL-03`, `TOOL-04`) |
| 07 | Mercado | Fase 04 | Conectores externos Apify, Ads, Trends e YouTube |
| 08 | Higienização | Fase 04 | Deduplicação, proveniência e isolamento de conteúdo |
| 09 | Julgamentos semânticos | Fase 03 | Decision packs JEV (dores, aderência de ementa) |
| 10 | Scoring | Fase 05 | Cálculo determinístico de Viability, Confidence e Coverage |
| 11 | Quality gate | Fase 05 | Avaliação de limites e definição da `recommendation` |
| 12 | Síntese | Fase 06 | Redação consultiva do dossiê a partir de fatos aprovados |
| 13 | Verificação | Fase 06 | Validação de claims contra evidências estruturadas |
| 14 | Entrega | Fase 07 | Persistência final, export e disparo de webhook assinado |
| 15 | Feedback | Fase 07 | Registro de decisão humana e outcomes para backtest |

## Execução e evidências

- [Prompt reutilizável por fase](../prompt-fase-template.md)
- [Relatórios de conclusão](reports/README.md)
- [Template de relatório](reports/_phase-report-template.md)

## Convenção

Cada entrega deve passar por teste, revisão e atualização documental. Commits devem ser pequenos e atômicos; nenhuma fase deve ser entregue em um único commit opaco.
