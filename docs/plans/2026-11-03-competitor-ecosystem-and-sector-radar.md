# Ecossistema de Concorrentes Fixos e Radar Setorial Permanente (ENS) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatizar o monitoramento dos 10 concorrentes educacionais fixos e do Radar Setorial Permanente das 10 seguradoras de referência da ENS desde a configuração do tenant até a coleta Apify, isolamento semântico, persistência de snapshots, formulário web sem atrito e novas seções visuais do Dossiê Executivo.

**Architecture:** Estende o monólito modular (`TenantConfig`) com um catálogo tipado e imutável por instituição (`competitors` educacionais vs `sector_radar` de seguradoras), congelado no snapshot de cada análise. O planejador de pesquisa gera consultas clusterizadas por domínio/rede respeitando o teto de orçamento Apify e limites de operadores de busca, enquanto a qualificação e a referência de preço isolam deterministicamente seguradoras (contexto setorial/demanda/dores de corretores) de concorrentes acadêmicos (oferta/ementa/preço), alimentando dois novos blocos visuais auditáveis no Dossiê Web.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, SQLAlchemy 2.0 + Alembic, Apify Actors pinados (`owner/name@build`), Vanilla ES Modules + CSS Tokens (`web/js/`, `web/styles/app.css`), Pytest.

**Spec:** Levantamento institucional `Benchmark_Redes_Sociais_Seguradoras_ENS_Atualizado.docx`, `AGENTS.md`, `docs/operations/configuration.md` e `docs/agent/workflow.md`.

## Global Constraints

- Nenhuma LLM ou JEV pode executar fórmulas financeiras, cálculo de referência de preço, permissões ou transições de estado sem validação em código (`AGENTS.md` regra 4).
- Conteúdo raspado de sites e redes de concorrentes e seguradoras é dado não confiável (`untrusted_evidence`), devendo passar por `EvidenceSanitizer` antes de persistência ou projeção em prompt (`AGENTS.md` regra 5).
- Seguradoras do `sector_radar` (Porto, Bradesco, Tokio Marine, Allianz, HDI, MAPFRE, Brasilseg/BB, Zurich, Itaú, Yelum) **jamais** podem ser contabilizadas como ofertas concorrentes diretas nem entrar no cálculo de `reference_mean_price_brl`.
- Perfis sociais marcados como `Não confirmado` no levantamento ENS (`brasilseg-bb`, `itau-seguros`, `yelum-seguros`, `hdi-seguros` no Instagram; `itau-seguros` no LinkedIn) não devem ter handles inventados; perfis LinkedIn de escopo `global` (`mapfre`, `zurich-seguros`) não podem ser comparados como audiência nacional brasileira.
- Análises e dossiês já concluídos permanecem imutáveis; a configuração do ecossistema é congelada em `proposal_data["_institution_context"]` e `tenant_config_snapshot` no momento da criação da análise.
- Actors Apify permanecem estritamente allowlisted e pinados (`owner/name@build`), respeitando `APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS` sem estouro de orçamento.

## Review Focus

- **Truncamento silencioso do Google Search (> 32 termos na query):** agrupar no máximo 5 domínios `site:` por chamada e limitar o tópico extraído a até 4 palavras-chave nucleares (`len(query.split()) <= 28`), testado em `Task 3`.
- **Contaminação de preço por página de seguradora:** página de produto securitário (ex.: prêmio de seguro ou franquia em `portoseguro.com.br`) capturada como `OFFER` deve ser barrada em `qualify_market_evidence.py` e `pricing_reference.py` com código `sector_ecosystem_not_course_offer`, testado em `Task 2`.
- **Handles sociais não confirmados e LinkedIn global:** perfis sem handle confirmado não geram chamadas de perfil no Instagram, e sinais de LinkedIn `global` recebem selo explícito `Global (contextual)` e bloqueio contra alegação de audiência nacional em `DossierVerifier`, testado em `Task 1` e `Task 2`.
- **Degradação graciosa sob orçamento Apify reduzido (`< US$ 1.50`):** o injetor de sementes reduz chamadas para o cluster prioritário sem lançar `ApifyBudgetExceededError`, testado em `Task 3`.
- **Retrocompatibilidade de tenants e dossiês antigos:** carregar `infnet.example.yaml` (sem chave `ecosystem`) e renderizar dossiês já salvos (sem `presentation.competitive_benchmark` ou `presentation.sector_radar`) funciona sem erro em Python e no frontend JS, testado em `Task 1` e `Task 5`.

