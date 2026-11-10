# Dossiê CMS Multi-Subpágina (9 Abas em Dark Theme) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar a visualização e publicação do Dossiê Executivo do Prometeus em um sistema estilo **CMS de 9 Subpáginas hospedadas em SQL**, replicando fielmente a estrutura, navegação, KPIs, matrizes e gráficos das 9 capturas de referência sobre o **Tema Escuro Canônico do Prometeus** (`tokens.css`), com preenchimento automático ao final da análise (IA + construtor determinístico validado pelo `DossierVerifier`) e governança interativa por área na aba `Revisões`.

**Architecture:**
1. **Construtor Determinístico + Síntese Verificada (`DossierCmsPageBuilder`):** Um módulo dedicado (`src/prometeus/application/dossier_cms_builder.py`) compõe o contrato estruturado `cms_pages` contendo o cabeçalho global (`meta`) e o payload tipado das **9 subpáginas** (`overview`, `key_metrics`, `fixed_competition`, `sector_radar`, `economics`, `swot_tows`, `viability_pillars`, `revisions`, `sources_evidences`), combinando cálculos em código (`ScoringResult`, `CourseEconomicsService`, `ecosystem_presentation`), evidências rastreáveis (`evidence_ids`) e afirmações verificadas (`claim_ids`).
2. **Trava de Integridade no `DossierVerifier`:** `DossierSynthesisService._build_visual_presentation_blocks` passa a incluir `cms_pages` no envelope `presentation` persistido em `DossierModel.presentation`, e `DossierVerifier.verify_presentation` audita `presentation["cms_pages"]` contra a projeção determinística — impedindo qualquer número inventado ou fora do catálogo.
3. **Persistência SQL de Revisões por Área e Hidratação Retrocompatível:** Uma nova tabela SQL `dossier_area_reviews` (`DossierAreaReviewModel` + migração `0013_dossier_area_reviews.py`) armazena o parecer humano das 4 áreas (`marketing`, `produto`, `comercial`, `financeiro`), comentários e histórico de versões (`v1.0`, `v1.1`...) exibidos na aba `Revisões`. Os endpoints `GET /v1/analyses` e `GET /v1/analyses/{id}` hidratam `cms_pages` automaticamente para dossiês legados já salvos no banco e expõem `POST /v1/analyses/{id}/area-reviews`.
4. **Interface Web Dark-Theme com 9 Subpáginas (`web/js/views/dossier-cms-tabs.js` + `dossier-view.js`):** A visão do dossiê passa a exibir a barra superior de navegação das 9 subpáginas, *breadcrumb* (`Dossiês > {Curso} > {Subpágina}`), cabeçalho com selo de atualização e ações (`Exportar`, `Compartilhar`), os 9 templates ricos em tema escuro com gráficos SVG/CSS (Donut IVO/IE/Revisão, Radar 6 Eixos, Cascata Financeira, Mapa de Posicionamento 2×2, Funil de 4 etapas, Série Temporal e Barras de Dimensão) e uma seção de **Auditoria Metodológica & Diagnóstico Integral** que preserva 100% dos contratos dos testes operacionais existentes.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Vanilla ES Modules (`web/js/`), CSS Custom Properties Dark Theme (`web/styles/tokens.css`, `web/styles/app.css`), Pytest + Node ESM runner para testes operacionais de UI.

---

## Mapa de Arquivos

### Novos Arquivos
- `src/prometeus/application/dossier_cms_builder.py` — Construtor determinístico do contrato `cms_pages` (9 subpáginas + metadados + cálculo de IVO/IE, matriz peso × nota, mapa 2×2, cascata financeira, radar 6 eixos, SWOT/TOWS estruturado e consolidação de revisões).
- `migrations/versions/0013_dossier_area_reviews.py` — Migração SQL criando a tabela `dossier_area_reviews` com isolamento por `tenant_id` e `analysis_id`.
- `web/js/views/dossier-cms-tabs.js` — Renderizadores modulares em Dark Theme para as 9 subpáginas do CMS (`overview`, `key_metrics`, `fixed_competition`, `sector_radar`, `economics`, `swot_tows`, `viability_pillars`, `revisions`, `sources_evidences`) e componentes gráficos SVG/CSS.
- `tests/unit/dossiers/test_dossier_cms_builder.py` — Testes unitários do contrato das 9 subpáginas, estados explícitos quando faltam premissas e validação no `DossierVerifier.verify_presentation`.
- `tests/integration/entrypoints/test_dossier_cms_api.py` — Testes de integração dos endpoints REST (`GET /v1/analyses/{id}`, hidratação de `cms_pages` e `POST /v1/analyses/{id}/area-reviews` com isolamento multi-tenant).
- `tests/operational/test_dossier_cms_subpages_rendering.py` — Testes operacionais via Node ESM validando a renderização das 9 subpáginas, troca de abas, gráficos SVG e preservação integral das garantias de segurança/XSS e auditoria.

