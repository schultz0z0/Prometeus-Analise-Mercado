# Correção dos achados da auditoria — plano de implementação

**Objetivo:** corrigir A01–A13 da auditoria de 04/11/2026, preservando o histórico sintético ENS e o uso integral da LLM tradicional sem JEV. Homologação manual e calibração comercial permanecem pendentes, conforme autorização do usuário.

**Arquitetura:** preservar o monólito e os contratos canônicos; eliminar cálculos/apresentações paralelos, controlar concorrência/transações e conectar entradas/saídas ao mesmo caso de uso. Autenticar operações por credenciais próprias do Prometeus, distintas do OAuth do fornecedor; sessão de navegador HttpOnly e escopos institucionais em código. Nenhuma credencial real entra em commits ou relatórios.

**Stack:** Python/FastAPI/SQLAlchemy/Celery, PostgreSQL/Redis, JavaScript, pytest/Ruff/mypy.

## Restrições e decisões

- `traditional` e `auto` sem JEV usam a LLM tradicional para planejamento, julgamentos e redação; OAuth existente e Apify serão preservados. `hybrid` explicitamente solicitado sem chave continua erro de configuração, sem substituição silenciosa.
- Não migrar ou apagar a base histórica sintética ENS nem recalcular silenciosamente análises publicadas.
- Novos contratos e revisões usam snapshots explícitos; conteúdo sem premissa é marcado ausente.
- Autenticação do Prometeus não depende do login ChatGPT. A API protege escopos e instituição; a interface oferece login de acesso próprio, preservando OAuth de inferência.
- Trabalho na branch `codex/audit-remediation`, com alterações anteriores da auditoria e DOCX pessoal preservados. Não publicar/implantar durante a implementação; homologação manual será posterior.

## Execução com regressões primeiro

1. **Dossiê/economia (A01/A02):** testes de proposta sem premissas e ocupação impossível; `synthesize_dossier.py`, serviço econômico e `dossier-view.js`; remover conteúdo inventado, usar Decimal e proveniência, testar saída final.
2. **Workflow (A04–A07):** regressões de cancelamento concorrente, publicação pós-commit, reanálise/idempotência e keywords; persistir governança e outbox/reconciliação; parar novas etapas após cancelamento; serializar persistência de julgamentos.
3. **Acesso e XSS (A03/A12):** testes anônimo/escopo/tenant/identidade e metadados HTML; middleware de acesso e sessão navegador, configuração segura, escape nas views; preservar callback OAuth por state/nonce e healthchecks.
4. **Entradas e entrega (A08/A09):** transportar MCP real por stdio com validação, compartilhar criação canônica e enfileiramento; eventos webhook persistidos e despacho/retries; testes de integração sem rede paga.
5. **Backup (A10):** roundtrip completo incluindo score/evidências/decisões/linhagem em ordem de FKs; restaurar formato completo versionado sem aceitar exportação antiga como backup completo.
6. **Avaliação e checks (A11/A13):** separar simulação e avaliação real sem gabarito; gates honestos pendentes; reconciliar testes do ecossistema; Ruff/mypy/pytest/documentação e revisão independente.

Cada grupo terá teste que falha antes da correção e passa depois. Atualizar documentação de módulo, ADR quando necessário, changelog e relatório de conclusão com comandos/resultados reais. Revisão de aderência e depois qualidade por revisor independente. Não declarar 10/10 comercial ou produção homologada por testes offline.

## Extensão descoberta na homologação real autorizada

Implementar ADR-0010: autorização por Actor persistida antes do POST e saldo agregado por análise, separado do custo observado e compartilhado com reparo. Testar primeiro reserva anterior à chamada, baixa cobrança provisória sem liberação, soma entre planos, rejeição inequívoca sem compra, incerteza com reserva e consultas sem saldo. Preservar canário já em execução com a versão anterior; reconciliar suas cobranças por consulta ao provedor sem inventar reserva histórica. Corrigir perda de metadata em billing/build nulo. Revisar implementações independentemente e revalidar ambiente antes de aprovar o runtime atualizado.