---

## Mapa de Arquivos

- **Domínio & Configuração:**
  - `src/prometeus/domain/configuration.py` — schemas `SocialChannelsConfig`, `CompetitorProfileConfig`, `SectorRadarActorConfig`, `TenantEcosystemConfig` e validações cruzadas de domínio/URL.
  - `config/tenants/ens.example.yaml` — cadastro canônico dos 10 concorrentes educacionais e das 10 seguradoras do Radar Setorial ENS.
  - `src/prometeus/application/create_analysis.py` — congelamento de `competitors` e `sector_radar` em `_institution_context`.
- **Isolamento Semântico, Escopo & Verificação:**
  - `src/prometeus/application/research_scope.py` — matchers determinísticos de domínio/handle para concorrentes fixos e atores do radar setorial.
  - `src/prometeus/application/qualify_market_evidence.py` — roteamento de evidências de `sector_radar` para contexto/demanda/currículo e bloqueio em `direct_competition`/`pricing`.
  - `src/prometeus/application/pricing_reference.py` — exclusão explícita de domínios `sector_radar`.
  - `src/prometeus/application/dossier_verifier.py` — invariantes `sector_actor_as_direct_competitor` e `global_social_metric_as_national`.
- **Planejamento de Pesquisa & Radar Setorial Permanente:**
  - `src/prometeus/application/plan_course_research.py` — geração clusterizada de buscas em concorrentes fixos e seguradoras + preservação de busca aberta.
  - `skills/planning-market-research/SKILL.md` — diretrizes de uso das listas institucionais sem limitar descoberta aberta (bump de versão).
  - `migrations/versions/0012_sector_radar_snapshots.py` & `src/prometeus/infrastructure/db/models.py` — tabela `sector_radar_snapshots`.
  - `src/prometeus/application/sector_radar.py` — `SectorRadarService` (coleta periódica/sob demanda com TTL, orçamento próprio e higienização).
  - `src/prometeus/entrypoints/cli/main.py` — comando `radar-refresh`.
  - `src/prometeus/application/run_course_analysis.py` — injeção do ecossistema no planejador, qualificador, referência de preço e baseline do radar.
- **Dossiê Executivo & Interface Web:**
  - `src/prometeus/application/synthesize_dossier.py` — blocos estruturados `competitive_benchmark` e `sector_radar` em `_build_visual_presentation_blocks`.
  - `skills/building-course-offers/SKILL.md` — regras de síntese separando concorrentes acadêmicos de sinais do ecossistema segurador (bump de versão).
  - `src/prometeus/entrypoints/rest/app.py` — endpoints `GET /v1/tenants/{tenant_id}/ecosystem` e `POST /v1/tenants/{tenant_id}/sector-radar/refresh`.
  - `web/js/store.js`, `web/js/views/intake-view.js`, `web/js/views/dossier-view.js`, `web/styles/app.css` — painel automático no intake e seções visuais de Concorrência Educacional e Radar das Seguradoras no dossiê web.

---

### Task 1: Modelo Canônico do Ecossistema Institucional e Cadastro ENS

**Files:**
- Modify: `src/prometeus/domain/configuration.py`
- Modify: `config/tenants/ens.example.yaml`
- Modify: `src/prometeus/application/create_analysis.py`
- Test: `tests/unit/domain/test_tenant_ecosystem_config.py`

**Interfaces:**
- Produces:
  - `SocialChannelsConfig`, `CompetitorProfileConfig`, `SectorRadarActorConfig`, `TenantEcosystemConfig` em `prometeus.domain.configuration`
  - `TenantConfig.ecosystem: TenantEcosystemConfig`
  - Snapshot em `proposal_data["_institution_context"]` contendo `id`, `name`, `domains`, `competitors` e `sector_radar`.

- [ ] **Step 1: Write the failing test in `tests/unit/domain/test_tenant_ecosystem_config.py`**