### Arquivos Modificados
- `src/prometeus/application/synthesize_dossier.py` — Integra `build_cms_dossier_pages` em `_build_visual_presentation_blocks`.
- `src/prometeus/application/dossier_verifier.py` — Audita `presentation["cms_pages"]` em `verify_presentation` e adiciona `"cms_pages"` ao conjunto `allowed`.
- `src/prometeus/infrastructure/db/models.py` — Adiciona `DossierAreaReviewModel` (`dossier_area_reviews`) e relacionamento em `AnalysisModel`.
- `src/prometeus/entrypoints/rest/app.py` — Hidrata `cms_pages` e `area_reviews` no payload do dossiê retornado pela API e adiciona o endpoint `POST /v1/analyses/{analysis_id}/area-reviews`.
- `web/js/store.js` — Adiciona estado `activeDossierTab` (default `'overview'`) e action `setActiveDossierTab(tabId)`.
- `web/js/api.js` — Adiciona helper `submitDossierAreaReview(analysisId, payload)` para gravação de parecer por área na aba `Revisões`.
- `web/js/views/dossier-view.js` — Renderiza o shell CMS (barra das 9 subpáginas, *breadcrumb*, header, subpágina ativa via `dossier-cms-tabs.js`, drawer de evidências e bloco de auditoria completa).
- `web/styles/app.css` — Estilos Dark Theme das 9 subpáginas, barra de abas estilo painel CMS, KPIs, gráficos SVG (donut, radar, cascata, scatter 2×2, funil), matrizes SWOT/TOWS e linha do tempo de revisões.
- `docs/README.md` — Atualiza o índice de documentação e registro da evolução do Dossiê CMS v3.

---

## Task 1: Construtor Determinístico `DossierCmsPageBuilder` e Verificação em `DossierVerifier`

**Files:**
- Create: `src/prometeus/application/dossier_cms_builder.py`
- Modify: `src/prometeus/application/synthesize_dossier.py`
- Modify: `src/prometeus/application/dossier_verifier.py`
- Test: `tests/unit/dossiers/test_dossier_cms_builder.py`

- [ ] **Step 1: Escrever o teste unitário falhando para o construtor das 9 subpáginas e `verify_presentation`**

Criar `tests/unit/dossiers/test_dossier_cms_builder.py` verificando que:
1. `build_cms_dossier_pages(proposal, facts, dossier, economics, ecosystem)` gera um dicionário determinístico com `schema_version == 1`, `default_tab == "overview"`, `tabs_order` contendo exatamente as 9 chaves (`overview`, `key_metrics`, `fixed_competition`, `sector_radar`, `economics`, `swot_tows`, `viability_pillars`, `revisions`, `sources_evidences`) e `pages` contendo o payload estruturado de cada uma das 9 subpáginas.
2. Os scores **IVO** (`round(facts.viability_score)`) e **IE** (`round(((facts.coverage_score + facts.confidence_score) / 2.0) * 100)`) e a **Matriz Peso × Nota** em `overview` e `viability_pillars` refletem exatamente os 6 pilares oficiais (`internal_history`, `paid_competition`, `search_and_media`, `employability`, `syllabus_fit`, `pricing`) sem inventar notas.
3. Quando `proposal` não contém premissas financeiras (`economics.status != "calculated"`), as subpáginas `overview`, `key_metrics` e `economics` expõem estados explícitos (`"status": "assumptions_required"`, `"value_label": "Requer premissas"`) em vez de números fabricados.
4. `DossierVerifier().verify_presentation(dossier, facts, presentation, proposal)` aprova quando `presentation["cms_pages"]` corresponde ao construtor determinístico e rejeita (`presentation.cms_pages` com `presentation_fact_mismatch`) se qualquer número ou texto dentro de `cms_pages` for adulterado.

