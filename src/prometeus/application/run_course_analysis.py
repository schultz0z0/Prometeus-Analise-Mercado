"""Caso de uso canônico para a auditoria completa de um novo curso."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.collect_market_evidence import (
    CollectMarketEvidenceService,
    RequiredSourceBlockedError,
    ResearchToolExecutor,
)
from prometeus.application.collection_diagnostics import summarize_collection
from prometeus.application.course_understanding import CourseUnderstandingService
from prometeus.application.decision_service import DecisionService
from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.evidence_features import (
    EvidenceFeatureExtractor,
    EvidenceFeatureSet,
    VerifiedFeature,
)
from prometeus.application.internal_history import InternalHistoryService
from prometeus.application.keywords import KeywordPipeline
from prometeus.application.plan_course_research import (
    CourseResearchPlanner,
    ResearchPlanValidationError,
)
from prometeus.application.pricing_reference import build_price_reference
from prometeus.application.qualify_market_evidence import EvidenceQualificationService
from prometeus.application.research_sufficiency import research_gaps
from prometeus.application.runtime_preflight import validate_runtime_preflight
from prometeus.application.scoring_service import ScoringService
from prometeus.application.skill_registry import SkillRegistry
from prometeus.application.synthesize_dossier import (
    DossierSynthesisService,
    DossierVerificationError,
)
from prometeus.domain.analyses import Analysis, AnalysisStatus, AnalysisStep
from prometeus.domain.configuration import (
    AppSettings,
    ConfigurationError,
    ScoringProfileConfig,
    load_scoring_profile,
)
from prometeus.domain.dossiers import DossierStatus
from prometeus.domain.ports.decision_model import DecisionModelPort
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.domain.ports.market_sources import EvidenceType, KeywordSet, MarketEvidence
from prometeus.domain.research import CourseResearchPlan, CourseUnderstanding
from prometeus.infrastructure.apify.client import ApifyError
from prometeus.infrastructure.apify.registry import ApifyActorRegistry
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    ConfigSnapshotModel,
    DossierModel,
    HistoricalCourseModel,
    HistoricalFunnelModel,
    MarketEvidenceModel,
    ResearchPlanModel,
    ScoringResultModel,
    ToolRunModel,
)
from prometeus.infrastructure.jev.client import JEVError

__all__ = ["WORKFLOW_STEPS", "RunCourseAnalysis"]


WORKFLOW_STEPS: tuple[tuple[int, str], ...] = (
    (1, "runtime_preflight"),
    (2, "intake_normalization"),
    (3, "readiness_assessment"),
    (4, "course_understanding"),
    (5, "keyword_entity_mapping"),
    (6, "research_planning"),
    (7, "institutional_history"),
    (8, "external_tool_execution"),
    (9, "evidence_sanitization"),
    (10, "semantic_judgments"),
    (11, "verified_feature_scoring"),
    (12, "quality_gates"),
    (13, "dossier_synthesis"),
    (14, "factual_verification"),
    (15, "publish_completion"),
)


BlockedWorkflowError = (
    ApifyError,
    ConfigurationError,
    ConnectionError,
    DossierVerificationError,
    JEVError,
    ResearchPlanValidationError,
    RequiredSourceBlockedError,
    TimeoutError,
    ValueError,
    httpx.HTTPError,
)


class RunCourseAnalysis:
    """Orquestra LLM, decisões, ferramentas, scoring e dossiê com checkpoints."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: AppSettings,
        llm: GenerativeModelPort,
        decision_model: DecisionModelPort,
        tool_executor: ResearchToolExecutor,
        registry: ApifyActorRegistry,
        skills: SkillRegistry | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.llm = llm
        self.registry = registry
        self.repository = AnalysisRepository(session)
        self.skills = skills or SkillRegistry()
        self.decisions = DecisionService(decision_model=decision_model, session=session)
        self.collector = CollectMarketEvidenceService(
            session=session,
            executor=tool_executor,
            registry=registry,
        )

    @staticmethod
    def _feature_dump(features: EvidenceFeatureSet) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "name": feature.name,
                "value": feature.value,
                "evidence_ids": feature.evidence_ids,
                "method": feature.method,
            }
            for name, feature in features.features.items()
        }

    @staticmethod
    def _feature_load(payload: dict[str, Any]) -> EvidenceFeatureSet:
        return EvidenceFeatureSet(
            features={
                name: VerifiedFeature(
                    name=str(item["name"]),
                    value=item["value"],
                    evidence_ids=[str(value) for value in item.get("evidence_ids", [])],
                    method=str(item["method"]),
                )
                for name, item in payload.items()
                if isinstance(item, dict)
            }
        )

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            return {str(key): RunCourseAnalysis._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [RunCourseAnalysis._normalize(item) for item in value]
        return value

    async def _checkpoint(
        self,
        analysis: Analysis,
        step_number: int,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        _, name = WORKFLOW_STEPS[step_number - 1]
        existing = next(
            (step for step in analysis.steps if step.step_number == step_number),
            None,
        )
        if existing is not None and existing.status == "COMPLETED":
            return existing.output_summary

        now = datetime.now(UTC)
        if existing is None:
            existing = AnalysisStep(
                id=str(uuid.uuid4()),
                analysis_id=analysis.id,
                step_number=step_number,
                name=name,
                status="RUNNING",
                started_at=now,
            )
            analysis.steps.append(existing)
        else:
            existing.status = "RUNNING"
            existing.started_at = now
            existing.finished_at = None
            existing.error_message = None
        await self.repository.save(analysis)
        await self.session.commit()

        try:
            output = await operation()
        except Exception as exc:
            # A failed flush poisons the session until rollback. Persist the
            # checkpoint failure in a fresh transaction, preserving prior commits.
            await self.session.rollback()
            existing.status = "FAILED"
            existing.finished_at = datetime.now(UTC)
            existing.error_message = (
                f"database_persistence_error: {type(exc).__name__}"
                if isinstance(exc, SQLAlchemyError)
                else str(exc).replace("\r", " ").replace("\n", " ")[:500]
            )
            if isinstance(exc, DossierVerificationError) and exc.report is not None:
                existing.output_summary = {"verification": exc.report}
            await self.repository.save(analysis)
            await self.session.commit()
            raise

        existing.status = "COMPLETED"
        existing.finished_at = datetime.now(UTC)
        existing.output_summary = output
        existing.error_message = None
        analysis.steps.sort(key=lambda step: step.step_number)
        await self.repository.save(analysis)
        await self.session.commit()
        return output

    async def _historical_features(
        self,
        analysis: Analysis,
        understanding: CourseUnderstanding,
        correlation_id: str,
    ) -> EvidenceFeatureSet:
        courses = list(
            (
                await self.session.execute(
                    select(HistoricalCourseModel).where(
                        HistoricalCourseModel.tenant_id == analysis.tenant_id
                    )
                )
            ).scalars()
        )
        if not courses:
            return EvidenceFeatureSet(features={})

        course_ids = [course.id for course in courses]
        funnels = list(
            (
                await self.session.execute(
                    select(HistoricalFunnelModel).where(
                        HistoricalFunnelModel.course_id.in_(course_ids)
                    )
                )
            ).scalars()
        )
        evidence_ids = [course.id for course in courses] + [funnel.id for funnel in funnels]
        decision = await self.decisions.execute_judgment(
            pack_id="comparable-fit-v1",
            context={
                "course_understanding": understanding.model_dump(mode="json"),
                "historical_courses": [
                    {
                        "id": course.id,
                        "name": course.name,
                        "category": course.category,
                        "modality": course.modality,
                        "tags": course.tags,
                        "target_audience": course.target_audience,
                    }
                    for course in courses
                ],
            },
            analysis=analysis,
            correlation_id=correlation_id,
            evidence_ids=evidence_ids,
        )
        features: dict[str, VerifiedFeature] = {}
        if decision.score_value is not None:
            features["comparable_fit_score"] = VerifiedFeature(
                name="comparable_fit_score",
                value=decision.score_value,
                evidence_ids=[decision.id, *evidence_ids],
                method="semantic_comparable_fit",
            )
        total_leads = sum(funnel.leads for funnel in funnels)
        total_enrolled = sum(funnel.enrolled for funnel in funnels)
        if funnels and total_leads > 0:
            features["conversion_rate"] = VerifiedFeature(
                name="conversion_rate",
                value=round(total_enrolled / total_leads, 6),
                evidence_ids=[funnel.id for funnel in funnels],
                method="historical_enrolled_over_leads",
            )
        if funnels:
            features["enrollments_count"] = VerifiedFeature(
                name="enrollments_count",
                value=round(total_enrolled / len(funnels)),
                evidence_ids=[funnel.id for funnel in funnels],
                method="historical_mean_enrollments",
            )
        return EvidenceFeatureSet(features=features)

    async def _market_features(
        self, analysis_id: str, understanding: CourseUnderstanding | None = None
    ) -> EvidenceFeatureSet:
        rows = list(
            (
                await self.session.execute(
                    select(MarketEvidenceModel).where(
                        MarketEvidenceModel.analysis_id == analysis_id
                    )
                )
            ).scalars()
        )
        evidences: list[MarketEvidence] = []
        for row in rows:
            try:
                evidence_type = EvidenceType(row.evidence_type)
            except ValueError:
                continue
            evidences.append(
                MarketEvidence(
                    id=row.id,
                    analysis_id=row.analysis_id,
                    evidence_type=evidence_type,
                    source_name=row.source_name,
                    source_url=row.source_url,
                    collector=row.collector,
                    content_hash=row.content_hash,
                    title=row.title,
                    raw_payload=row.raw_payload,
                    sanitized_data=row.sanitized_data,
                    quality_score=row.quality_score,
                    cost_usd=row.cost_usd,
                    collected_at=row.collected_at,
                )
            )
        features = EvidenceFeatureExtractor(
            geography=understanding.geography if understanding else None,
            price_period=understanding.proposed_price_period if understanding else None,
        ).extract(evidences)
        # Consulta válida e vazia tem proveniência própria; falha/rejeição não equivale a zero.
        runs = (
            (
                await self.session.execute(
                    select(ToolRunModel).where(ToolRunModel.analysis_id == analysis_id)
                )
            )
            .scalars()
            .all()
        )
        empty_features = {"meta_ads_library": "ad_count", "linkedin_jobs": "open_jobs_count"}
        for run in runs:
            name = empty_features.get(run.capability)
            if (
                name
                and features.get(name) is None
                and (run.parameters or {}).get("observation_status") == "observed_empty"
            ):
                features.features[name] = VerifiedFeature(name, 0, [run.id], "observed_empty_query")
        return features

    async def execute(self, analysis_id: str, correlation_id: str) -> Analysis:
        analysis = await self.repository.get_by_id(analysis_id)
        if analysis is None:
            raise ValueError(f"Análise não encontrada: {analysis_id}")
        if analysis.status == AnalysisStatus.COMPLETED:
            return analysis
        snapshot = (
            await self.session.execute(
                select(ConfigSnapshotModel).where(
                    ConfigSnapshotModel.analysis_id == analysis.id,
                    ConfigSnapshotModel.tenant_id == analysis.tenant_id,
                )
            )
        ).scalar_one_or_none()
        profile = (
            ScoringProfileConfig.model_validate(snapshot.scoring_profile_snapshot)
            if snapshot
            else load_scoring_profile(Path(self.settings.SCORING_PROFILE_PATH))
        )
        v2 = profile.historical_method == "ipd"
        if analysis.status in {AnalysisStatus.BLOCKED, AnalysisStatus.WAITING_FOR_INPUT}:
            analysis.resume(
                correlation_id=correlation_id, reason="Retomada idempotente do workflow"
            )
        elif analysis.status == AnalysisStatus.QUEUED:
            analysis.start(correlation_id=correlation_id, reason="Início da auditoria real")
        await self.repository.save(analysis)
        await self.session.commit()

        try:

            async def preflight() -> dict[str, Any]:
                report = validate_runtime_preflight(self.settings)
                if not report.ready:
                    messages = "; ".join(issue.message for issue in report.errors)
                    raise ConfigurationError(messages)
                return {
                    "ai_mode": report.ai_mode,
                    "jev_enabled": report.jev_enabled,
                    "required_sources": report.required_sources,
                    "synthetic_sources": report.synthetic_sources,
                    "guidance_snapshots": [
                        skill.snapshot() for skill in self.skills.load_all().values()
                    ],
                    "scoring_profile_id": profile.profile_id,
                }

            await self._checkpoint(analysis, 1, preflight)

            async def normalize_intake() -> dict[str, Any]:
                normalized = self._normalize(analysis.proposal_data)
                if not analysis.course_name.strip():
                    raise ValueError("O título do curso é obrigatório.")
                return {"course_name": analysis.course_name.strip(), "proposal": normalized}

            intake = await self._checkpoint(analysis, 2, normalize_intake)
            proposal = dict(intake["proposal"])

            async def assess_readiness() -> dict[str, Any]:
                result = await self.decisions.execute_judgment(
                    pack_id="readiness-v1",
                    context={"course_name": analysis.course_name, "proposal": proposal},
                    analysis=analysis,
                    correlation_id=correlation_id,
                )
                return {
                    "decision_id": result.id,
                    "selected_choice": result.selected_choice,
                    "confidence": result.confidence,
                }

            readiness = await self._checkpoint(analysis, 3, assess_readiness)
            if readiness.get("selected_choice") != "READY":
                analysis.wait_for_input(
                    correlation_id=correlation_id,
                    reason=f"Readiness: {readiness.get('selected_choice')}",
                )
                await self.repository.save(analysis)
                await self.session.commit()
                return analysis

            async def understand_course() -> dict[str, Any]:
                understanding = await CourseUnderstandingService(self.llm, self.skills).understand(
                    analysis.id, analysis.course_name, proposal
                )
                return understanding.model_dump(mode="json")

            understanding_payload = await self._checkpoint(analysis, 4, understand_course)
            understanding = CourseUnderstanding.model_validate(understanding_payload)

            async def map_keywords() -> dict[str, Any]:
                keyword_set = await KeywordPipeline(self.llm, self.decisions).build_keyword_set(
                    course_title=understanding.course_title,
                    description=understanding.summary,
                    target_audience=", ".join(understanding.target_audiences),
                    correlation_id=correlation_id,
                )
                if not keyword_set.all_search_terms:
                    raise ValueError("A LLM não produziu keywords relevantes para a pesquisa.")
                return keyword_set.model_dump(mode="json")

            keyword_payload = await self._checkpoint(analysis, 5, map_keywords)
            KeywordSet.model_validate(keyword_payload)

            async def plan_research() -> dict[str, Any]:
                plan = await CourseResearchPlanner(self.llm, self.skills, self.settings).plan(
                    understanding
                )
                return plan.model_dump(mode="json")

            plan_payload = await self._checkpoint(analysis, 6, plan_research)
            plan = CourseResearchPlan.model_validate(plan_payload)

            async def inspect_history() -> dict[str, Any]:
                if v2:
                    features, audit = await InternalHistoryService(
                        self.session, self.decisions
                    ).build(analysis, understanding, correlation_id)
                    return {"features": self._feature_dump(features), "audit": audit}
                features = await self._historical_features(analysis, understanding, correlation_id)
                return {"features": self._feature_dump(features)}

            history_payload = await self._checkpoint(analysis, 7, inspect_history)
            history_features = self._feature_load(dict(history_payload.get("features", {})))

            async def execute_tools() -> dict[str, Any]:
                outcome = await self.collector.collect(
                    tenant_id=analysis.tenant_id,
                    plan=plan,
                    understanding_snapshot=understanding.model_dump(mode="json"),
                )
                return {
                    "research_plan_id": outcome.research_plan_id,
                    "completed_call_ids": outcome.completed_call_ids,
                    "evidence_ids": outcome.evidence_ids,
                    "optional_failures": outcome.optional_failures,
                    "spent_usd": outcome.spent_usd,
                }

            await self._checkpoint(analysis, 8, execute_tools)

            async def sanitize_evidence() -> dict[str, Any]:
                qualifier = EvidenceQualificationService(self.session, self.decisions)
                qualification = await qualifier.qualify(analysis, understanding, correlation_id)
                diagnostic_runs = list(
                    (
                        await self.session.execute(
                            select(ToolRunModel).where(ToolRunModel.analysis_id == analysis.id)
                        )
                    ).scalars()
                )
                diagnostic_evidence = list(
                    (
                        await self.session.execute(
                            select(MarketEvidenceModel).where(
                                MarketEvidenceModel.analysis_id == analysis.id
                            )
                        )
                    ).scalars()
                )
                observations = summarize_collection(
                    [
                        {
                            key: getattr(run, key)
                            for key in (
                                "id",
                                "planned_call_id",
                                "capability",
                                "query",
                                "status",
                                "raw_items_count",
                                "valid_items_count",
                                "error_code",
                                "parameters",
                            )
                        }
                        for run in diagnostic_runs
                    ],
                    [
                        {"tool_run_id": row.tool_run_id, "sanitized_data": row.sanitized_data}
                        for row in diagnostic_evidence
                    ],
                )
                market = await self._market_features(analysis.id, understanding)
                gaps = research_gaps(market)
                repair_status = "sufficient_signals" if not gaps else "no_remaining_budget"
                plans = (
                    (
                        await self.session.execute(
                            select(ResearchPlanModel).where(
                                ResearchPlanModel.analysis_id == analysis.id
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                spent = sum(item.spent_usd for item in plans)
                remaining = max(0.0, plan.budget_limit_usd - spent)
                # Uma rodada complementar no máximo; ID estável permite retomar sem refazer planejamento/coleta.
                repair_id = f"{plan.id}-followup"
                stored_repair = next((item for item in plans if item.id == repair_id), None)
                if gaps and (remaining > 0 or stored_repair is not None):
                    if stored_repair is not None:
                        repair = CourseResearchPlan.model_validate(stored_repair.plan_snapshot)
                    else:
                        repair = await CourseResearchPlanner(
                            self.llm, self.skills, self.settings
                        ).plan(
                            understanding,
                            gaps=gaps,
                            previous_queries=[
                                (call.capability, call.query) for call in plan.tool_calls
                            ],
                            budget_limit_usd=remaining,
                            observations=observations,
                        )
                        repair = repair.model_copy(update={"id": repair_id})
                    if repair.tool_calls:
                        await self.collector.collect(
                            tenant_id=analysis.tenant_id,
                            plan=repair,
                            understanding_snapshot=understanding.model_dump(mode="json"),
                        )
                        qualification = await qualifier.qualify(
                            analysis, understanding, correlation_id
                        )
                        market = await self._market_features(analysis.id, understanding)
                        repair_status = (
                            "round_limit_reached" if research_gaps(market) else "sufficient_signals"
                        )
                    else:
                        repair_status = "no_new_queries"
                merged = EvidenceFeatureSet(
                    features={**market.features, **history_features.features}
                )
                pricing_audit: dict[str, Any] = {}
                if v2:
                    rows = (
                        (
                            await self.session.execute(
                                select(MarketEvidenceModel).where(
                                    MarketEvidenceModel.analysis_id == analysis.id,
                                    MarketEvidenceModel.evidence_type == EvidenceType.OFFER.value,
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    pricing_audit = build_price_reference(
                        course_title=analysis.course_name,
                        level=understanding.level,
                        institution_name=understanding.institution_name,
                        institution_domains=understanding.institution_domains,
                        internal_prices=history_payload.get("audit", {}).get("observed_prices", []),
                        offers=[
                            {
                                "id": row.id,
                                "title": row.title,
                                "source_url": row.source_url,
                                "sanitized_data": row.sanitized_data,
                            }
                            for row in rows
                        ],
                        installments=proposal.get("installments_count"),
                    )
                    pricing_audit["guidance"] = [
                        skill.snapshot() for skill in self.skills.for_stage("pricing_extraction")
                    ]
                    if pricing_audit["mean_total_brl"] is not None:
                        ids = sorted(
                            {
                                str(eid)
                                for item in pricing_audit["comparables"]
                                for eid in item["evidence_ids"]
                                if eid
                            }
                        )
                        # One-sided data is valid but has lower completeness/confidence.
                        confidence = (
                            0.8
                            if pricing_audit["internal_count"] and pricing_audit["external_count"]
                            else 0.5
                        )
                        merged.features["reference_mean_price_brl"] = VerifiedFeature(
                            "reference_mean_price_brl",
                            pricing_audit["mean_total_brl"],
                            ids,
                            "mean_per_comparable_course",
                        )
                        merged.features["pricing_confidence"] = VerifiedFeature(
                            "pricing_confidence", confidence, ids, "pricing_source_completeness"
                        )
                return {
                    "features": self._feature_dump(merged),
                    "qualification": qualification,
                    "remaining_gaps": research_gaps(market),
                    "repair_status": repair_status,
                    "pricing_audit": pricing_audit,
                    "initial_collection_diagnostics": observations,
                }

            feature_payload = await self._checkpoint(analysis, 9, sanitize_evidence)
            verified_features = self._feature_load(dict(feature_payload.get("features", {})))

            async def semantic_judgments() -> dict[str, Any]:
                evidence_ids = sorted(
                    (
                        await self.session.execute(
                            select(MarketEvidenceModel.id).where(
                                MarketEvidenceModel.analysis_id == analysis.id
                            )
                        )
                    ).scalars()
                )
                evidence_rows = list(
                    (
                        await self.session.execute(
                            select(MarketEvidenceModel).where(
                                MarketEvidenceModel.analysis_id == analysis.id
                            )
                        )
                    ).scalars()
                )
                evidence_rows = [
                    row
                    for row in evidence_rows
                    if (row.sanitized_data or {}).get("_qualification", {}).get("accepted") is True
                ]
                if v2:
                    evidence_rows = [
                        row
                        for row in evidence_rows
                        if "curriculum"
                        in (row.sanitized_data or {}).get("_qualification", {}).get("use_for", [])
                    ]
                evidence_ids = [row.id for row in evidence_rows]
                if not evidence_rows:
                    return {
                        "decision_id": None,
                        "score_value": None,
                        "confidence": 0,
                        "evidence_ids": [],
                    }
                result = await self.decisions.execute_judgment(
                    pack_id="syllabus-fit-v1",
                    context={
                        "guidance": "\n".join(
                            skill.instructions
                            for skill in self.skills.for_stage("curriculum_audit")
                        ),
                        "course_understanding": understanding.model_dump(mode="json"),
                        "curriculum": proposal.get("curriculum_text") or proposal.get("curriculum"),
                        "market_evidence": [
                            {
                                "id": row.id,
                                "type": row.evidence_type,
                                "title": row.title,
                                "data": row.sanitized_data,
                            }
                            for row in evidence_rows
                        ],
                    },
                    analysis=analysis,
                    correlation_id=correlation_id,
                    evidence_ids=evidence_ids,
                )
                if result.score_value is None:
                    raise ValueError("O julgamento de aderência curricular não retornou score.")
                return {
                    "decision_id": result.id,
                    "score_value": result.score_value,
                    "confidence": result.confidence,
                    "requires_human_review": result.requires_human_review or result.is_noul,
                    "evidence_ids": evidence_ids,
                }

            judgment = await self._checkpoint(analysis, 10, semantic_judgments)
            if judgment["score_value"] is not None:
                verified_features.features["syllabus_fit_score"] = VerifiedFeature(
                    name="syllabus_fit_score",
                    value=float(judgment["score_value"]),
                    evidence_ids=[str(judgment["decision_id"]), *judgment["evidence_ids"]],
                    method="semantic_syllabus_fit",
                )
                if v2:
                    ids = [str(judgment["decision_id"])]
                    verified_features.features["syllabus_confidence"] = VerifiedFeature(
                        "syllabus_confidence",
                        float(judgment["confidence"]),
                        ids,
                        "semantic_confidence",
                    )
                    verified_features.features["syllabus_requires_review"] = VerifiedFeature(
                        "syllabus_requires_review",
                        int(bool(judgment.get("requires_human_review"))),
                        ids,
                        "semantic_review_gate",
                    )

            async def calculate_score() -> dict[str, Any]:
                scoring = ScoringService(session=self.session)
                scoring._profiles_cache[profile.profile_id] = profile
                inputs = scoring.build_pillar_inputs(
                    verified_features,
                    proposed_price_brl=understanding.proposed_price_brl,
                    proposed_price_source_id=f"course-understanding:{understanding.snapshot_hash}",
                    profile_id=profile.profile_id,
                )
                result = await scoring.execute_scoring(
                    pillar_inputs=inputs,
                    analysis=analysis,
                    correlation_id=correlation_id,
                    is_experimental=True,
                    finalize_analysis=False,
                    profile_id=profile.profile_id,
                )
                return {
                    "scoring_result_id": result.id,
                    "viability_score": result.viability_score,
                    "coverage_score": result.coverage_score,
                    "confidence_score": result.confidence_score,
                    "recommendation": result.recommendation.value,
                }

            score_payload = await self._checkpoint(analysis, 11, calculate_score)

            async def apply_quality_gates() -> dict[str, Any]:
                scoring = (
                    await self.session.execute(
                        select(ScoringResultModel).where(
                            ScoringResultModel.analysis_id == analysis.id
                        )
                    )
                ).scalar_one()
                return {
                    "recommendation": scoring.recommendation,
                    "gate_details": scoring.gate_details,
                    "coverage_score": scoring.coverage_score,
                    "confidence_score": scoring.confidence_score,
                }

            await self._checkpoint(analysis, 12, apply_quality_gates)

            async def synthesize() -> dict[str, Any]:
                dossier = await DossierSynthesisService(
                    self.session, self.llm, DossierVerifier(), decisions=self.decisions
                ).synthesize_and_verify(analysis.id)
                return {
                    "dossier_id": dossier.id,
                    "status": dossier.status.value,
                    "model_name": dossier.model_name,
                    "facts_hash": dossier.facts_hash,
                }

            dossier_payload = await self._checkpoint(analysis, 13, synthesize)

            async def verify_facts() -> dict[str, Any]:
                dossier = (
                    await self.session.execute(
                        select(DossierModel).where(DossierModel.analysis_id == analysis.id)
                    )
                ).scalar_one()
                if dossier.status != DossierStatus.VERIFIED.value:
                    raise DossierVerificationError("Dossiê persistido não está verificado.")
                return {
                    "dossier_id": dossier.id,
                    "status": dossier.status,
                    "facts_hash": dossier.facts_hash,
                }

            await self._checkpoint(analysis, 14, verify_facts)

            async def publish_completion() -> dict[str, Any]:
                scoring = (
                    await self.session.execute(
                        select(ScoringResultModel).where(
                            ScoringResultModel.analysis_id == analysis.id
                        )
                    )
                ).scalar_one()
                return {
                    "recommendation": scoring.recommendation,
                    "score": score_payload["viability_score"],
                    "dossier_id": dossier_payload["dossier_id"],
                    "checkpoint_persisted": True,
                    "webhook": "not_configured",
                }

            completion = await self._checkpoint(analysis, 15, publish_completion)
            from prometeus.domain.analyses import AnalysisRecommendation

            analysis.complete(
                recommendation=AnalysisRecommendation(completion["recommendation"]),
                correlation_id=correlation_id,
                reason="Auditoria real concluída com dossiê verificado",
            )
            await self.repository.save(analysis)
            await self.session.commit()
            return analysis
        except BlockedWorkflowError as exc:
            if analysis.status == AnalysisStatus.RUNNING:
                analysis.block(correlation_id=correlation_id, reason=str(exc)[:500])
            await self.repository.save(analysis)
            await self.session.commit()
            return analysis
        except Exception as exc:
            await self.session.rollback()
            if analysis.status == AnalysisStatus.RUNNING:
                reason = (
                    f"database_persistence_error: {type(exc).__name__}"
                    if isinstance(exc, SQLAlchemyError) else str(exc)[:500]
                )
                analysis.fail(correlation_id=correlation_id, reason=reason)
            await self.repository.save(analysis)
            await self.session.commit()
            raise