```python
from pathlib import Path
import pytest
from prometeus.domain.configuration import ConfigurationError, TenantConfig, load_tenant_config


def test_ens_tenant_config_loads_ten_competitors_and_ten_sector_insurers():
    cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    assert len(cfg.ecosystem.competitors) == 10
    assert len(cfg.ecosystem.sector_radar) == 10

    comp_ids = {c.id for c in cfg.ecosystem.competitors}
    assert {"conhecer-seguros", "fgv", "ibmec", "fipecafi", "fia", "insper", "estacio", "esa-oab", "fiap", "alura"} == comp_ids

    primary_insurers = {s.id for s in cfg.ecosystem.sector_radar if s.priority == "primary"}
    assert primary_insurers == {"porto-seguro", "bradesco-seguros", "tokio-marine", "allianz-seguros", "hdi-seguros"}

    by_id = {s.id: s for s in cfg.ecosystem.sector_radar}
    assert by_id["mapfre"].social.linkedin_scope == "global"
    assert by_id["zurich-seguros"].social.linkedin_scope == "global"
    assert by_id["itau-seguros"].social.instagram_handle is None
    assert by_id["hdi-seguros"].social.instagram_handle is None


def test_infnet_tenant_without_ecosystem_remains_backward_compatible():
    cfg = load_tenant_config(Path("config/tenants/infnet.example.yaml"))
    assert cfg.ecosystem.competitors == []
    assert cfg.ecosystem.sector_radar == []


def test_rejects_domain_collision_between_competitors_and_sector_radar():
    with pytest.raises(ConfigurationError):
        TenantConfig.model_validate({
            "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
            "ecosystem": {
                "competitors": [{"id": "c1", "name": "C1", "category": "direct_specialist", "domains": ["portoseguro.com.br"]}],
                "sector_radar": [{"id": "s1", "name": "Porto", "domains": ["portoseguro.com.br"]}],
            },
        })


def test_rejects_non_https_social_or_portal_urls():
    with pytest.raises(ValueError):
        TenantConfig.model_validate({
            "institution": {"id": "ens", "display_name": "ENS", "domains": ["ens.edu.br"]},
            "ecosystem": {
                "competitors": [{
                    "id": "c1",
                    "name": "C1",
                    "category": "direct_specialist",
                    "domains": ["exemplo.edu.br"],
                    "portal_url": "http://exemplo.edu.br/pos",
                }],
            },
        })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/unit/domain/test_tenant_ecosystem_config.py -v`
Expected: FAIL (`AttributeError: 'TenantConfig' object has no attribute 'ecosystem'`)

- [ ] **Step 3: Implement ecosystem models in `src/prometeus/domain/configuration.py`, populate `config/tenants/ens.example.yaml`, and freeze snapshot in `src/prometeus/application/create_analysis.py`**

Implement `SocialChannelsConfig`, `CompetitorProfileConfig`, `SectorRadarActorConfig`, and `TenantEcosystemConfig` with domain normalization (`lowercase`, strip `www.`), `https://` URL validation, and cross-set collision checks (`institution.domains ∩ competitors.domains ∩ sector_radar.domains == ∅`) raising `ConfigurationError` in `load_tenant_config` / `model_validator`. Populate all 10 competitors and 10 insurers in `config/tenants/ens.example.yaml` matching `Benchmark_Redes_Sociais_Seguradoras_ENS_Atualizado.docx`. Update `CreateAnalysisUseCase.execute` to include `competitors` and `sector_radar` serialized dicts inside `proposal_with_idempotency["_institution_context"]`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk pytest tests/unit/domain/test_tenant_ecosystem_config.py tests/unit/ -k "config or create_analysis" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/prometeus/domain/configuration.py config/tenants/ens.example.yaml src/prometeus/application/create_analysis.py tests/unit/domain/test_tenant_ecosystem_config.py
rtk git commit -m "feat(config): add tenant competitor and sector radar ecosystem models for ENS"
```

---

### Task 2: Blindagem Determinística e Semântica (Concorrente Educacional vs Seguradora vs ENS)

**Files:**
- Modify: `src/prometeus/application/research_scope.py`
- Modify: `src/prometeus/application/qualify_market_evidence.py`
- Modify: `src/prometeus/application/pricing_reference.py`
- Modify: `src/prometeus/application/dossier_verifier.py`
- Test: `tests/unit/application/test_ecosystem_evidence_isolation.py`

**Interfaces:**
- Consumes: `institution_context` dict (`domains`, `competitors`, `sector_radar`) from Task 1.
- Produces:
  - `match_configured_competitor(payload: dict[str, object], source_url: str, context: dict[str, object] | None) -> dict[str, object] | None`
  - `match_sector_radar_actor(payload: dict[str, object], source_url: str, context: dict[str, object] | None) -> dict[str, object] | None`
  - Qualification fields on `sanitized_data["_qualification"]`: `actor_role`, `matched_actor_id`, `matched_actor_name`, `linkedin_scope`.
  - Updated `build_price_reference(..., sector_radar_domains: list[str] | None = None) -> dict[str, Any]`.
  - New `DossierVerifier` checks: `sector_actor_as_direct_competitor` and `global_social_metric_as_national`.

- [ ] **Step 1: Write the failing tests in `tests/unit/application/test_ecosystem_evidence_isolation.py`**

```python
from prometeus.application.pricing_reference import build_price_reference
from prometeus.application.research_scope import (
    match_configured_competitor,
    match_sector_radar_actor,
)