- [ ] **Step 2: Executar o teste para confirmar a falha inicial**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/unit/dossiers/test_dossier_cms_builder.py
```
Expected: `FAIL` (`ModuleNotFoundError: No module named 'prometeus.application.dossier_cms_builder'`).

- [ ] **Step 3: Implementar `src/prometeus/application/dossier_cms_builder.py` e integrar em `synthesize_dossier.py` e `dossier_verifier.py`**

Implementar em `src/prometeus/application/dossier_cms_builder.py`:
- Constante `CMS_TABS_METADATA` com a ordem canônica das 9 subpáginas:
  1. `overview` — `"Visão Geral"`
  2. `key_metrics` — `"Métricas-Chave"`
  3. `fixed_competition` — `"Concorrência Fixa"`
  4. `sector_radar` — `"Radar Setorial"`
  5. `economics` — `"Economia & Cenários"`
  6. `swot_tows` — `"SWOT & TOWS"`
  7. `viability_pillars` — `"Pilares de Viabilidade"`
  8. `revisions` — `"Revisões"`
  9. `sources_evidences` — `"Fontes & Evidências"`
- Pesos canônicos dos 6 pilares (`PILLAR_WEIGHTS`: `internal_history: 0.20`, `paid_competition: 0.20`, `search_and_media: 0.20`, `employability: 0.15`, `syllabus_fit: 0.15`, `pricing: 0.10`) e metadados de rótulo/ícone.
- Construtores determinísticos por subpágina:
  - `_build_overview_page(...)`: 5 KPIs de topo (IVO, IE, Recomendação oficial, Projeção/Equilíbrio de Matrículas, Margem Prevista), barras `dimensions_bars` (0–100), `scenario_summary` (Conservador, Base, Otimista ou estado explícito de premissa ausente), `decision_matrix` (Critério, Peso, Nota, Contribuição em pts, Leitura `Forte`/`Adequada`/`Atenção`/`Insuficiente`) e `key_insights` (claims verificados com `evidence_ids`).
  - `_build_key_metrics_page(...)`: 8 KPIs em 2 linhas (Alunos/Turmas Históricas, Ocupação/Conversão Histórica, Aderência da Base ENS, Procura Externa, Ticket Médio Projetado, Custo Variável/CAC, Margem Prevista, Resumo IE / IVO), série histórica de turmas comparáveis (`historical_trend`), funil de capacidade/equilíbrio (`funnel_stages`), composição `ie_ivo_summary`, tabela `dimension_indicators`, tabela `internal_benchmark` (Média ENS comparáveis vs. Curso Proposto) e `analytical_highlights`.
  - `_build_fixed_competition_page(...)`: 4 KPIs (Concorrentes mapeados `offers_found_count` de `monitored_total`, Intensidade competitiva, Faixa média de preço em R\$, Lacunas de posicionamento), linhas da tabela comparativa (`competitor_rows` a partir de `ecosystem["competitive_benchmark"]["rows"]`), pontos do `positioning_map_2x2` (eixo X = preço normalizado, eixo Y = carga horária/profundidade + zona `"Espaço de oportunidade (ENS)"`), `observed_signals`, `ens_differentiation` e `actionable_insights`.
  - `_build_sector_radar_page(...)`: 5 KPIs (Índice/Cobertura do Radar Setorial, Tendência de Demanda, Maturidade do Tema, Intensidade Competitiva, Potencial de Escala), `radar_axes` (6 eixos 0–100: Demanda, Busca & Mídia, Competitividade, Relevância Profissional, Histórico ENS, Aderência Curricular), `trend_series` (série temporal do Google Trends quando observada), `subthemes_distribution` (agrupamento por `theme_detected` em `sector_radar`), `radar_signals` (Fortes vs. Pontos de Atenção), `theme_clusters`, `executive_reading` e `bottom_highlights`.
  - `_build_economics_page(...)`: 6 KPIs (Receita Esperada Base, Ticket Médio, Margem Líquida, Ponto de Equilíbrio, Custos Fixos da Turma, Resultado Líquido Base), `waterfall_steps` (Receita Bruta, Descontos/Impostos, Custos Variáveis, Custos Fixos, Resultado Líquido), `launch_scenarios` (Conservador, Base, Otimista), `sensitivity_matrix` (Variação de Desconto/Ticket × Cenário de Matrículas) e `risks_and_assumptions` (`risks` de `limitations`/`cons` + `assumptions` de `economics.input_sources`).
  - `_build_swot_tows_page(...)`: 4 KPIs (Aderência Estratégica, Forças & Oportunidades, Fragilidades & Riscos, Posicionamento Estratégico), `swot` (`strengths`, `weaknesses`, `opportunities`, `threats` com `claim_ids`/`evidence_ids`), `tows` (`so_strategies`, `st_strategies`, `wo_strategies`, `wt_strategies` derivados das ações recomendadas e claims verificados), `recommended_priorities` e `executive_synthesis`.
  - `_build_viability_pillars_page(...)`: 6 cards `pillar_cards` (nota `/100`, peso `%`, status `Forte`/`Adequado`/`Atenção`/`Insuficiente` e 3 sub-métricas determinísticas cada), `ivo_composition_donut`, `weight_score_matrix`, `pillar_justifications` e `footer_recommendation`.
  - `_build_revisions_page(...)`: `area_reviews` padrão para as 4 áreas (`marketing`, `produto`, `comercial`, `financeiro`), `overall_progress` (percentual aprovado e contagem), `version_history` (`v1.0 Base — Publicação automática IA` + entradas subsequentes), `comments_feed`, `changes_summary`, `pendencies` (a partir de `dossier.required_validations`), `approval_recommendation` e `next_steps` (a partir de `dossier.recommended_actions`).
  - `_build_sources_evidences_page(...)`: `collected_sources` (catálogo consolidado de fontes com tipo, status, contagem e observação), `research_coverage` (barras por dimensão + cobertura geral `%`), `evidence_reliability` (score `/100` + selo), `primary_evidence_categories` (4 cards por categoria com `evidence_ids`) e `analysis_method_steps` (5 etapas: `1 Coleta`, `2 Preparação`, `3 Classificação`, `4 Score`, `5 Decisão`).
- Atualizar `DossierSynthesisService._build_visual_presentation_blocks` (`src/prometeus/application/synthesize_dossier.py:923-974`) e `DossierVerifier.verify_presentation` (`src/prometeus/application/dossier_verifier.py:41-168`) para incluir e auditar `"cms_pages"`.

- [ ] **Step 4: Executar os testes unitários para confirmar aprovação**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/unit/dossiers/test_dossier_cms_builder.py tests/unit/dossiers/test_dossier_verifier.py
```
Expected: `PASS`.

