import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.application.run_course_analysis import RunCourseAnalysis
from prometeus.domain.analyses import AnalysisStatus
from prometeus.domain.configuration import AppSettings
from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFacts,
    DossierOutput,
    DossierSection,
    DossierStatus,
)
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyError
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.models import (
    Base,
    DossierModel,
    HistoricalCourseModel,
    HistoricalFunnelModel,
    MarketEvidenceModel,
    ResearchPlanModel,
    ScoringResultModel,
    ToolRunModel,
)
from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


class WorkflowLLM(FakeGenerativeModel):
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        if "Título fornecido pelo usuário" in prompt:
            return json.dumps(
                {
                    "summary": "Formação aplicada em dados para o mercado segurador.",
                    "subject_domains": ["seguros", "dados"],
                    "target_audiences": ["analistas de seguros"],
                    "learning_outcomes": ["analisar riscos com dados"],
                    "level": "pós-graduação",
                    "modality": "online",
                    "geography": "Brasil",
                    "language": "pt-BR",
                    "proposed_price_brl": 14000,
                    "duration_months": 12,
                    "supplied_materials": ["ementa"],
                    "uncertainties": [],
                    "hypotheses": [],
                }
            )
        if "Allowlist de capabilities" in prompt:
            calls = []
            for capability in (
                "google_search",
                "meta_ads_library",
                "linkedin_jobs",
                "instagram",
                "google_trends",
            ):
                calls.append(
                    {
                        "id": f"call-{capability}",
                        "capability": capability,
                        "query": "curso dados seguros",
                        "required": True,
                        "rationale": f"Medir sinal real em {capability}",
                        "max_items": 10,
                        "parameters": {"country": "BR"},
                    }
                )
            return json.dumps(
                {
                    "questions": [
                        {
                            "id": "question-demand",
                            "question": "Existe demanda observável?",
                            "evidence_need": "Sinais externos",
                            "priority": 1,
                        }
                    ],
                    "tool_calls": calls,
                }
            )
        if "Opções disponíveis" in prompt:
            options = json.loads(prompt.split("Opções disponíveis: ", 1)[1].split("\n", 1)[0])
            selected = "READY" if "READY" in options else options[0]
            distribution = {option: (0.95 if option == selected else 0.0) for option in options}
            return json.dumps(
                {
                    "selected_choice": selected,
                    "confidence": 0.95,
                    "distribution": distribution,
                }
            )
        if "Critério de Avaliação" in prompt:
            score = 88.0 if "módulos da ementa" in prompt else 84.0
            return json.dumps(
                {
                    "score_value": score,
                    "confidence": 0.9,
                    "requires_human_review": False,
                }
            )
        raise AssertionError(f"Prompt inesperado no teste: {prompt[:120]}")

    async def synthesize_dossier(
        self,
        facts: DossierFacts,
        prompt_version: str = "dossier-v1",
    ) -> DossierOutput:
        claim = DossierClaim(
            claim_id="CLM-SCORE",
            statement=f"O score observado foi {facts.viability_score:.1f}.",
            claim_type=ClaimType.QUANTITATIVE,
            evidence_ids=["scoring_result"],
        )
        sections = [
            DossierSection(
                section_id=f"section-{audience}",
                title=title,
                target_audience=audience,
                content=f"Síntese baseada no score observado de {facts.viability_score:.1f}.",
                claim_ids=[claim.claim_id],
            )
            for audience, title in (
                ("executive", "Resumo executivo"),
                ("academic", "Auditoria acadêmica"),
                ("marketing", "Oferta e posicionamento"),
            )
        ]
        return DossierOutput(
            analysis_id=facts.analysis_id,
            prompt_version=prompt_version,
            model_name="workflow-test-llm",
            executive_summary=sections[0].content,
            sections=sections,
            claims=[claim],
            facts_hash=facts.compute_facts_hash(),
            status=DossierStatus.DRAFT,
        )


class RecordedToolExecutor:
    def __init__(self, registry: ApifyActorRegistry, fail_capability: str | None = None) -> None:
        self.registry = registry
        self.fail_capability = fail_capability
        self.calls: list[str] = []

    async def execute(
        self,
        call: PlannedToolCall,
        *,
        max_total_charge_usd: float,
    ) -> ApifyExecutionResult:
        self.calls.append(call.capability)
        if call.capability == self.fail_capability:
            raise ApifyError("falha externa controlada")
        spec = self.registry.require(call.capability)
        items = {
            "google_search": [
                {
                    "title": "Pós em Dados para Seguros",
                    "url": "https://concorrente.example/curso",
                    "price_brl": 15000,
                }
            ],
            "meta_ads_library": [
                {
                    "id": "ad-1",
                    "pageName": "Concorrente",
                    "competition_index": 0.72,
                }
            ],
            "linkedin_jobs": [
                {
                    "id": "job-1",
                    "title": "Analista de Dados em Seguros",
                    "jobUrl": "https://linkedin.example/job-1",
                    "salary_median_brl": 11000,
                }
            ],
            "instagram": [
                {"id": "post-1", "url": "https://instagram.example/post-1", "caption": "dados"}
            ],
            "google_trends": [
                {
                    "searchTerm": "curso dados seguros",
                    "average_interest": 78,
                    "growth_trend_pct": 25,
                }
            ],
        }[call.capability]
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=f"run-{call.capability}",
                dataset_id=f"dataset-{call.capability}",
                status="SUCCEEDED",
                actor_id=spec.actor_id,
                build_number=spec.build,
                cost_usd=0.01,
            ),
            items=items,
            total_items=len(items),
        )