ENS_CTX = {
    "id": "ens",
    "name": "Escola de Negócios e Seguros",
    "domains": ["ens.edu.br", "enscursos.com.br"],
    "competitors": [
        {"id": "ibmec", "name": "Ibmec", "aliases": ["pos ibmec"], "domains": ["ibmec.br", "pos.ibmec.br"], "social": {"instagram_handle": "ibmec"}},
        {"id": "conhecer-seguros", "name": "Conhecer Seguros", "aliases": [], "domains": ["conhecerseguros.com.br"], "social": {"instagram_handle": "conhecerseguros"}},
    ],
    "sector_radar": [
        {"id": "porto-seguro", "name": "Porto Seguro", "aliases": ["porto"], "domains": ["portoseguro.com.br"], "social": {"instagram_handle": "porto", "linkedin_scope": "national"}},
        {"id": "mapfre", "name": "MAPFRE", "aliases": ["mapfre brasil"], "domains": ["mapfre.com.br"], "social": {"instagram_handle": "mapfrebrasil", "linkedin_scope": "global"}},
    ],
}


def test_matches_competitor_and_sector_actor_by_domain_and_handle():
    comp = match_configured_competitor({}, "https://pos.ibmec.br/mba-financas-e-riscos", ENS_CTX)
    assert comp is not None and comp["id"] == "ibmec"

    insurer = match_sector_radar_actor({"ownerUsername": "porto"}, "https://www.instagram.com/p/xyz/", ENS_CTX)
    assert insurer is not None and insurer["id"] == "porto-seguro"


def test_pricing_reference_excludes_sector_radar_domains_even_if_price_present():
    audit = build_price_reference(
        course_title="MBA em Inteligência Artificial Aplicada a Seguros",
        level="MBA Executivo",
        institution_name="Escola de Negócios e Seguros",
        institution_domains=["ens.edu.br"],
        sector_radar_domains=["portoseguro.com.br", "bradescoseguros.com.br"],
        internal_prices=[],
        offers=[
            {
                "id": "ev-porto-1",
                "title": "MBA Executivo Seguros e IA Corporativa",
                "source_url": "https://www.portoseguro.com.br/treinamento-corretores",
                "sanitized_data": {"total_price": 4500.0, "_qualification": {"accepted": True}},
            },
            {
                "id": "ev-ibmec-1",
                "title": "MBA em Inteligência Artificial e Gestão de Riscos em Seguros",
                "source_url": "https://pos.ibmec.br/mba-ia-seguros",
                "sanitized_data": {"total_price": 16800.0, "_qualification": {"accepted": True}},
            },
        ],
    )
    assert audit["external_count"] == 1
    assert any(x["id"] == "ev-porto-1" and x["reason_code"] == "sector_ecosystem_not_course_offer" for x in audit["excluded"])
```

Add unit tests in the same file asserting:
1. `EvidenceQualificationService.qualify` sets `actor_role="sector_radar"`, `context_only=True`, `direct_competition.usable=False` (`rejection_cause="sector_ecosystem_not_educational_competitor"`), and `pricing.usable=False` for `portoseguro.com.br` items.
2. `DossierVerifier` flags `sector_actor_as_direct_competitor` if `"Porto Seguro"` or `"Bradesco Seguros"` appears as an unqualified competitor in `highlights.competitors`, and flags `global_social_metric_as_national` when a claim attributes MAPFRE/Zurich global LinkedIn audience to Brazil.

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/unit/application/test_ecosystem_evidence_isolation.py -v`
Expected: FAIL (`ImportError: cannot import name 'match_configured_competitor'`)

