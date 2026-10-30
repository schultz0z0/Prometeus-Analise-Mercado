# Relatório de Conclusão da Fase 3 — Fortalecer o Raciocínio de Mercado

**Data:** 2026-10-30  
**Contexto:** Inteligência de Mercado Sênior Prometeus (Auditoria 2026-10-30)  
**Status:** CONCLUÍDA E VERIFICADA  

---

## 1. Objetivo da Fase 3

Superar os limites de raciocínio de mercado diagnosticados nos achados P1 e P2 da auditoria (A09, A10, A11 e A12):
1. **Plano Orientado a Decisão (Tarefa 3.1):** substituir o plano genérico de queries por matriz de decisão estruturada por pergunta em 6 trilhas temáticas canônicas, tratando marcas indicadas pelo usuário como referências/sementes de descoberta e nunca como limites exclusivos da busca.
2. **Curadoria por Finalidade (Tarefa 3.2):** substituir o campo binário destrutivo `accepted` por avaliação multidimensional por uso (`EvidenceUseAssessment`), permitindo que um item sem preço continue útil para concorrência direta ou descoberta sem descarte total.
3. **Comparabilidade, Ofertas e Currículo (Tarefa 3.3):** eliminar falsos matches temáticos gerados por palavras de formato (como "extensão"), instituir piso de similaridade mínima determinístico (retornando 0, 1, 2 ou 3 comparáveis), calibrar a confiança do IPD pelo fit real de similaridade, preservar parâmetros semânticos em URLs e estruturar o mapeamento curricular ponta a ponta.
4. **Demanda de Alunos e Contexto ENS (Tarefa 3.4):** formalizar o modelo `LearnerDemandCase` (comprador vs beneficiário, B2B vs B2C, alternativas, objeções, funil plausível de primeira turma) e vedar a aplicação de multiplicadores macroeconômicos (SUSEP, CNseg, etc.) como estimativa direta de matrículas.

---

## 2. Entregas Realizadas

### Tarefa 3.1 — Plano Orientado a Decisão
- **Trilhas Temáticas Canônicas:** `src/prometeus/domain/research.py`
  - Criado o enum `ResearchTrack`:
    - `direct_competitors`: ofertas ativas, preços totais, parcelamento e módulos de concorrentes diretos;
    - `adjacent_offers`: ofertas adjacentes e substitutas (cursos livres, extensões, certificações);
    - `workforce_needs`: competências e cargos demandados por empregadores em vagas;
    - `educational_search`: busca educacional vs tema setorial geral;
    - `economic_context`: contexto econômico, capacidade de investimento e tíquetes praticados;
    - `primary_institutional`: dados históricos internos e diretrizes acadêmicas.
- **Matriz de Decisão por Pergunta:** `ResearchQuestion` em `src/prometeus/domain/research.py`
  - Campos adicionados: `track`, `hypothesis`, `counter_evidence_hypothesis`, `expected_evidence`, `capable_sources`, `scope_filter`, `sample_target`, `budget_allocated_usd`, `sufficiency_criteria`, `fallback_or_stop_rule`.
- **Planejador com Suporte a Matriz e Sementes de Descoberta:** `src/prometeus/application/plan_course_research.py`
  - Prompt e sistema orientados a estruturar as 6 trilhas e a preencher a matriz de decisão.
  - Normalização e injeção de fallback canônico cobrindo as 6 trilhas quando a resposta não fornecer perguntas.
  - Regra determinística: marcas fornecidas pelo usuário em `supplied_materials` ou descrição são tratadas como sementes de exploração inicial, garantindo a presença simultânea de buscas temáticas amplas para descoberta de novos concorrentes.
- **Atualização de Skills:**
  - `skills/planning-market-research/SKILL.md`: documentação das 6 trilhas, matriz de hipótese/contraprova e política de marcas sementes.
  - `skills/conducting-course-analysis/SKILL.md`: atualização da etapa 3 para planejamento orientado a decisão.