- [ ] **Step 5: Commit da Task 1**

Run:
```powershell
rtk git add src/prometeus/application/dossier_cms_builder.py src/prometeus/application/synthesize_dossier.py src/prometeus/application/dossier_verifier.py tests/unit/dossiers/test_dossier_cms_builder.py
rtk git commit -m "feat(dossier): add deterministic 9-subpage CMS builder and verifier check"
```

---

## Task 2: Persistência SQL de Revisões por Área (`dossier_area_reviews`) e Endpoints REST

**Files:**
- Create: `migrations/versions/0013_dossier_area_reviews.py`
- Modify: `src/prometeus/infrastructure/db/models.py`
- Modify: `src/prometeus/entrypoints/rest/app.py`
- Test: `tests/integration/entrypoints/test_dossier_cms_api.py`

- [ ] **Step 1: Escrever o teste de integração falhando para hidratação de `cms_pages` e revisão por área**

Criar `tests/integration/entrypoints/test_dossier_cms_api.py` testando:
1. `GET /v1/analyses/{analysis_id}` retorna `dossier.presentation.cms_pages` completo com as 9 subpáginas (inclusive para dossiês salvos antes da existência de `cms_pages`, via hidratação em tempo de leitura).
2. `POST /v1/analyses/{analysis_id}/area-reviews` com `{"area": "marketing", "status": "APPROVED", "reviewer_name": "Ana Ribeiro", "comment": "Demanda validada."}` persiste a revisão na tabela `dossier_area_reviews`, incrementa a versão exibida na aba `Revisões` (`v1.1`), atualiza o progresso geral (`25%` para 1 de 4 áreas aprovadas) e adiciona o comentário ao feed.
3. Isolamento multi-tenant: outra instituição não consegue ler nem publicar revisões de área em `analysis_id` alheio (`404`).

