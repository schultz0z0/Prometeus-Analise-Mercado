# Correções da auditoria sistêmica — 04/11/2026

**Produto:** Prometeus — Inteligência para Produtos Educacionais.
**Mantenedora:** Agência Prometeus. **Branch:** `codex/audit-remediation`.
**Status:** correções A01–A13 implementadas e verificadas no workspace; homologação manual pendente. Não houve implantação no stack em uso.

Este relatório complementa a [auditoria original](system-audit-2026-11-04.md) e o [plano autorizado](../../plans/2026-11-04-audit-remediation.md). Testes automatizados não equivalem a garantia de ausência de defeitos, calibração comercial ou aprovação de produção.

## Rastreabilidade dos achados

| Achado | Correção entregue | Evidência automatizada principal |
|---|---|---|
| A01 — conteúdo acrescentado sem evidência | Removidos defaults de preço, custos, personas, currículo, SWOT e conclusões de mercado. Contrato de apresentação 2; frontend desconsidera enriquecimentos legados inseguros. Consulta planejada não é apresentada como executada. | `test_verified_presentation.py`, `test_synthesize_dossier_integration.py`, `test_dossier_view_rendering.py` |
| A02 — economia impossível | Serviço canônico Decimal, premissas explícitas com proveniência, capacidade e contribuição validadas; ausência gera `not_calculable`. Cenários e rateio mensal conciliam centavos. | `test_verified_presentation.py` |
| A03 — ausência de autenticação/autorização | Identidades por papel/instituição, Bearer ou sessão HttpOnly, controle de origem, validação de todos os tenants recebidos e proprietário persistido. Decisor vem da identidade autenticada. Compose em loopback por padrão. | `test_access_control.py` |
| A04 — cancelamento sobrescrito | Revisão otimista do agregado, consultas de estado antes/depois de checkpoints e antes de julgamentos/coletas. Lease exclusivo, heartbeat e interrupção ao perder posse. Aborto de Actor quando possível. | `test_workflow_reliability.py` |
| A05 — publicação antes de commit | Outbox transacional `analysis_jobs`, publicação após commit e reconciliação periódica com backoff. Estado remoto indeterminado bloqueia em `IN_DOUBT`, sem repetir compra automaticamente. | `test_workflow_reliability.py`, `test_collection_integrity.py`, validação PostgreSQL |
| A06 — reanálise/idempotência/snapshot | Caso de uso compartilhado, chave única por instituição e novo snapshot por reanálise. Chave original continua reservada à criação original. | `test_create_analysis.py`, `test_rest_endpoints.py`, `test_workflow_reliability.py`, validação PostgreSQL |
| A07 — sessão concorrente em keywords | Julgamentos persistidos em sequência, com análise/instituição; erro de fornecedor não vira irrelevância semântica. | `test_workflow_reliability.py` |
| A08 — MCP incompleto | Entrada stdio executável, negociação JSON-RPC, notificações sem resposta, identidade local institucional e criação canônica com outbox. | `test_mcp_runtime.py`, `test_mcp_stdio.py`, `test_mcp_tools.py` |
| A09 — webhook desconectado | Eventos terminais na transação do estado, assinatura com segredo configurado, retries, deduplicação e dead-letter. Sem segredo/destino, usa polling. | `test_workflow_events.py`, contratos existentes do dispatcher |
| A10 — backup parcial | Formato 2 cobre as 18 tabelas mapeadas em ordem de FKs; valida cobertura, contagens e checksum antes da limpeza. PostgreSQL usa snapshot consistente. | `test_backup_restore.py`, roundtrip PostgreSQL |
| A11 — avaliação circular e gates indevidos | Gabaritos não chegam à inferência. Simulação não aprova gates; fornecedor real exige opt-in. Gates comerciais e de produção permanecem pendentes. | `test_release_evaluation_integrity.py` |
| A12 — XSS em metadados | Escape dos campos controlados no portfólio e CSP sem scripts inline; unidade do ticket preservada. | `test_portfolio_output_security.py`, navegador com metadado malicioso |
| A13 — checks quebrados | Lint, formatação, tipagem e expectativas de testes reconciliados. Artefatos históricos selados ficam fora da formatação. | Suíte completa, Ruff, mypy e validação documental |

