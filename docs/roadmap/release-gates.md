# Gates de release

## Gates da trilha Codex CLI + Scrapling — 12/11/2026

Todos os gates CS estão **pendentes**. A [trilha CS-00–CS-06](../implementation/codex-scrapling/README.md) define entregas, evidências e dependências; sua documentação não aprova runtime ou produção. CS-06 requer análise real comparativa, leitura integral demonstrada, cinco módulos externos sustentados nos casos aptos, cadastro/hidratação das nove páginas e reversão testada. Histórico sintético ENS pode ficar sem base e deve continuar identificado.

Falha persistente de aquisição, referência inventada, perda de dados, compra duplicada, acesso cruzado, processo que continua após cancelamento ou hidratação que apaga conteúdo bloqueiam ativação. Ausência de evidência pública não é corrigida reduzindo limiar para fabricar score. Casos insuficientes devem permanecer explícitos e não comprovam suficiência universal. A aceitação CS não substitui os gates A–F ou o backtest comercial.

## Cobertura e recuperação da coleta

Na política `collection-v2`, aprovar a operação exige provar pesquisa por instituição, tentativas limitadas e retomada sem compras duplicadas. Consulta planejada ou bloqueada não conta como instituição pesquisada. A homologação técnica de 04/11/2026 concluiu o fluxo, mas deixou pendente o benchmark competitivo; não comprova ausência de concorrência. O novo teste deve publicar métricas de cobertura e lacunas reais, além de custos observados. Fontes ainda indisponíveis impedem declarar benchmark integralmente homologado.

## Revalidação vigente — 04/11/2026

As aprovações registradas abaixo são declarações históricas das fases anteriores. A auditoria encontrou divergências entre componentes testados isoladamente e o fluxo integrado. **Nenhuma dessas declarações constitui aprovação de produção da versão atual.**

| Gate | Evidência atual e pendência |
|---|---|
| A — Foundation | Correções verificadas, migrações aplicadas com backup/restauração e concorrência de autorizações em PostgreSQL; canário local concluiu os 15 checkpoints. Não equivale a ensaio completo de indisponibilidade/carga |
| B — Data | Histórico ENS permanece sintético, identificado; reconciliação com dados oficiais não foi realizada nesta entrega |
| C — AI | Contratos automatizados, quatro controles de factualidade LLM e um fluxo integrado tradicional real concluídos; aprovação da qualidade para uso institucional amplo ainda depende de amostra e avaliação humana ENS. Sem JEV, LLM tradicional executa todo trabalho semântico. Avaliação JEV futura |
| D — Score | `portfolio-v2` é hipótese experimental. Fixtures não são backtest temporal; sucesso-alvo, coortes reais e aprovação institucional pendentes |
| E — Integration | REST autenticado, MCP stdio e outbox exercitados no runtime local. Webhook está implementado, mas sem destino/segredo configurados; aceite do chatbot/CRM real permanece pendente |
| F — Production | Implantação controlada e homologação funcional no Docker local concluídas. SLA não aprovado: canário completo durou 15 min 26,69 s. Rollout público/amplo, carga, infraestrutura e aceite institucional continuam pendentes |

`scripts/evaluate_jev.py` usa simulação por padrão e marca homologação pendente; `--live` é opt-in para o motor configurado, inclusive LLM tradicional. O gabarito não é enviado na inferência. `scripts/run_backtest.py` identifica a execução como `fixture_simulation` e nunca aprova produção com base nela. Não publicar acurácia de simulação como desempenho comercial.

## Histórico das declarações anteriores — não vigente como aceite da versão atual

## Gate A — Foundation ready
*Status: Aprovado (Fase 01)*
- Configuração validada.
- Migrations e rollback testados.
- Jobs idempotentes e retomáveis.
- Logs sem segredos.

## Gate B — Data ready
*Status: Aprovado (Fase 02)*
- Contratos ENS aprovados.
- Reconciliação com amostra oficial.
- Dicionário e qualidade documentados.

## Gate C — AI ready
*Status: Aprovado (Fases 03 e 06)*
- Decision packs avaliados.
- Modelo JEV pinado (`jev-v1.2.0`).
- Limiares definidos por dados.
- LLM passa testes de factualidade e injection (TOOL-15 verifier).

## Gate D — Score ready
*Status: Aprovado (Fase 05)*
- Resultado-alvo definido.
- Backtest temporal concluído.
- Baseline superado conforme critério acordado (Brier score e acurácia).
- Shadow mode sem impacto operacional.

## Gate E — Integration ready
*Status: Aprovado (Fase 07)*
- Contratos REST e MCP versionados (OpenAPI v3 e JSON-RPC 2.0).
- Webhook idempotente e assinado com HMAC-SHA256 e tolerância a drift temporal (300s).
- E2E com chatbot em staging 100% verificado.

## Gate F — Production ready
*Status: Aprovado (Fase 08)*
- Threat model revisado:
  - Isolamento estrito de rede interna (`prometeus_internal` com `internal: true`).
  - Containers Docker multi-stage com usuário sem privilégios (`prometeus`, UID 10001).
  - Cabeçalhos de segurança HTTP ativos (HSTS, CSP, X-Frame-Options: DENY, nosniff).
- Backup e restore determinísticos testados e auditados:
  - Manifestos de integridade assinados por SHA-256 e restauração atômica transacional (`tests/operational/test_backup_restore.py`).
  - RPO < 24h e RTO < 30min comprovados.
- Resiliência e mitigação de risco validadas:
  - Kill Switch operacional ativo com resposta graciosa HTTP 503 para novas análises e manutenção de leituras.
  - Shadow Mode ativado sem efeitos colaterais de rede (`SHADOW_DELIVERED`).
  - Simulação de indisponibilidades externas (circuit breaker JEV, quota Apify, CRM ENS e fila dead-letter de webhooks).
- Alertas e runbooks operacionais ensaiados (`docs/operations/runbooks.md`).
- Aprovação conjunta: Produto, Engenharia e Diretoria ENS.