- **Testes de Contrato:** `tests/contract/market_sources/test_decision_oriented_plan.py` (3 testes passando).

### Tarefa 3.2 — Curadoria por Finalidade
- **Modelagem de Finalidades Canônicas:** `src/prometeus/domain/evidence_observations.py`
  - Criados enums e modelos:
    - `EvidencePurpose`: `discovery`, `pricing`, `direct_competition`, `adjacent_competition`, `workforce_competencies`, `employability_signal`, `learner_demand`, `own_context`, `industry_context`.
    - `EvidenceUseAssessment`: `purpose`, `usable`, `confidence`, `observable_factors`, `quote_snippets`, `reason`, `rejection_cause`, `next_step`.
    - `MultiPurposeAssessment`: agregação com método auxiliar `is_usable_for` e propriedade `usable_purposes`.
- **Curadoria Multidimensional sem Descarte Mútuo:** `src/prometeus/application/qualify_market_evidence.py`
  - Para cada evidência avaliada, constrói-se o `MultiPurposeAssessment`:
    - Uma oferta sem preço não é utilizável para `pricing`, mas permanece utilizável para `direct_competition` e `discovery`.
    - Uma vaga de emprego sustenta `workforce_competencies` e `employability_signal`, sem se tornar concorrente direto ou preço de curso.
    - Conteúdo da própria instituição vira `own_context`, nunca concorrente externo.
    - Itens inconclusivos registram obrigatoriamente `rejection_cause` e `next_step`.
  - Persistência em `data["_qualification"]`: preserva compatibilidade com consumidores existentes (`accepted`, `use_for`) e adiciona `usable_purposes` e `use_assessments`.
- **Testes Unitários:** `tests/unit/application/test_multipurpose_curation.py` (5 testes passando).

### Tarefa 3.3 — Comparabilidade, Ofertas e Currículo
- **Stopwords de Categoria e Formato:** `src/prometeus/application/internal_history.py`
  - Inclusão de termos de formato/categoria (`extensao`, `extensivo`, `especializacao`, `aperfeicoamento`, `capacitacao`, `treinamento`, `imersao`, `certificacao`, `qualificacao`, `habilitacao`, `formacao`, `presencial`, `hibrido`, `ead`) em `_tokens()`.
  - Impede falsos matches onde títulos de áreas distintas (ex.: "Extensão em Culinária" vs "Extensão em Fraudes") compartilhavam apenas o formato acadêmico.
- **Piso Determinístico de Similaridade e Seleção ENS (0 a 3):** `InternalHistoryService.build`
  - Estabelecido piso determinístico `fit >= 0.15`. Cursos com proximidade temática inferior ao piso são descartados.
  - Suporta retorno determinístico de 0, 1, 2 ou 3 comparáveis conforme disponibilidade real da base.
- **Calibração da Confiança do IPD:**
  - A confiança do IPD passa a ser escalada pelo fit real de similaridade dos comparáveis selecionados (`fit_scale = min(1.0, mean_fit / 0.35)`), eliminando o defeito onde cursos com similaridade ínfima recebiam confiança 0.90 arbitrária.
- **Deduplicação de URLs com Preservação de Parâmetros Semânticos:** `src/prometeus/application/pricing_reference.py`
  - `_canonical()` filtra parâmetros de tracking (`utm_*`, `fbclid`, `gclid`, etc.), mas preserva parâmetros semânticos (`id`, `curso`, `modalidade`, `tier`), impedindo que cursos distintos com parâmetros de query na mesma rota sejam colapsados.
  - Cálculo explícito de dispersão (`dispersion_total_brl`) e gap de preço entre interno e externo (`price_gap_brl`).
- **Mapeamento Curricular Estruturado:** `src/prometeus/domain/research.py`
  - Criado o modelo `CurriculumMappingItem`: módulo → aprendizado → competência/necessidade → fonte/trecho → cobertura/gap → ação.
