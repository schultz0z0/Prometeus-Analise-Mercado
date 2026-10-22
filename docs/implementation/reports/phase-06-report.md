# Relatório de conclusão — Fase 06: Dossiê e Síntese Generativa

## Resumo executivo

- **Fase:** 06 — Dossiê e Síntese Generativa
- **Status:** COMPLETE
- **Nota:** 10/10
- **Início:** 2026-10-22 16:51 BRT
- **Fim:** 2026-10-22 17:02 BRT
- **Responsável pela execução:** Antigravity AI
- **Plano da fase:** `docs/implementation/phase-06-dossier.md`
- **Gate relacionado:** [Gate C — AI ready](../../roadmap/release-gates.md#gate-c--ai-ready) (factualidade e injection da LLM)
- **Commit inicial:** `3fd15de`
- **Commit final:** a ser registrado após este commit

## Escopo planejado

Produzir narrativa útil sem permitir que o modelo altere fatos, invente sustentação ou execute comandos adversariais. Implementa as etapas 12 (síntese) e 13 (verificação) do workflow do Prometeus:

1. Definir `DossierFacts` e schema de saída com hashing canônico imutável de proveniência.
2. Criar adapter fake e fixtures de fatos com métricas reais de mercado e institucionais.
3. Criar prompts versionados com separação estrita entre instrução e conteúdo (`config/prompts/dossier-v1.yaml`).
4. Estender o provider generativo (`GenerativeModelPort`) para saída estruturada do dossiê, com controle de timeout e estimativa de custo.
5. Exigir `evidence_ids` por claim relevante e validação de vínculo.
6. Implementar verificação numérica determinística e de referências (TOOL-15 `DossierVerifier`).
7. Testar cenários de evasão, prompt injection, números inventados (alucinação) e dados ausentes.
8. Criar seções para 3 públicos decisores: Diretoria (`executive`), Acadêmico (`academic`) e Marketing (`marketing`).
9. Persistir dossiês auditáveis no PostgreSQL (`dossiers`) com integridade relacional 1:1 e cascade delete.
10. Validar requisitos formais de aprovação do Gate C — AI ready.

## Escopo entregue

- **Modelos Canônicos de Dossiê e Fatos (`src/prometeus/domain/dossiers.py`)**:
  - `DossierFacts` e `DossierFactItem`: agregação imutável de scores, decisões JEV e evidências de mercado higienizadas com cálculo determinístico de `facts_hash` via SHA-256.
  - `DossierClaim`: afirmações tipadas (`quantitative`, `qualitative`, `strategic`), níveis de suporte (`observed`, `suggestive`, `hypothesis`) e status de auditoria (`verified`, `unsupported`, `flagged_hallucination`, `rejected`).
  - `DossierSection`: divisões temáticas para diretoria, acadêmico e marketing.
  - `DossierOutput`: representação estruturada completa do dossiê com vínculo ao hash factual e custos em USD.
- **Prompt Versionado `dossier-v1` (`config/prompts/dossier-v1.yaml`)**:
  - Delimitação explícita dos fatos de entrada em `<approved_facts>` com regra inegociável de proibição de alucinação e proibição de execução de texto como instrução.
  - Schema de saída JSON estrito com claims decompostas e referências a `evidence_ids`.
- **Extensão da Porta Generativa (`GenerativeModelPort`) e Adaptadores**:
  - `src/prometeus/domain/ports/generative_model.py`: adicionado método `synthesize_dossier` sem quebrar contratos da Fase 04.
  - `src/prometeus/infrastructure/llm/fake.py`: implementação em memória determinística com suporte a simulação de injeção e alucinações.
  - `src/prometeus/infrastructure/llm/client.py`: implementação HTTP compatível com OpenAI/OpenRouter, extração robusta de JSON ({...}) e tratamento de codeblocks.
- **Verificador Factual Determinístico — TOOL-15 (`src/prometeus/application/dossier_verifier.py`)**:
  - Validação estrita de existência de `evidence_ids` citados.
  - Extração e batimento exato de números (moedas R$, percentuais e contagens de vagas/alunos) contra os valores das evidências referenciadas.
  - Marcação imediata de `FLAGGED_HALLUCINATION` quando métricas inventadas forem identificadas.
  - Detecção ativa e bloqueio de variantes de prompt injection (`REJECTED`).
  - Transição de status para `REVISION_REQUIRED` quando houver alucinação ou taxa de claims sem suporte $> 20\%$.
- **Serviço de Orquestração (`src/prometeus/application/synthesize_dossier.py`)**:
  - `DossierSynthesisService` orquestra a consolidação factual (`build_facts`), acionamento da LLM, execução do `DossierVerifier` e persistência relacional.
- **Persistência Relacional em PostgreSQL e Migração Alembic**:
  - Tabela `dossiers` criada em `src/prometeus/infrastructure/db/models.py` com tipos `JSONB`, restrição `UNIQUE (analysis_id)`, chave estrangeira cascade delete e migração `migrations/versions/0006_create_dossiers_table.py`.
- **Suite de Avaliação do Gate C — AI ready (`tests/evaluation/dossier/test_gate_c_ai_ready.py`)**:
  - Testes com fixtures benchmark comprovando zero claims quantitativas sem suporte, detecção de números sinteticamente alterados e resistência a ataques de injeção.

## Matriz de rastreabilidade

| Requisito / Critério | Implementação | Teste | Evidência | Resultado |
|---|---|---|---|---|
| Modelos de Domínio e Hash SHA-256 | `src/prometeus/domain/dossiers.py` | `tests/unit/dossiers/test_dossier_models.py` | Fatos imutáveis, hash determinístico independente da ordem | Aprovado |
| Prompt Versionado `dossier-v1` | `config/prompts/dossier-v1.yaml` | `tests/contract/market_sources/test_generative_model.py` | Separação entre instrução e conteúdo delimitado | Aprovado |
| Verificador Factual (TOOL-15) | `src/prometeus/application/dossier_verifier.py` | `tests/unit/dossiers/test_dossier_verifier.py` | 6 testes de consistência numérica, IDs inexistentes e injeção | Aprovado |
| Persistência Relacional PostgreSQL | `src/prometeus/infrastructure/db/models.py`, migration 0006 | `tests/integration/dossiers/test_dossier_db_integration.py` | DDL PostgreSQL com JSONB, UNIQUE e cascade delete | Aprovado |
| Orquestração E2E de Síntese | `src/prometeus/application/synthesize_dossier.py` | `tests/integration/dossiers/test_synthesize_dossier_integration.py` | Carga de scores/evidências, síntese fake e gravação em banco | Aprovado |
| Avaliação de Gate C (AI ready) | `tests/evaluation/dossier/test_gate_c_ai_ready.py` | `test_gate_c_zero_unsupported_quantitative_claims...` | 0 alucinações, 100% claims quantitativas verificadas, bloqueio injection | Aprovado |

## Arquivos criados ou modificados

| Arquivo | Alteração | Motivo |
|---|---|---|
| `src/prometeus/domain/dossiers.py` | Criado | Modelos de domínio canônicos de dossiê, fatos e claims |
| `config/prompts/dossier-v1.yaml` | Criado | Prompt versionado para síntese executiva factual |
| `src/prometeus/domain/ports/generative_model.py` | Modificado | Adicionado método `synthesize_dossier` à interface |
| `src/prometeus/infrastructure/llm/fake.py` | Modificado | Implementação fake determinística de síntese de dossiê |
| `src/prometeus/infrastructure/llm/client.py` | Modificado | Implementação HTTP e parsing JSON de dossiês |
| `src/prometeus/application/dossier_verifier.py` | Criado | Verificador de claims numéricas, referências e injeção (TOOL-15) |
| `src/prometeus/application/synthesize_dossier.py` | Criado | Serviço de orquestração de síntese e persistência |
| `src/prometeus/infrastructure/db/models.py` | Modificado | Adicionado `DossierModel` e relacionamento em `AnalysisModel` |
| `migrations/versions/0006_create_dossiers_table.py` | Criado | Migração Alembic para tabela `dossiers` em PostgreSQL |
| `tests/unit/dossiers/test_dossier_models.py` | Criado | Testes unitários de modelos e hash SHA-256 |
| `tests/unit/dossiers/test_dossier_verifier.py` | Criado | Testes unitários do verificador determinístico |
| `tests/integration/dossiers/test_dossier_db_integration.py` | Criado | Testes de integridade relacional PostgreSQL e DDL |
| `tests/integration/dossiers/test_synthesize_dossier_integration.py` | Criado | Testes de integração do fluxo completo de síntese |
| `tests/evaluation/dossier/test_gate_c_ai_ready.py` | Criado | Suite de validação empírica do Gate C (AI ready) |
| `docs/implementation/reports/phase-06-report.md` | Criado | Relatório formal de conclusão da fase |

## Testes e verificações

| Comando | Momento | Exit code | Resultado resumido |
|---|---|---:|---|
| `pytest tests/unit/dossiers/ -q` | Fase 06 | 0 | 8 testes unitários aprovados |
| `pytest tests/integration/dossiers/ -q` | Fase 06 | 0 | 3 testes de integração aprovados |
| `pytest tests/evaluation/dossier/ -q` | Gate C | 0 | 3 testes de avaliação de factualidade e injection aprovados |
| `pytest -q` | Regressão completa | 0 | `131 passed in 2.73s [100%]` (14 novos testes na fase) |
| `ruff check .` | Qualidade | 0 | `All checks passed!` |
| `ruff format --check .` | Qualidade | 0 | `165 files already formatted` |
| `mypy src` | Tipagem | 0 | `Success: no issues found in 37 source files` |
| `python scripts/validate_docs.py` | Documentação | 0 | `100 Markdown files checked` (100% íntegros) |

## Rubrica 10/10

| Critério | Máximo | Obtido | Evidência |
|---|---:|---:|---|
| Escopo obrigatório entregue | 2 | 2 | Todos os 10 itens da Fase 06 entregues e validados |
| Testes e regressão aprovados | 2 | 2 | 131 testes aprovados na suíte completa com 100% de sucesso |
| Critérios de aceite e gates aprovados | 2 | 2 | Gate C — AI ready plenamente atendido (zero claims sem suporte e resistência a injection) |
| Documentação atualizada | 1 | 1 | 100 docs validados via `validate_docs.py`, relatório emitido |
| Segurança e privacidade verificadas | 1 | 1 | Defesa ativa contra prompt injection, conteúdo delimitado não confiável |
| Revisão sem defeitos críticos/altos | 1 | 1 | Zero warnings em Mypy e Ruff |
| Sem bloqueios ou pendências essenciais | 1 | 1 | Persistência em PostgreSQL com integridade referencial testada |
| **Total** | **10** | **10** | **Conclusão com excelência** |

## Gate da fase

- **Gate aplicável:** [Gate C — AI ready](../../roadmap/release-gates.md#gate-c--ai-ready) (factualidade e injection da LLM)
- **Resultado:** **APROVADO**
- **Evidências:**
  1. Zero claims quantitativas sem evidência ou com números alucinados na avaliação benchmark.
  2. Bloqueio determinístico de variações de evasão e prompt injection pelo `DossierVerifier`.
  3. Formatação estruturada em seções para Diretoria, Acadêmico e Marketing cumprida.
  4. Rastreabilidade auditável garantida pelo hash SHA-256 do `DossierFacts`.