- [ ] **Step 3: Implement matchers, qualification routing, pricing exclusion, and verifier rules**

1. In `src/prometeus/application/research_scope.py`: implement `match_configured_competitor` and `match_sector_radar_actor` matching normalized hostnames/subdomains (`urlsplit`) and social handles (`ownerUsername`, `pageName`, `page_name`, `advertiser_name`).
2. In `src/prometeus/application/qualify_market_evidence.py`: bump `QUALIFICATION_VERSION = 4` (so cache invalidates cleanly when actor role logic updates), compute `sector_actor = match_sector_radar_actor(...)` and `comp_actor = match_configured_competitor(...)`, enforce `relevant = False` and `context_only = True` for `sector_actor` on `OFFER`/`PAID_COMPETITION` while keeping `use_for = ["sector_radar", "audience_needs", "curriculum"]` when scoped & trusted, and persist `actor_role`, `matched_actor_id`, `matched_actor_name`, `linkedin_scope` inside `_qualification`.
3. In `src/prometeus/application/pricing_reference.py`: add optional `sector_radar_domains: list[str] | None = None` to `build_price_reference` and exclude matching hosts or `qualification.get("actor_role") == "sector_radar"` with `reason_code = "sector_ecosystem_not_course_offer"`.
4. In `src/prometeus/application/dossier_verifier.py`: enforce `sector_actor_as_direct_competitor` and `global_social_metric_as_national`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk pytest tests/unit/application/test_ecosystem_evidence_isolation.py tests/unit/dossiers/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/prometeus/application/research_scope.py src/prometeus/application/qualify_market_evidence.py src/prometeus/application/pricing_reference.py src/prometeus/application/dossier_verifier.py tests/unit/application/test_ecosystem_evidence_isolation.py
rtk git commit -m "feat(qualification): isolate sector radar insurers from educational competitors and pricing"
```

---

### Task 3: Planejamento de Pesquisa Clusterizado por Ecossistema (Respeitando Orçamento Apify)

**Files:**
- Modify: `src/prometeus/application/plan_course_research.py`
- Modify: `src/prometeus/application/run_course_analysis.py`
- Modify: `skills/planning-market-research/SKILL.md`
- Test: `tests/unit/application/test_ecosystem_research_planning.py`

**Interfaces:**
- Consumes: `TenantEcosystemConfig` (Task 1), `match_configured_competitor` / `match_sector_radar_actor` (Task 2).
- Produces:
  - `build_ecosystem_seed_calls(understanding: CourseUnderstanding, ecosystem: TenantEcosystemConfig, allowed_capabilities: list[str], budget_usd: float) -> tuple[list[ResearchQuestion], list[PlannedToolCall]]` in `plan_course_research.py`
  - `CourseResearchPlanner.plan(..., ecosystem: TenantEcosystemConfig | None = None) -> CourseResearchPlan`

- [ ] **Step 1: Write the failing tests in `tests/unit/application/test_ecosystem_research_planning.py`**

Write tests verifying:
1. With full ENS `ecosystem` and `budget_usd=5.0`, `CourseResearchPlanner.plan` produces:
   - Clustered `google_search` calls covering all 10 educational competitor domains (`<= 5` `site:` domains per query and `<= 28` whitespace-separated tokens per query).
   - A `web_crawler` call whose `parameters["depends_on"]` includes the competitor `google_search` call IDs (never raw hallucinated URLs).
   - At least 1 open-market `google_search` call without `site:` operator (preserving broad discovery).
   - Sector radar `google_search` call(s) covering the 10 insurer domains (primary cluster first) linked to `q-sector-radar` (`ResearchTrack.WORKFORCE_NEEDS`), plus social listening calls that skip `unconfirmed` Instagram handles (`itau-seguros`, `hdi-seguros`, `yelum-seguros`, `brasilseg-bb`).
2. With constrained budget `budget_usd=1.10`, `build_ecosystem_seed_calls` degrades to compact competitor + primary 5 insurers (`porto-seguro`, `bradesco-seguros`, `tokio-marine`, `allianz-seguros`, `hdi-seguros`) without exceeding budget.

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/unit/application/test_ecosystem_research_planning.py -v`
Expected: FAIL (`TypeError: CourseResearchPlanner.plan() got an unexpected keyword argument 'ecosystem'`)