def workflow_settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        AI_MODE="traditional",
        GEN_LLM_PROVIDER="openai",
        OPENAI_API_KEY="test-key",
        APIFY_TOKEN="test-apify-token",
        APIFY_REQUIRED_SOURCES=(
            "google_search,meta_ads_library,linkedin_jobs,instagram,google_trends"
        ),
        APIFY_ACTOR_GOOGLE_SEARCH="apify/google-search-scraper@0.0.473",
        APIFY_ACTOR_META_AD_LIBRARY="igolaizola/facebook-ad-library-scraper@0.0.59",
        APIFY_ACTOR_LINKEDIN_JOBS="curious_coder/linkedin-jobs-scraper@1.7.18",
        APIFY_ACTOR_INSTAGRAM="apify/instagram-scraper@0.0.831",
        APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143",
    )


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        yield db
    await engine.dispose()


async def seed_analysis_and_history(session: AsyncSession) -> str:
    created = await CreateAnalysisUseCase(session).execute(
        CreateAnalysisCommand(
            tenant_id="ens",
            course_name="Pós em Dados Aplicados a Seguros",
            proposal_data={
                "curriculum_text": "Dados, riscos, Python e modelos preditivos",
                "target_audience": "Analistas de seguros",
                "ticket": 14000,
            },
            idempotency_key="real-workflow-e2e",
            correlation_id="corr-create",
        )
    )
    course = HistoricalCourseModel(
        id="history-course-1",
        tenant_id="ens",
        external_id="ens-history-1",
        name="MBA em Analytics para Seguros",
        category="seguros e dados",
        modality="online",
        workload_hours=360,
        tags=["dados", "seguros"],
        target_audience=["analistas"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    funnel = HistoricalFunnelModel(
        id="history-funnel-1",
        course_id=course.id,
        external_course_id=course.external_id,
        period="2025",
        leads=400,
        applicants=80,
        enrolled=40,
        conversion_lead_to_applicant=0.2,
        conversion_applicant_to_enrolled=0.5,
        conversion_lead_to_enrolled=0.1,
        average_ticket_brl=13000,
        total_revenue_brl=520000,
    )
    session.add_all([course, funnel])
    await session.commit()
    return created.analysis_id


@pytest.mark.asyncio
async def test_full_workflow_uses_persisted_real_source_contracts_and_resumes_idempotently(
    session: AsyncSession,
) -> None:
    analysis_id = await seed_analysis_and_history(session)
    settings = workflow_settings()
    registry = ApifyActorRegistry.from_settings(settings)
    llm = WorkflowLLM()
    executor = RecordedToolExecutor(registry)
    use_case = RunCourseAnalysis(
        session=session,
        settings=settings,
        llm=llm,
        decision_model=LLMDecisionAdapter(llm),
        tool_executor=executor,
        registry=registry,
    )

    result = await use_case.execute(analysis_id, "corr-workflow")

    assert result.status == AnalysisStatus.COMPLETED
    assert len(result.steps) == 15
    assert all(step.status == "COMPLETED" for step in result.steps)
    assert executor.calls == settings.required_market_sources
    assert await session.scalar(select(func.count()).select_from(ResearchPlanModel)) == 1
    assert await session.scalar(select(func.count()).select_from(ToolRunModel)) == 5
    assert await session.scalar(select(func.count()).select_from(MarketEvidenceModel)) == 5
    scoring = (await session.execute(select(ScoringResultModel))).scalar_one()
    assert scoring.viability_score != 86.4
    assert scoring.pillar_scores["paid_competition"]["features"]["evidence_ids"]
    dossier = (await session.execute(select(DossierModel))).scalar_one()
    assert dossier.status == "VERIFIED"

    repeated = await use_case.execute(analysis_id, "corr-resume")

    assert repeated.status == AnalysisStatus.COMPLETED
    assert len(executor.calls) == 5
    assert await session.scalar(select(func.sum(ToolRunModel.cost_usd))) == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_required_external_source_failure_blocks_without_score_or_dossier(
    session: AsyncSession,
) -> None:
    analysis_id = await seed_analysis_and_history(session)
    settings = workflow_settings()
    registry = ApifyActorRegistry.from_settings(settings)
    llm = WorkflowLLM()
    executor = RecordedToolExecutor(registry, fail_capability="meta_ads_library")
    use_case = RunCourseAnalysis(
        session=session,
        settings=settings,
        llm=llm,
        decision_model=LLMDecisionAdapter(llm),
        tool_executor=executor,
        registry=registry,
    )

    result = await use_case.execute(analysis_id, "corr-blocked")

    assert result.status == AnalysisStatus.BLOCKED
    assert result.recommendation is None
    assert await session.scalar(select(func.count()).select_from(ScoringResultModel)) == 0
    assert await session.scalar(select(func.count()).select_from(DossierModel)) == 0