- [ ] **Step 2: Executar o teste de integração para confirmar a falha inicial**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/integration/entrypoints/test_dossier_cms_api.py
```
Expected: `FAIL` (endpoint `POST /v1/analyses/{id}/area-reviews` inexistente / `404` ou `405`).

- [ ] **Step 3: Criar `DossierAreaReviewModel`, migração `0013_dossier_area_reviews.py` e endpoints em `app.py`**

1. Em `src/prometeus/infrastructure/db/models.py`, adicionar `DossierAreaReviewModel` (`__tablename__ = "dossier_area_reviews"`) com colunas `id`, `analysis_id`, `tenant_id`, `area` (`marketing | produto | comercial | financeiro`), `status` (`APPROVED | IN_REVIEW | PENDING | CHANGES_REQUESTED`), `reviewer_name`, `comment`, `version_label`, `created_at`, `updated_at` e relacionamento `area_reviews` em `AnalysisModel`.
2. Criar `migrations/versions/0013_dossier_area_reviews.py` com `upgrade()` e `downgrade()`.
3. Em `src/prometeus/entrypoints/rest/app.py`:
   - Criar helper `_enrich_dossier_cms_pages(analysis, dossier_dict)` que garante `presentation["cms_pages"]` em qualquer dossiê retornado por `GET /v1/analyses` e `GET /v1/analyses/{analysis_id}` e mescla as revisões humanas (`analysis.area_reviews` + `analysis.human_decisions`) na subpágina `revisions` e as fontes reais (`analysis.tool_runs` + `analysis.evidences`) na subpágina `sources_evidences`.
   - Adicionar `POST /v1/analyses/{analysis_id}/area-reviews` validado por Pydantic (`AreaReviewRequest`), respeitando isolamento por `tenant_id`.

- [ ] **Step 4: Executar os testes de integração para confirmar aprovação**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/integration/entrypoints/test_dossier_cms_api.py
```
Expected: `PASS`.

- [ ] **Step 5: Commit da Task 2**

Run:
```powershell
rtk git add migrations/versions/0013_dossier_area_reviews.py src/prometeus/infrastructure/db/models.py src/prometeus/entrypoints/rest/app.py tests/integration/entrypoints/test_dossier_cms_api.py
rtk git commit -m "feat(api): persist area reviews in SQL and hydrate 9-subpage CMS dossier"
```

---

## Task 3: Design System Dark-Theme, Store de Subpáginas e Renderizadores das 9 Abas (`web/`)

**Files:**
- Create: `web/js/views/dossier-cms-tabs.js`
- Modify: `web/js/store.js`
- Modify: `web/js/api.js`
- Modify: `web/js/views/dossier-view.js`
- Modify: `web/styles/app.css`
- Test: `tests/operational/test_dossier_cms_subpages_rendering.py`

- [ ] **Step 1: Escrever o teste operacional falhando para o layout de 9 subpáginas e gráficos Dark Theme**

Criar `tests/operational/test_dossier_cms_subpages_rendering.py` verificando via Node ESM que:
1. `renderDossierView` renderiza a barra superior do CMS com todas as 9 subpáginas (`Visão Geral`, `Métricas-Chave`, `Concorrência Fixa`, `Radar Setorial`, `Economia & Cenários`, `SWOT & TOWS`, `Pilares de Viabilidade`, `Revisões`, `Fontes & Evidências`), o *breadcrumb* (`Dossiês`, nome do curso, aba ativa) e botões de ação (`Exportar`, `Compartilhar`).
2. Ao alternar `activeDossierTab` no `store` para cada uma das 9 chaves (`overview`, `key_metrics`, `fixed_competition`, `sector_radar`, `economics`, `swot_tows`, `viability_pillars`, `revisions`, `sources_evidences`), o template correspondente é destacado e seus cards, matrizes e gráficos SVG (`cms-donut-chart`, `cms-radar-chart`, `cms-waterfall-chart`, `cms-positioning-map`, `cms-funnel-chart`) são renderizados sem erros.
3. Todos os textos permanecem escapados contra XSS (`<script>` nunca executa) e os botões `inspectionButton` continuam abrindo o drawer de evidências.
4. O conjunto completo de testes legados em `tests/operational/test_dossier_view_rendering.py` continua passando sem regressão.