- [ ] **Step 3: Implement `build_ecosystem_seed_calls`, wire `CourseResearchPlanner.plan` and `run_course_analysis.py`, and update `skills/planning-market-research/SKILL.md`**

1. Implement `compact_topic_terms(understanding: CourseUnderstanding, max_tokens: int = 4) -> str` and `build_ecosystem_seed_calls(...)` in `src/prometeus/application/plan_course_research.py`.
2. Pass serialized summary of `ecosystem.competitors` and `ecosystem.sector_radar` into the planner prompt context AND deterministically merge missing ecosystem seed calls (when `gaps is None` and `ecosystem` is non-empty) prior to deduplication and `depends_on` normalization.
3. Update `skills/planning-market-research/SKILL.md` (bump `**Version:**` patch/minor) instructing the planner on dual-track ecosystem usage (competitor course comparison vs insurer demand/theme radar).
4. In `src/prometeus/application/run_course_analysis.py`, load `TenantEcosystemConfig` from the frozen `analysis` snapshot (`_institution_context` / config snapshot) and pass it into `CourseResearchPlanner.plan(...)`, `qualifier.qualify(..., institution_context=...)`, and `build_price_reference(..., sector_radar_domains=...)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk pytest tests/unit/application/test_ecosystem_research_planning.py tests/unit/application/test_plan_course_research.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/prometeus/application/plan_course_research.py src/prometeus/application/run_course_analysis.py skills/planning-market-research/SKILL.md tests/unit/application/test_ecosystem_research_planning.py
rtk git commit -m "feat(research): add clustered competitor and sector radar query planning"
```

---

### Task 4: Serviço e Persistência do "Radar Setorial Permanente" (`SectorRadarService`)

**Files:**
- Create: `migrations/versions/0012_sector_radar_snapshots.py`
- Modify: `src/prometeus/infrastructure/db/models.py`
- Create: `src/prometeus/application/sector_radar.py`
- Modify: `src/prometeus/entrypoints/cli/main.py`
- Modify: `src/prometeus/application/run_course_analysis.py`
- Test: `tests/integration/market_sources/test_sector_radar_service.py`

**Interfaces:**
- Consumes: `TenantConfig` (Task 1), `ApifyClient` / `MarketSourcePort`, `EvidenceSanitizer`.
- Produces:
  - `SectorRadarSnapshotModel` in `src/prometeus/infrastructure/db/models.py` (`id`, `tenant_id`, `status`, `collected_at`, `expires_at`, `monitored_actors_count`, `covered_actors`, `signals`, `trending_themes`, `spent_usd`, `config_hash`).
  - `SectorRadarSignal(ImmutableModel)` and `SectorRadarService` in `src/prometeus/application/sector_radar.py`:
    - `async get_latest_snapshot(tenant_id: str, include_expired: bool = False) -> SectorRadarSnapshotModel | None`
    - `async refresh_radar(tenant_id: str, tenant_config: TenantConfig, *, max_budget_usd: float = 1.50, force: bool = False) -> SectorRadarSnapshotModel`
  - CLI command: `prometeus radar-refresh --tenant ens [--force] [--max-budget-usd 1.50]`

- [ ] **Step 1: Write the failing integration test in `tests/integration/market_sources/test_sector_radar_service.py`**