Os arquivos de teste citados podem ser localizados pelo nome em `tests/`. A [operação após as correções](../../operations/audit-remediation.md) documenta acesso, migração, recuperação e configuração; a [ADR-0009](../../architecture/adr/0009-access-and-workflow-recovery.md) registra as decisões.

## Verificação final

Comandos executados com o ambiente `.venv` do projeto, via `rtk proxy`:

- `.venv/Scripts/python.exe -m pytest --junitxml=output/audit-remediation/full-suite.xml`: **691 aprovados, 5 ignorados, zero falhas**, em 23,09 s. Um teste live Apify e quatro testes live LLM requerem opt-in e não foram executados.
- `.venv/Scripts/python.exe -m ruff check .`: aprovado.
- `.venv/Scripts/python.exe -m ruff format --check .`: 258 arquivos já formatados.
- `.venv/Scripts/python.exe -m mypy src`: aprovado, 91 arquivos.
- `.venv/Scripts/python.exe scripts/validate_docs.py`: aprovado; contagem final inclui este relatório.
- `docker compose config --quiet`, `node --check web/js/app.js` e `git -c core.whitespace=cr-at-eol diff --check`: aprovados. Git informa conversões normais de final de linha no Windows.
- Os sete hashes do manifesto da auditoria de segurança original continuam íntegros.

Em PostgreSQL 16 temporário e isolado, foram executadas as migrações desde banco vazio até `0013_workflow_reliability`, criação concorrente com mesma chave, rejeição de atualização obsoleta após cancelamento e exportação/restauração completa de 18 tabelas com FKs e scoring. Também foi realizado downgrade `0013 → 0012` e novo upgrade, preservando análise e score de teste. Resultados locais: `output/audit-remediation/postgres-validation.json` e `migration-roundtrip.json`. O contêiner temporário foi removido após a verificação de sua identificação exclusiva; os serviços existentes não foram reiniciados.

No navegador, uma aplicação temporária com SQLite e credenciais fictícias confirmou login, persistência da sessão após reload, portfólio sintético ENS com 33 cursos, abertura de dossiê sem premissas financeiras inventadas, escape de título malicioso sem execução e logout com posterior rejeição da sessão. Evidência visual local: `output/playwright/remediation-dossier.png`. A revisão também revelou resumos zerados no fallback histórico não carregado no banco: agora os resumos derivam dos próprios registros sintéticos existentes, com regressão dedicada e sem alterar a base.

Revisões independentes da análise e do workflow encontraram problemas adicionais de precedência institucional, perda de lease, starvation do reconciliador, repetição de Actor indeterminado e healthcheck do scheduler; as correções foram incorporadas. O revisor final reexecutou 25 testes focais e não apontou bloqueios adicionais nos escopos revisados. Isso não substitui testes de carga ou homologação real dos fornecedores.

## Preservação e próxima etapa

O histórico sintético ENS, o DOCX pessoal não rastreado e os arquivos reais de configuração/credenciais foram preservados. Sem JEV, `AI_MODE=traditional` ou `auto` utiliza a LLM tradicional em todos os julgamentos semânticos, planejamento e redação, incluindo o adaptador ChatGPT OAuth. Sem JEV, nenhuma comparação shadow fictícia é produzida. Fórmulas, permissões e transições de estado continuam sob validação em código.

Não foram realizadas chamadas pagas à LLM/Apify, testes live JEV, conexão ao CRM ENS, calibração com resultados oficiais, carga ou ensaio completo de desastre. A homologação manual com a ENS permanece pendente por decisão do usuário. Antes de executar a versão corrigida no stack atual, aplicar a migração e iniciar o scheduler conforme o runbook, preservando volumes e credenciais. A chave própria de acesso ao Prometeus é distinta do OAuth ChatGPT; o bootstrap fica no arquivo privado descrito no runbook e não é exposto em relatórios.
