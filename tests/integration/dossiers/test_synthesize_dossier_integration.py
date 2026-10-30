"""Testes de integração para DossierSynthesisService e fluxo ponta a ponta de síntese de dossiê."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.synthesize_dossier import (
    DossierSynthesisService,
    DossierVerificationError,
)
from prometeus.domain.analyses import Analysis
from prometeus.domain.dossiers import DossierStatus
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    Base,
    DecisionResultModel,
    DossierModel,
    MarketEvidenceModel,
    ScoringResultModel,
)
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.mark.parametrize("installments", [12, None, True, 0])
async def test_real_failure_facts_expose_computed_total_and_history_nature(
    db_session, installments
):
    from prometeus.application.dossier_verifier import DossierVerifier
    from prometeus.domain.dossiers import DossierClaim
    from prometeus.infrastructure.db.models import AnalysisStepModel, ResearchPlanModel

    analysis = Analysis.create(
        tenant_id="ens", course_name="Extensão em Fraude", correlation_id="facts-regression"
    )
    analysis.proposal_data = {
        "ticket": 100,
        "price_period": "monthly",
        "installments_count": installments,
        "duration_months": 1,
        "curriculum_text": "Extensão em Fraude. Modalidade on-line. Duração 16h.",
    }
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="regression-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=55.26,
            coverage_score=0.8,
            confidence_score=0.6573,
            partial_score=55.26,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={
                "internal_history": {"is_present": True, "raw_score": 72.22, "confidence": 0.9}
            },
            gate_details={},
        )
    )
    db_session.add(
        ResearchPlanModel(
            id="regression-plan",
            analysis_id=analysis.id,
            tenant_id="ens",
            cache_key="regression",
            understanding_snapshot={
                "target_audiences": ["Profissionais de seguros"],
                "proposed_price_brl": 1200,
                "proposed_price_period": "total",
            },
        )
    )
    db_session.add(
        AnalysisStepModel(
            id="regression-preflight",
            analysis_id=analysis.id,
            step_number=1,
            name="runtime_preflight",
            status="COMPLETED",
            output_summary={"synthetic_sources": ["institutional_history"]},
        )
    )
    db_session.add(
        AnalysisStepModel(
            id="regression-history",
            analysis_id=analysis.id,
            step_number=7,
            name="institutional_history",
            status="COMPLETED",
            output_summary={
                "audit": {
                    "family": "extensao",
                    "reference_n": 10,
                    "reference_period": "2025",
                    "comparables": [
                        {"name": name, "category": "Extensão", "period": "2025"}
                        for name in [
                            "Seguros Cibernéticos",
                            "Análise de Dados",
                            "Responsabilidade Civil",
                        ]
                    ],
                }
            },
        )
    )
    await db_session.commit()
    facts = await DossierSynthesisService(db_session, FakeGenerativeModel()).build_facts(
        analysis.id
    )
    if installments == 12:
        assert facts.get_fact_item("provided_proposal").key_metrics["total_price_brl"] == 1200
    else:
        assert "total_price_brl" not in facts.get_fact_item("provided_proposal").key_metrics
    assert facts.get_fact_item("provided_proposal").key_metrics["duration_months"] == 1
    history = facts.get_fact_item("institutional_history")
    assert history.key_metrics["data_nature"] == "synthetic"
    assert history.key_metrics["comparables_count"] == 3
    assert history.key_metrics["reference_count"] == 10
    assert history.key_metrics["reference_period"] == "2025"
    assert history.key_metrics["internal_ipd_score"] == 72.22
    assert history.key_metrics["internal_ipd_confidence"] == 0.9
    ipd_claim = DossierClaim(
        statement="O IPD histórico interno é 72,22.", evidence_ids=["institutional_history"]
    )
    assert DossierVerifier().verify_claim(ipd_claim, facts).verification_status == "verified"
    text = (
        "A proposta informa 16 horas e 12 parcelas de R$ 100, total de R$ 1.200."
        if installments == 12
        else "A proposta informa 16 horas."
    )
    claim = DossierClaim(statement=text, evidence_ids=["provided_proposal"])
    assert DossierVerifier().verify_claim(claim, facts).verification_status == "verified"
    if installments != 12:
        unsupported = DossierClaim(
            statement="O investimento total é R$ 1.200.", evidence_ids=["provided_proposal"]
        )
        assert (
            DossierVerifier().verify_claim(unsupported, facts).verification_status
            == "flagged_hallucination"
        )

    import json

    from prometeus.application.decision_service import DecisionService
    from prometeus.infrastructure.llm.decision_adapter import LLMDecisionAdapter

    class Capturing(FakeGenerativeModel):
        async def generate_text(self, prompt, system_prompt=None, temperature=0.2):
            context = json.loads(prompt.split("Contexto avaliado:\n", 1)[1])
            assert [f["evidence_id"] for f in context["cited_facts"]] == ["institutional_history"]
            metrics = context["cited_facts"][0]["key_metrics"]
            assert metrics["data_nature"] == "synthetic"
            assert metrics["comparables_count"] == 3
            assert metrics["reference_count"] == 10
            assert "suporte empírico" not in prompt
            assert "Histórico sintético NÃO sustenta" in system_prompt
            return json.dumps(
                {
                    "selected_choice": "OBSERVED",
                    "confidence": 0.95,
                    "distribution": {"OBSERVED": 0.95, "SUGGESTIVE": 0.04, "UNSUPPORTED": 0.01},
                }
            )

    service = DossierSynthesisService(
        db_session,
        FakeGenerativeModel(),
        decisions=DecisionService(LLMDecisionAdapter(Capturing()), db_session),
    )
    from prometeus.domain.dossiers import DossierOutput, DossierSection

    recorded = "O histórico institucional sintético compara a proposta com três cursos de extensão de 2025, em uma família de referência de 10 cursos; essa base não demonstra demanda ou conversão real da nova oferta."
    draft = DossierOutput(
        analysis_id=analysis.id,
        facts_hash=facts.compute_facts_hash(),
        executive_summary=recorded,
        claims=[
            DossierClaim(
                claim_id="history-claim", statement=recorded, evidence_ids=["institutional_history"]
            )
        ],
        sections=[
            DossierSection(
                section_id="history",
                title="Histórico",
                target_audience="executive",
                content=recorded,
                claim_ids=["history-claim"],
            )
        ],
    )
    assert (await service._verify_generated_dossier(draft, facts)).status == "VERIFIED"


@pytest.mark.parametrize("revision_valid", [True, False])
async def test_invalid_initial_generation_consumes_same_single_revision(db_session, revision_valid):
    from prometeus.infrastructure.llm.client import DossierGenerationError

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="parse-repair")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="parse-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()

    class InvalidFirst(FakeGenerativeModel):
        revisions = 0

        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            raise DossierGenerationError(
                "Sections não é uma lista", raw_response='{"sections":"errado"}'
            )

        async def revise_dossier(
            self, facts, draft, verification_report, prompt_version="dossier-v1"
        ):
            self.revisions += 1
            assert draft == {"raw_response": '{"sections":"errado"}'}
            assert verification_report["gate"] == "contract"
            if not revision_valid:
                raise DossierGenerationError(
                    "Sections ainda inválida", raw_response='{"sections":null}'
                )
            return await FakeGenerativeModel.synthesize_dossier(self, facts, prompt_version)

    llm = InvalidFirst()
    service = DossierSynthesisService(db_session, llm)
    if revision_valid:
        assert (await service.synthesize_and_verify(analysis.id)).status == "VERIFIED"
    else:
        with pytest.raises(DossierVerificationError) as error:
            await service.synthesize_and_verify(analysis.id)
        assert error.value.report["attempt_count"] == 2
        assert error.value.report["gate"] == "contract"
        assert (await db_session.execute(select(DossierModel))).scalar_one_or_none() is None
    assert llm.revisions == 1


async def test_semantic_report_identifies_all_rejected_claims_and_citations(db_session):
    from prometeus.application.decision_service import DecisionService
    from prometeus.domain.dossiers import DossierClaim, DossierOutput, DossierSection
    from prometeus.infrastructure.jev.fake_client import FakeDecisionClient

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="all-issues")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="all-issues-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()
    service = DossierSynthesisService(
        db_session,
        FakeGenerativeModel(),
        decisions=DecisionService(
            FakeDecisionClient(canned_choices={"evidence-support-v1": "UNSUPPORTED"}), db_session
        ),
    )
    facts = await service.build_facts(analysis.id)
    draft = DossierOutput(
        analysis_id=analysis.id,
        facts_hash=facts.compute_facts_hash(),
        executive_summary="Síntese.",
        claims=[
            DossierClaim(
                claim_id="c1", statement="Primeira afirmação.", evidence_ids=["scoring_result"]
            ),
            DossierClaim(
                claim_id="c2", statement="Outra afirmação.", evidence_ids=["scoring_result"]
            ),
        ],
        sections=[
            DossierSection(
                section_id="exec",
                title="Diretoria",
                target_audience="executive",
                content="Leitura executiva.",
                claim_ids=["c1", "c2"],
            )
        ],
    )
    with pytest.raises(DossierVerificationError) as error:
        await service._verify_generated_dossier(draft, facts)
    report = error.value.report
    assert {"claims.c1", "claims.c2"}.issubset({issue["path"] for issue in report["issues"]})
    assert all(issue["evidence_ids"] == ["scoring_result"] for issue in report["issues"])
    assert all(issue["selected_choice"] == "UNSUPPORTED" for issue in report["issues"])
    assert all(issue["confidence"] == 0.9 for issue in report["issues"])


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_synthesize_and_verify_e2e_flow(db_session: AsyncSession) -> None:
    repo = AnalysisRepository(db_session)
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Inteligência de Dados para Subscrição de Seguros",
        correlation_id="corr-dossier-e2e",
    )
    await repo.save(analysis)
    await db_session.commit()

    # 1. Cria ScoringResult vinculado
    scoring = ScoringResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        profile_id="default-v1",
        viability_score=88.5,
        coverage_score=1.0,
        confidence_score=0.91,
        partial_score=88.5,
        recommendation="APPROVED",
        is_experimental=False,
        pillar_scores={
            "internal_history": {"raw_score": 90.0, "is_present": True},
            "search_and_media": {"raw_score": 85.0, "is_present": True},
        },
        gate_details={"all_passed": True},
        created_at=datetime.now(UTC),
    )
    db_session.add(scoring)

    # 2. Cria MarketEvidence vinculada
    ev = MarketEvidenceModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        evidence_type="SEARCH_VOLUME",
        source_name="GoogleAds",
        source_url="https://ads.google.com",
        collector="google_ads_collector",
        content_hash="hash-ev-ads",
        title="Buscas para Subscrição de Riscos",
        raw_payload={},
        sanitized_data={"monthly_volume": 4500, "cpc_brl": 6.8},
        quality_score=0.95,
        cost_usd=0.01,
        collected_at=datetime.now(UTC),
    )
    db_session.add(ev)

    # 3. Cria DecisionResult do JEV
    dec = DecisionResultModel(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        pack_id="syllabus-fit-v1",
        decision_type="score",
        confidence=0.92,
        is_noul=False,
        selected_choice=None,
        distribution={},
        score_value=92.0,
        requires_human_review=False,
        evidence_ids=[],
        model_version="jev-gpt4o-2026-03",
        created_at=datetime.now(UTC),
    )
    db_session.add(dec)
    await db_session.commit()

    # 4. Executa síntese do dossiê
    fake_llm = FakeGenerativeModel()
    service = DossierSynthesisService(db_session, fake_llm)

    dossier_output = await service.synthesize_and_verify(analysis.id, prompt_version="dossier-v1")

    assert dossier_output is not None
    assert dossier_output.status == DossierStatus.VERIFIED
    assert len(dossier_output.sections) == 3
    assert len(dossier_output.claims) >= 2

    # Verifica persistência no PostgreSQL / SQLite
    stmt = select(DossierModel).where(DossierModel.analysis_id == analysis.id)
    persisted = (await db_session.execute(stmt)).scalar_one_or_none()
    assert persisted is not None
    assert persisted.status == "VERIFIED"
    assert persisted.prompt_version == "dossier-v1"
    assert "MBA em Inteligência de Dados" in persisted.executive_summary
    assert len(persisted.sections) == 3
    assert persisted.presentation["schema_version"] == dossier_output.schema_version


async def test_facts_exclude_rejected_evidence_and_keep_observed_fields(db_session):
    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="facts")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="sc",
            analysis_id=analysis.id,
            profile_id="default-v1",
            viability_score=10,
            coverage_score=0.2,
            confidence_score=0.3,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    for name, data in [
        (
            "accepted",
            {
                "price_brl": 1200,
                "price_period": "monthly",
                "location": "Brazil",
                "description": "Preço publicado",
            },
        ),
        ("rejected", {"_qualification": {"accepted": False, "reason": "Anúncio de serviço B2C"}}),
        (
            "context",
            {
                "description": "Notícia regulatória",
                "_qualification": {
                    "accepted": False,
                    "context_only": True,
                    "classification": "CONTEXT",
                    "reason": "Contexto do setor, sem prova de demanda",
                },
            },
        ),
    ]:
        db_session.add(
            MarketEvidenceModel(
                id=name,
                analysis_id=analysis.id,
                evidence_type="OFFER",
                source_name="test",
                source_url=f"https://example.edu/{name}",
                collector="test",
                content_hash=name,
                title=name,
                raw_payload=data,
                sanitized_data=data,
                quality_score=1,
                cost_usd=0,
            )
        )
    await db_session.commit()
    facts = await DossierSynthesisService(db_session, FakeGenerativeModel()).build_facts(
        analysis.id
    )
    assert facts.get_fact_item("rejected") is None
    assert facts.get_fact_item("context").key_metrics["evidence_role"] == "context_only"
    assert facts.get_fact_item("accepted").key_metrics["price_brl"] == 1200
    assert facts.get_fact_item("accepted").key_metrics["price_period"] == "monthly"
    assert any("B2C" in limitation for limitation in facts.limitations)
    assert any("experimental" in limitation for limitation in facts.limitations)


async def test_semantically_unsupported_narrative_is_not_persisted(db_session):
    from prometeus.application.decision_service import DecisionService
    from prometeus.infrastructure.jev.fake_client import FakeDecisionClient

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="semantic")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="semantic-score",
            analysis_id=analysis.id,
            profile_id="default-v1",
            viability_score=10,
            coverage_score=0.2,
            confidence_score=0.3,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()
    decisions = DecisionService(
        FakeDecisionClient(canned_choices={"evidence-support-v1": "UNSUPPORTED"}), db_session
    )
    service = DossierSynthesisService(db_session, FakeGenerativeModel(), decisions=decisions)
    with pytest.raises(DossierVerificationError, match="semântico"):
        await service.synthesize_and_verify(analysis.id)
    assert (await db_session.execute(select(DossierModel))).scalar_one_or_none() is None


async def test_public_limitations_do_not_expose_pillar_keys(db_session):
    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="labels")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="labels-score",
            analysis_id=analysis.id,
            profile_id="default-v1",
            viability_score=0,
            coverage_score=0,
            confidence_score=0,
            partial_score=0,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={
                "search_and_media": {
                    "raw_score": 0,
                    "is_present": False,
                    "missing_reason": "Nenhuma feature verificada mínima para o pilar",
                }
            },
            gate_details={},
        )
    )
    await db_session.commit()
    facts = await DossierSynthesisService(db_session, FakeGenerativeModel()).build_facts(
        analysis.id
    )
    assert not any("search_and_media" in text or "feature" in text for text in facts.limitations)
    assert any("Interesse de busca" in text for text in facts.limitations)


async def test_rejected_dossier_diagnostics_survive_failed_checkpoint_without_publication(
    db_session,
):
    from prometeus.application.run_course_analysis import RunCourseAnalysis
    from prometeus.infrastructure.db.models import AnalysisStepModel

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="rejected")
    repo = AnalysisRepository(db_session)
    await repo.save(analysis)
    db_session.add(
        ScoringResultModel(
            id="rejected-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()

    class InvalidLLM(FakeGenerativeModel):
        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            doc = await super().synthesize_dossier(facts, prompt_version)
            doc.claims[0].statement = "Garantia de 999999 matrículas."
            return doc

    workflow = object.__new__(RunCourseAnalysis)
    workflow.session = db_session
    workflow.repository = repo
    service = DossierSynthesisService(db_session, InvalidLLM())

    async def synthesize():
        await service.synthesize_and_verify(analysis.id)
        return {}

    with pytest.raises(DossierVerificationError):
        await workflow._checkpoint(analysis, 13, synthesize)
    step = (await db_session.execute(select(AnalysisStepModel))).scalar_one()
    assert step.status == "FAILED"
    report = step.output_summary["verification"]
    assert report["gate"] == "deterministic"
    assert any(i["code"] == "flagged_hallucination" for i in report["issues"])
    assert (await db_session.execute(select(DossierModel))).scalar_one_or_none() is None


@pytest.mark.parametrize("repair_outcome", ["valid", "invalid", "unavailable", "mutated_facts"])
async def test_one_dossier_revision_uses_same_facts_and_keeps_gate(db_session, repair_outcome):
    from prometeus.infrastructure.db.models import AnalysisStepModel

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="revision")
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="revision-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    db_session.add(
        AnalysisStepModel(
            id="revision-step",
            analysis_id=analysis.id,
            step_number=13,
            name="dossier_synthesis",
            status="RUNNING",
        )
    )
    await db_session.commit()

    class RevisingLLM(FakeGenerativeModel):
        def __init__(self):
            super().__init__()
            self.revisions = []
            self.initial_hash = None

        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            self.initial_hash = facts.compute_facts_hash()
            doc = await super().synthesize_dossier(facts, prompt_version)
            doc.claims[0].statement = "Garantia de 999999 matrículas."
            return doc

        async def revise_dossier(
            self, facts, draft, verification_report, prompt_version="dossier-v1"
        ):
            self.revisions.append(verification_report)
            assert facts.compute_facts_hash() == self.initial_hash
            assert draft.status == "REVISION_REQUIRED"
            assert any(i["code"] == "flagged_hallucination" for i in verification_report["issues"])
            step = await db_session.get(AnalysisStepModel, "revision-step")
            assert step.output_summary["verification"]["issues"]
            assert step.output_summary["dossier_revision"] == {"status": "RUNNING", "attempt": 2}
            if repair_outcome == "unavailable":
                raise ConnectionError("provider unavailable")
            if repair_outcome == "invalid":
                return draft
            if repair_outcome == "mutated_facts":
                facts.viability_score = 999
            return await FakeGenerativeModel.synthesize_dossier(self, facts, prompt_version)

    llm = RevisingLLM()
    service = DossierSynthesisService(db_session, llm)
    if repair_outcome == "valid":
        doc = await service.synthesize_and_verify(analysis.id)
        assert doc.status == "VERIFIED"
        persisted = (await db_session.execute(select(DossierModel))).scalar_one()
        assert persisted.presentation["verification"]["attempt_count"] == 2
    else:
        with pytest.raises(DossierVerificationError) as error:
            await service.synthesize_and_verify(analysis.id)
        assert error.value.report["attempt_count"] == 2
        assert error.value.report["issues"]
        assert (await db_session.execute(select(DossierModel))).scalar_one_or_none() is None
    assert len(llm.revisions) == 1
    stored_score = (await db_session.execute(select(ScoringResultModel))).scalar_one()
    assert stored_score.viability_score == 50
    assert stored_score.recommendation == "INSUFFICIENT_EVIDENCE"


async def test_revised_dossier_is_checked_again_by_semantic_gate(db_session):
    from prometeus.application.decision_service import DecisionService
    from prometeus.domain.dossiers import SupportLevel
    from prometeus.infrastructure.jev.fake_client import FakeDecisionClient

    analysis = Analysis.create(
        tenant_id="ens", course_name="Curso", correlation_id="semantic-revision"
    )
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="semantic-revision-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()
    checked_texts = []

    class SemanticPolicy(FakeDecisionClient):
        async def execute_choice(self, pack, context, evidence_ids=None):
            checked_texts.append(context["untrusted_claim"])
            choice = (
                "UNSUPPORTED" if "garante demanda" in context["untrusted_claim"] else "OBSERVED"
            )
            self.canned_choices[pack.pack_id] = choice
            return await super().execute_choice(pack, context, evidence_ids)

    class SemanticRevision(FakeGenerativeModel):
        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            doc = await super().synthesize_dossier(facts, prompt_version)
            doc.claims[1].statement = "A proposta garante demanda."
            return doc

        async def revise_dossier(
            self, facts, draft, verification_report, prompt_version="dossier-v1"
        ):
            assert draft.status == "REVISION_REQUIRED"
            assert verification_report["gate"] == "semantic"
            doc = await FakeGenerativeModel.synthesize_dossier(self, facts, prompt_version)
            doc.claims[1].statement = "A demanda permanece uma hipótese a validar."
            doc.claims[1].support_level = SupportLevel.HYPOTHESIS
            return doc

    service = DossierSynthesisService(
        db_session, SemanticRevision(), decisions=DecisionService(SemanticPolicy(), db_session)
    )
    result = await service.synthesize_and_verify(analysis.id)
    assert result.status == "VERIFIED"
    assert "A proposta garante demanda." in checked_texts
    assert "A demanda permanece uma hipótese a validar." in checked_texts


@pytest.mark.parametrize("initial_invalid", [True, False])
async def test_semantic_outage_preserves_diagnostics_without_more_generation(
    db_session, initial_invalid
):
    from prometeus.application.decision_service import DecisionService
    from prometeus.application.run_course_analysis import RunCourseAnalysis
    from prometeus.infrastructure.db.models import AnalysisStepModel
    from prometeus.infrastructure.jev.fake_client import FakeDecisionClient

    analysis = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="outage")
    analysis.start(correlation_id="outage")
    repo = AnalysisRepository(db_session)
    await repo.save(analysis)
    db_session.add(
        ScoringResultModel(
            id="outage-score",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=50,
            coverage_score=0.8,
            confidence_score=0.6,
            partial_score=50,
            recommendation="INSUFFICIENT_EVIDENCE",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    await db_session.commit()

    class Revising(FakeGenerativeModel):
        revisions = 0

        async def synthesize_dossier(self, facts, prompt_version="dossier-v1"):
            doc = await super().synthesize_dossier(facts, prompt_version)
            if initial_invalid:
                doc.claims[0].statement = "Garantia de 999999 matrículas."
            return doc

        async def revise_dossier(
            self, facts, draft, verification_report, prompt_version="dossier-v1"
        ):
            self.revisions += 1
            return await FakeGenerativeModel.synthesize_dossier(self, facts, prompt_version)

    llm = Revising()
    service = DossierSynthesisService(
        db_session,
        llm,
        decisions=DecisionService(FakeDecisionClient(simulate_unavailable=True), db_session),
    )
    workflow = object.__new__(RunCourseAnalysis)
    workflow.session, workflow.repository = db_session, repo

    async def operation():
        await service.synthesize_and_verify(analysis.id)
        return {}

    with pytest.raises(DossierVerificationError):
        await workflow._checkpoint(analysis, 13, operation)
    step = (await db_session.execute(select(AnalysisStepModel))).scalar_one()
    assert step.status == "FAILED"
    report = step.output_summary["verification"]
    assert report["issues"][0]["code"] == "semantic_unavailable"
    assert llm.revisions == (1 if initial_invalid else 0)
    if initial_invalid:
        assert any(i["code"] == "flagged_hallucination" for i in report["attempts"][0]["issues"])
    assert (await db_session.execute(select(DossierModel))).scalar_one_or_none() is None


async def test_job_descriptions_reach_writer_facts_and_integrity_report_is_tracked(db_session):
    """Tarefa 1.3: descrições completas de vagas alcançam os fatos do redator

    e o IntegrityReport compara source -> observation -> brief.
    """
    analysis = Analysis.create(
        tenant_id="ens", course_name="MBA Gestão de Sinistros", correlation_id="t1-3"
    )
    await AnalysisRepository(db_session).save(analysis)
    db_session.add(
        ScoringResultModel(
            id="score-t13",
            analysis_id=analysis.id,
            profile_id="portfolio-v2",
            viability_score=70.0,
            coverage_score=0.8,
            confidence_score=0.75,
            partial_score=70.0,
            recommendation="PROCEED_WITH_RESERVATIONS",
            is_experimental=True,
            pillar_scores={},
            gate_details={},
        )
    )
    job_desc = "Responsável pela regulação de sinistros patrimoniais complexos e prevenção a fraudes."
    db_session.add(
        MarketEvidenceModel(
            id="job-ev-1",
            analysis_id=analysis.id,
            evidence_type="JOB_MARKET",
            source_name="apify_linkedin_jobs",
            source_url="https://linkedin.com/jobs/view/12345",
            collector="test",
            content_hash="hash-1",
            title="Analista de Sinistros Sênior",
            raw_payload={"title": "Analista de Sinistros Sênior", "descriptionText": job_desc},
            sanitized_data={
                "title": "Analista de Sinistros Sênior",
                "descriptionText": job_desc,
                "_qualification": {"accepted": True},
            },
            quality_score=1.0,
            cost_usd=0.01,
        )
    )
    await db_session.commit()

    service = DossierSynthesisService(db_session, FakeGenerativeModel({}))
    facts = await service.build_facts(analysis.id)

    # 1. IntegrityReport gerado e anexado
    integrity = facts.analysis_audit.get("integrity_report")
    assert integrity is not None
    assert integrity["source_count"] == 1
    assert integrity["observations_count"] == 1
    assert integrity["job_descriptions_expected"] == 1
    assert integrity["job_descriptions_available"] == 1
    assert integrity["missing_descriptions_count"] == 0

    # 2. Descrição presente no fato entregue ao redator
    job_item = next(it for it in facts.items if it.evidence_id == "job-ev-1")
    assert job_desc in job_item.summary
    assert "Descrição não disponível" not in job_item.summary
    assert job_item.key_metrics.get("has_description") is True