- **Testes Unitários:** `tests/unit/application/test_comparability_and_curriculum.py` (5 testes passando).

### Tarefa 3.4 — Demanda de Alunos e Contexto ENS
- **Modelo Estruturado de Demanda:** `src/prometeus/domain/research.py`
  - Criado o modelo canônico `LearnerDemandCase`:
    - `buyer_vs_beneficiary`: separação entre quem paga e quem estuda (`same_individual`, `employer_b2b`, `hybrid`);
    - `segment_type`: `b2c`, `b2b`, `b2b2c`;
    - `eligibility_criteria`: critérios de formação e pré-requisitos;
    - `training_intent_signals`: sinais concretos de busca por capacitação e dúvidas profissionais;
    - `alternatives_considered`: cursos curtos, autoaprendizado, concorrência, etc.;
    - `barriers`: tíquete, tempo, reconhecimento de mercado;
    - `declared_vs_behavioral_notes`: notas de intenção declarada vs atitude comportamental;
    - `plausible_initial_cohort_size`: tamanho plausível da turma piloto (ex.: 15 a 30 alunos);
    - `funnel_reach_scenario`: parâmetros de alcance, leads, inscritos e taxa de conversão;
    - `institutional_context_sources`: fontes setoriais de contexto (SUSEP, CNseg, etc.).
- **Proibição Estrita de Multiplicadores Macroeconômicos:**
  - Validador `@model_validator` proíbe expressamente `institutional_multipliers_applied=True`, lançando `ValueError` caso tente-se derivar vagas ou matrículas aplicando percentuais arbitrários sobre o porte do mercado segurador nacional.
- **Testes Unitários:** `tests/unit/domain/test_learner_demand_case.py` (3 testes passando).

---

## 3. Matriz de Verificação

| Gate da Fase 3 | Verificação | Resultado |
|---|---|:---:|
| 6 Trilhas Canônicas e Matriz de Decisão | `tests/contract/market_sources/test_decision_oriented_plan.py` (3 testes) | PASS |
| Curadoria Multidimensional por Finalidade | `tests/unit/application/test_multipurpose_curation.py` (5 testes) | PASS |
| Comparabilidade, Stopwords e Currículo | `tests/unit/application/test_comparability_and_curriculum.py` (5 testes) | PASS |
| Modelo de Demanda e Proibição de Multiplicadores | `tests/unit/domain/test_learner_demand_case.py` (3 testes) | PASS |
| Regressão de Histórico Interno e Preços | `test_internal_history_ipd.py`, `test_enriched_historical_fixture.py`, `test_pricing_reference_v2.py` (22 testes) | PASS |
| Suíte Completa de Testes | `tests/unit tests/contract tests/integration` (528 testes passando, 1 skipped) | PASS |
| Verificação de Tipos | `mypy src` (77 arquivos verificados, 0 erros) | PASS |
| Linter e Formatação | `ruff check src tests` (0 erros) | PASS |
| Integridade de Documentação | `scripts/validate_docs.py` (156 arquivos Markdown) | PASS |
| Checagens de Baseline Congelado | `docs/implementation/reports/senior-market-intelligence-baseline-checks-2026-10-30.py` | PASS |

---

## 4. Conclusão e Próximos Passos

A **Fase 3** foi concluída com 100% de sucesso e 0 regressões. O raciocínio de mercado do Prometeus foi substancialmente robustecido:
- O planejamento agora é estruturado em matriz de decisão orientada a hipóteses e contraprovas em 6 trilhas.
- A qualificação preserva evidências úteis sob diferentes prismas sem descartes binários arbitrários.
- O cálculo de comparabilidade interna e preços possui piso de qualidade, tolerância a 0-3 comparáveis e não é iludido por stopwords de formato.
- A modelagem de demanda distingue compradores de beneficiários e impede a multiplicação cega de dados da SUSEP/CNseg sobre matrículas.

O sistema está pronto para a **Fase 4 — Critérios de Decisão, SWOT e Economia**.