- [ ] **Step 2: Executar o teste operacional para confirmar a falha inicial**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/operational/test_dossier_cms_subpages_rendering.py
```
Expected: `FAIL`.

- [ ] **Step 3: Implementar `web/js/views/dossier-cms-tabs.js`, atualizar `store.js`, `api.js`, `dossier-view.js` e `web/styles/app.css`**

1. **`web/js/store.js`:** Adicionar `activeDossierTab: 'overview'` ao estado inicial e `setActiveDossierTab(tabId)` ao store.
2. **`web/js/api.js`:** Adicionar `submitDossierAreaReview(analysisId, reviewPayload)` chamando `POST /v1/analyses/${analysisId}/area-reviews`.
3. **`web/js/views/dossier-cms-tabs.js`:**
   - Criar um fallback client-side determinístico (`ensureCmsPages(dossier, course)`) para que mesmo quando `renderDossierView` for chamado em testes unitários/operacionais com um payload mínimo de `dossier` (sem passar pelo backend), o objeto `cms_pages` das 9 subpáginas seja sintetizado em memória com a mesma estrutura canônica.
   - Implementar os primitivos gráficos SVG/CSS em Dark Theme:
     - `renderDonutGaugeSvg(value, max, label, sublabel, tone)` (usado em Pilares de Viabilidade, Revisões e Fontes & Evidências).
     - `renderHorizontalBars(items)` (usado em Visão Geral, Radar Setorial e Fontes & Evidências).
     - `renderPositioningMap2x2Svg(points, opportunityZone)` (usado em Concorrência Fixa).
     - `renderRadar6AxesSvg(axes)` (usado em Radar Setorial).
     - `renderWaterfallChartSvg(steps)` (usado em Economia & Cenários).
     - `renderFunnelSvg(stages)` (usado em Métricas-Chave).
   - Implementar os 9 renderizadores fiéis às capturas de referência em Dark Theme:
     - `renderOverviewTab(page, dossier, helpers)`
     - `renderKeyMetricsTab(page, dossier, helpers)`
     - `renderFixedCompetitionTab(page, dossier, helpers)`
     - `renderSectorRadarTab(page, dossier, helpers)`
     - `renderEconomicsTab(page, dossier, helpers)`
     - `renderSwotTowsTab(page, dossier, helpers)`
     - `renderViabilityPillarsTab(page, dossier, helpers)`
     - `renderRevisionsTab(page, dossier, course, helpers)` (incluindo formulário inline para registrar aprovação/revisão por área: Marketing, Produto, Comercial, Financeiro)
     - `renderSourcesEvidencesTab(page, dossier, helpers)`
4. **`web/js/views/dossier-view.js`:**
   - Renderizar no topo do dossiê o **CMS Navigation Shell** (barra horizontal com as 9 subpáginas, *breadcrumb*, cabeçalho da subpágina ativa, status pill e botões `Exportar` / `Compartilhar`).
   - Renderizar o painel principal da subpágina ativa e manter as demais subpáginas e o bloco de **Auditoria Metodológica & Diagnóstico Integral** acessíveis no DOM (com controle de visibilidade por aba/acordeão) para que:
     - a troca de abas seja instantânea;
     - a impressão/exportação e os testes operacionais de auditoria (`test_dossier_view_rendering.py`) encontrem todos os elementos `#sec-*` sem qualquer quebra.
5. **`web/styles/app.css`:**
   - Adicionar classes `.cms-dossier-shell`, `.cms-subnav`, `.cms-subnav__tab`, `.cms-breadcrumb`, `.cms-page-header`, `.cms-kpi-grid`, `.cms-kpi-card`, `.cms-card`, `.cms-matrix-table`, `.cms-swot-grid`, `.cms-tows-grid`, `.cms-pillar-grid`, `.cms-revision-timeline`, `.cms-method-pipeline` usando exclusivamente os tokens escuros de `tokens.css` (`--prometeus-bg-canvas`, `--prometeus-surface-card`, `--prometeus-border-card`, `--prometeus-primary`, `--prometeus-status-*`).