Test scenarios with SQLite async session + fake collector:
1. `refresh_radar` collects institutional web + confirmed national social signals for ENS's `sector_radar`, sanitizes HTML/PII via `EvidenceSanitizer`, extracts `SectorRadarSignal` items tagged with `actor_id` (`porto-seguro`, `bradesco-seguros`, etc.) and `scope_badge`, and persists a `READY` snapshot with `expires_at = collected_at + timedelta(hours=168)`.
2. Calling `refresh_radar` again before expiration with `force=False` returns the cached snapshot with `$0.00` extra spend.
3. Partial source failure marks the snapshot `PARTIAL` (preserving valid signals) rather than crashing.

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/integration/market_sources/test_sector_radar_service.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'prometeus.application.sector_radar'`)

- [ ] **Step 3: Create migration `0012_sector_radar_snapshots.py`, `SectorRadarSnapshotModel`, `SectorRadarService`, CLI subcommand, and hook baseline into `run_course_analysis.py`**

1. Add `SectorRadarSnapshotModel` to `src/prometeus/infrastructure/db/models.py` and create Alembic migration `0012_sector_radar_snapshots.py` chaining from `0011_execution_envelopes`.
2. Implement `SectorRadarService` in `src/prometeus/application/sector_radar.py` enforcing budget ceiling, untrusted-data sanitization, and TTL caching.
3. Add `radar-refresh` command in `src/prometeus/entrypoints/cli/main.py`.
4. In `src/prometeus/application/run_course_analysis.py`, read `await SectorRadarService(self.session, ...).get_latest_snapshot(analysis.tenant_id)` during evidence consolidation and attach its metadata/signals to `analysis_audit["sector_radar_baseline"]` as verified contextual provenance.

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk pytest tests/integration/market_sources/test_sector_radar_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add migrations/versions/0012_sector_radar_snapshots.py src/prometeus/infrastructure/db/models.py src/prometeus/application/sector_radar.py src/prometeus/entrypoints/cli/main.py src/prometeus/application/run_course_analysis.py tests/integration/market_sources/test_sector_radar_service.py
rtk git commit -m "feat(radar): add persistent SectorRadarService snapshots and CLI refresh"
```

---

### Task 5: Atualização do Dossiê e Dossiê Visual Web (Matriz de Concorrentes + Pulso do Radar Setorial)

**Files:**
- Modify: `src/prometeus/application/synthesize_dossier.py`
- Modify: `skills/building-course-offers/SKILL.md`
- Modify: `web/js/views/dossier-view.js`
- Modify: `web/styles/app.css`
- Test: `tests/unit/dossiers/test_ecosystem_presentation_blocks.py`
- Test: `tests/operational/test_dossier_view_rendering.py`

**Interfaces:**
- Consumes: `_qualification` actor matches (Task 2), `sector_radar_baseline` (Task 4), `DossierFacts` & `DossierOutput`.
- Produces:
  - `presentation["competitive_benchmark"]`: `{monitored_total, offers_found_count, whitespace_summary, rows: [{competitor_id, name, category_label, status, observed_offer_title, modality, workload_hours, price_display, ens_differentiation, evidence_ids}]}`
  - `presentation["sector_radar"]`: `{monitored_insurers_total, baseline_collected_at, signals_count, executive_pulse, signals: [{actor_id, insurer_name, priority, channel_label, scope_badge, theme_detected, market_or_broker_pain, curriculum_link, source_url, evidence_ids}]}`
  - Visual sections `#sec-competitive-benchmark` and `#sec-sector-radar` in `web/js/views/dossier-view.js`.

- [ ] **Step 1: Write failing unit & operational rendering tests**

1. In `tests/unit/dossiers/test_ecosystem_presentation_blocks.py`: verify `_build_visual_presentation_blocks` builds `competitive_benchmark` (distinguishing `direct_offer`, `adjacent_offer`, `no_offer_observed`, and `not_queried` without inventing prices or courses) and `sector_radar` (grouping observed signals from Porto/Bradesco/Tokio/Allianz/MAPFRE with `scope_badge="Global (contextual)"` on global LinkedIn signals and preserving `evidence_ids`).
2. In `tests/operational/test_dossier_view_rendering.py`: verify `renderDossierView` renders `#sec-competitive-benchmark` and `#sec-sector-radar` when present, AND renders legacy dossiers (without those keys) cleanly with zero errors while keeping all existing audit sections intact.

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk pytest tests/unit/dossiers/test_ecosystem_presentation_blocks.py tests/operational/test_dossier_view_rendering.py -v`
Expected: FAIL (`KeyError: 'competitive_benchmark'`)

- [ ] **Step 3: Implement synthesis blocks, update `skills/building-course-offers/SKILL.md`, and render visual components in `dossier-view.js` + `app.css`**

1. In `src/prometeus/application/synthesize_dossier.py`: enrich `build_facts` so each `DossierFactItem` carries `actor_role`, `matched_actor_id`, `matched_actor_name`, and `linkedin_scope` in `key_metrics`, and compute `competitive_benchmark` + `sector_radar` deterministically in `_build_visual_presentation_blocks`.
2. Update `skills/building-course-offers/SKILL.md` (bump `**Version:**` to `2.1.0`) instructing synthesis to articulate both educational whitespace (vs the 10 competitors) and employer/broker demand signals (from the 10 insurers) without conflating them.
3. In `web/js/views/dossier-view.js` & `web/styles/app.css`: add `renderCompetitiveBenchmark(pres.competitive_benchmark)` and `renderSectorRadar(pres.sector_radar)` with subnav links, status badges, scope pills, and `inspectionButton(row.evidence_ids)` triggers, plus `sector_ecosystem_not_course_offer` label in `priceReason(...)`.

- [ ] **Step 4: Run all dossier and operational tests**

Run: `rtk pytest tests/unit/dossiers/ tests/integration/dossiers/ tests/operational/test_dossier_view_rendering.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/prometeus/application/synthesize_dossier.py skills/building-course-offers/SKILL.md web/js/views/dossier-view.js web/styles/app.css tests/unit/dossiers/test_ecosystem_presentation_blocks.py tests/operational/test_dossier_view_rendering.py
rtk git commit -m "feat(dossier): add competitive benchmark matrix and sector radar visual sections"
```

---

### Task 6: Endpoints REST de Ecossistema, Intake Sem Atrito e Documentação

**Files:**
- Modify: `src/prometeus/entrypoints/rest/app.py`
- Modify: `web/js/store.js`
- Modify: `web/js/views/intake-view.js`
- Modify: `docs/operations/configuration.md`
- Modify: `docs/agent/workflow.md`
- Test: `tests/integration/entrypoints/test_tenant_ecosystem_api.py`

**Interfaces:**
- Consumes: `load_tenant_config` (Task 1), `SectorRadarService` (Task 4).
- Produces:
  - `GET /v1/tenants/{tenant_id}/ecosystem` -> `{tenant_id, institution_name, competitors, sector_radar, allow_extra_intake_competitors, radar_status}`
  - `POST /v1/tenants/{tenant_id}/sector-radar/refresh` -> `{tenant_id, status, collected_at, expires_at, signals_count, spent_usd}`
  - Automatic ecosystem monitoring panel in `web/js/views/intake-view.js`.

- [ ] **Step 1: Write failing API integration test in `tests/integration/entrypoints/test_tenant_ecosystem_api.py`**

Test `GET /v1/tenants/ens/ecosystem` returns HTTP 200 with 10 `competitors`, 10 `sector_radar` entries, `radar_status`, and zero secret fields; test unknown tenant returns HTTP 404.

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/integration/entrypoints/test_tenant_ecosystem_api.py -v`
Expected: FAIL (`404 Not Found`)

- [ ] **Step 3: Implement REST endpoints, store sync, friction-free intake panel, and docs update**

1. Add `GET /v1/tenants/{tenant_id}/ecosystem` and `POST /v1/tenants/{tenant_id}/sector-radar/refresh` in `src/prometeus/entrypoints/rest/app.py` resolving `config/tenants/{tenant_id}.yaml` (falling back to `config/tenants/{tenant_id}.example.yaml` in development/homologation when matching `INSTITUTION_CONFIG_PATH`).
2. Add `loadTenantEcosystem()` in `web/js/store.js` called during initialization and `setTenant(tenantId)`.
3. In `web/js/views/intake-view.js`: replace the manual `#course-competitors` field block with the **Ecossistema Monitorado Automaticamente** card (displaying the 10 Educational Competitors chips + 10 Sector Radar Insurers chips + radar freshness indicator) and a collapsed `<details>` `"+ Adicionar concorrente extra pontual para esta análise (opcional)"` preserving `#course-competitors` inside so existing form submission logic continues to accept optional extra seeds seamlessly.
4. Document the `ecosystem` YAML block and `sector_radar` workflow behavior in `docs/operations/configuration.md` and `docs/agent/workflow.md`.

- [ ] **Step 4: Run full regression suite**

Run: `rtk pytest tests/unit/ tests/integration/ tests/contract/ tests/operational/ -v`
Expected: PASS (0 failures)

- [ ] **Step 5: Commit**

```bash
rtk git add src/prometeus/entrypoints/rest/app.py web/js/store.js web/js/views/intake-view.js docs/operations/configuration.md docs/agent/workflow.md tests/integration/entrypoints/test_tenant_ecosystem_api.py
rtk git commit -m "feat(web): expose tenant ecosystem API and automate competitor/radar intake UI"
```