- [ ] **Step 4: Executar todos os testes operacionais de renderização**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest tests/operational/test_dossier_cms_subpages_rendering.py tests/operational/test_dossier_view_rendering.py
```
Expected: `PASS` em 100% dos testes novos e existentes.

- [ ] **Step 5: Commit da Task 3**

Run:
```powershell
rtk git add web/js/store.js web/js/api.js web/js/views/dossier-cms-tabs.js web/js/views/dossier-view.js web/styles/app.css tests/operational/test_dossier_cms_subpages_rendering.py
rtk git commit -m "feat(web): implement dark-theme 9-subpage CMS dossier interface and charts"
```

---

## Task 4: Documentação Canônica, Verificação Ponta a Ponta e Homologação Visual

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/plans/2026-11-10-cms-dossier-subpages.md`

- [ ] **Step 1: Atualizar `docs/README.md` com a referência ao contrato `cms_pages` e às 9 subpáginas do Dossiê Executivo**

Registrar em `docs/README.md` a arquitetura de publicação automática das 9 subpáginas do dossiê (`cms_pages`) e a tabela `dossier_area_reviews`.

- [ ] **Step 2: Executar a suíte completa de testes e linter**

Run:
```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk ruff check src tests
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; rtk pytest
```
Expected: `0` erros no `ruff` e `100%` dos testes passando.

- [x] **Step 3: Commit final da documentação**

---

### Task 5: Refinamento Visual Executivo ("Anti-AI-Slop") & Dossiê Showcase (`anl-stj-001`)

**Status:** VALIDADO (10/11/2026)

1. **KPI Cards em Layout Horizontal Split (`web/js/views/dossier-cms-tabs.js` & `web/styles/app.css`)**:
   - Topo com chip de ícone vetorial contextual (`getKpiIconSvg`) + rótulo executivo em sentence-case;
   - Rodapé dividido horizontalmente: métrica tabular gigante à esquerda (`font-variant-numeric: tabular-nums`) com sufixo de unidade leve (`<small class="cms-kpi-card__unit">` para `/100`, `players`, `matrículas`, `sinais`, `oportunidades`) e coluna de contexto à direita (pílula semântica de delta + sublabel comparativo);
   - Conformidade total com o detector `impeccable detect` (zero `border-left: 3px`, zero `text-transform: uppercase` com tracking exagerado).
2. **Gráficos Vetoriais Nativos (SVG) de Alta Precisão**:
   - **Aba 1 (`Visão Geral`)**: Barras horizontais com escala `0 | 20 | 40 | 60 | 80 | 100` e linhas de grade verticais + card do cenário `Base` destacado;
   - **Aba 2 (`Métricas-Chave`)**: Gráfico vetorial de Área + Linha (`renderHistoricalTrendSvg`), Funil Trapezoidal centralizado (`.cms-funnel-stage`) e Trajetória Dual-Line IE vs. IVO (`renderIeIvoTrajectorySvg` com linha tracejada `Limiar 75`);
   - **Aba 3 (`Concorrência Fixa`)**: Badges monogramáticos institucionais (`FGV`, `INS`, `PUC`, `IBM`, `ESA`) + Mapa de Posicionamento 2×2 (`renderPositioning2x2Svg`) com elipse tracejada esmeralda `Espaço de oportunidade (ENS)` quando há ofertas comparáveis medidas;
   - **Aba 4 (`Radar Setorial`)**: Radar Hexagonal de 6 eixos (`renderRadarSvg` com anéis `20..100` e polígono de referência) + Mapa Setorial 2D de Clusters (`renderSectorBubbleMapSvg`);
   - **Aba 5 (`Economia & Cenários`)**: Gráfico **Waterfall / Floating Bridge** vetorial (`renderWaterfallSvg` — `Receita Bruta` ancorada em 0, barras flutuantes de deduções/custos em coral `#f87171` com conectores tracejados e `Resultado Líquido` ancorado em esmeralda `#34d399`) + Matriz `Preço × Volume` com linha/coluna/célula `Base` destacadas.
3. **Dossiê Showcase Completo no SQLite (`scripts/seed_stj_showcase_dossier.py` -> `anl-stj-001`)**:
   - Baseado no curso real *DIREITO DOS SEGUROS NOS TRIBUNAIS SUPERIORES: Recursos Excepcionais, Relevância da Questão Federal e Formação de Precedentes* (Extensão, 24h, Online ao vivo, 6 módulos de 4h, 8 docentes doutores);
   - Gerado pelos construtores determinísticos (`DossierSynthesisService._build_visual_presentation_blocks`) e validado sem divergências por `DossierVerifier().verify_presentation(...)`.


