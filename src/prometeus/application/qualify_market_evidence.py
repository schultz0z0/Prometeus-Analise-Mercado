"""Qualificação semântica por item, persistida antes da extração e retomável."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.decision_service import DecisionService
from prometeus.application.evidence_features import EvidenceFeatureExtractor
from prometeus.application.evidence_projection import (
    PROJECTOR_VERSION,
    build_qualification_context,
)
from prometeus.application.research_scope import is_own_institution, normalize_geography
from prometeus.application.skill_registry import SkillRegistry
from prometeus.application.tool_capabilities import CAPABILITY_CONTRACTS
from prometeus.domain.analyses import Analysis
from prometeus.domain.evidence_observations import (
    EvidencePurpose,
    EvidenceUseAssessment,
    MultiPurposeAssessment,
)
from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence
from prometeus.domain.research import CourseUnderstanding
from prometeus.infrastructure.db.models import DecisionResultModel, MarketEvidenceModel

PACK = "market-relevance-v1"
QUALIFICATION_VERSION = 3


class EvidenceQualificationService:
    def __init__(
        self, session: AsyncSession, decisions: DecisionService, skills: SkillRegistry | None = None
    ) -> None:
        self.session = session
        self.decisions = decisions
        self.skills = skills or SkillRegistry()

    async def qualify(
        self,
        analysis: Analysis,
        understanding: CourseUnderstanding,
        correlation_id: str,
        *,
        institution_context: dict[str, object] | None = None,
    ) -> dict[str, int]:
        institution_context = institution_context or {
            "name": getattr(understanding, "institution_name", ""),
            "domains": getattr(understanding, "institution_domains", []),
        }
        review_skills = self.skills.for_stage("evidence_review")
        # Local procedures/catalog changes must invalidate persisted qualification.
        guidance = "\n\n".join(skill.instructions for skill in review_skills)
        actor_guidance = "\n".join(
            s.instructions
            for s in self.skills.for_capabilities(list(self.skills.CAPABILITY_SKILLS))
        )
        skill_hash = hashlib.sha256(
            (
                guidance
                + actor_guidance
                + json.dumps(CAPABILITY_CONTRACTS, sort_keys=True, ensure_ascii=False)
            ).encode()
        ).hexdigest()
        pack = self.decisions.get_pack(PACK)
        pack_hash = hashlib.sha256(pack.model_dump_json().encode()).hexdigest()
        identity_hash = hashlib.sha256(
            json.dumps(institution_context, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        rows = (
            (
                await self.session.execute(
                    select(MarketEvidenceModel)
                    .where(MarketEvidenceModel.analysis_id == analysis.id)
                    .order_by(MarketEvidenceModel.collected_at, MarketEvidenceModel.id)
                )
            )
            .scalars()
            .all()
        )
        accepted = 0
        for row in rows:
            capability = row.source_name.removeprefix("apify_")
            actor_skills = (
                self.skills.for_capabilities([capability])
                if capability in self.skills.CAPABILITY_SKILLS
                else []
            )
            data = dict(row.sanitized_data or {})
            prior = data.pop("_qualification", {})
            scope = EvidenceFeatureExtractor(geography=understanding.geography)
            own = is_own_institution(data, row.source_url, institution_context)
            scoped = scope.accepts(
                MarketEvidence.create(
                    analysis_id=analysis.id,
                    evidence_type=EvidenceType(row.evidence_type),
                    source_name=row.source_name,
                    source_url=row.source_url,
                    collector=row.collector,
                    title=row.title,
                    raw_payload=data,
                    sanitized_data=data,
                )
            )
            judgment_context = {
                "_trusted_skill_guidance": guidance,
                "course": {
                    "title": understanding.course_title,
                    "domains": understanding.subject_domains,
                    "audiences": understanding.target_audiences,
                    "geography": normalize_geography(understanding.geography),
                },
                "expected_signal": row.evidence_type,
                "source": row.source_name,
                "scope_compatible": scoped,
                "geography_validation": "localização observada verificada pelo código"
                if row.evidence_type == "JOB_MARKET"
                else "o código não confirma a região deste item; consulta e IP do coletor não provam localização do conteúdo",
                "own_institution": own,
                "signal_policy": {
                    "JOB_MARKET": "Avaliar relação do cargo e competências com a atuação dos egressos. Uma vaga NÃO precisa exigir MBA nem demonstrar procura por curso para ser relevante à empregabilidade/ementa. Cargo adjacente genérico sem relação observável permanece contexto.",
                    "SOCIAL_VOICE": "Necessidades, dúvidas e dificuldades profissionais pertinentes podem orientar a ementa. Propaganda genérica ou entretenimento não prova dor nem intenção de matrícula.",
                    "OFFER": "Ofertas da própria instituição são contexto institucional; empregadores e notícias não são concorrentes. Comparabilidade de tema/categoria/preço é verificada separadamente.",
                    "TRENDS": "Série temporal válida mede interesse relativo. Metadados sem série não devem ser interpretados como procura zero.",
                }.get(
                    row.evidence_type,
                    "Avaliar apenas o sinal específico solicitado; não inferir matrículas de presença de anúncio.",
                ),
                "untrusted_evidence": build_qualification_context(
                    data,
                    purpose=row.evidence_type,
                    budget=14000,
                    title=row.title,
                    url=row.source_url,
                ),
            }
            comp_versions = {
                "projector": PROJECTOR_VERSION,
                "qualification_service": f"v{QUALIFICATION_VERSION}",
            }
            cache_key = self.decisions.cache_key_for(
                PACK, judgment_context, component_versions=comp_versions
            )
            cached = False
            if (
                isinstance(prior, dict)
                and prior.get("pack_id") == PACK
                and prior.get("qualification_version") == QUALIFICATION_VERSION
                and prior.get("institution_hash") == identity_hash
                and prior.get("review_skill_hash") == skill_hash
                and prior.get("pack_hash") == pack_hash
                and prior.get("understanding_hash") == understanding.snapshot_hash
                and prior.get("execution_cache_key") == cache_key
            ):
                decision = await self.session.get(DecisionResultModel, prior.get("decision_id", ""))
                cached = bool(
                    decision
                    and decision.analysis_id == analysis.id
                    and decision.pack_id == PACK
                    and row.id in decision.evidence_ids
                )
            if cached:
                accepted += int(prior.get("accepted") is True)
                continue
            result = await self.decisions.execute_judgment(
                pack_id=PACK,
                analysis=analysis,
                correlation_id=correlation_id,
                evidence_ids=[row.id],
                component_versions=comp_versions,
                context=judgment_context,
            )
            relevant = (
                scoped
                and result.selected_choice == "RELEVANT"
                and not result.requires_human_review
                and not result.is_noul
                and not own
            )
            reason = (
                "Localização fora do escopo ou não comprovada"
                if not scoped
                else {
                    "RELEVANT": "Sinal pertinente ao público e à necessidade pesquisada",
                    "CONTEXT": "Contexto de setor; não comprova oferta concorrente ou demanda",
                    "IRRELEVANT": "Conteúdo incompatível com o sinal educacional pesquisado",
                    "INCONCLUSIVE": "Conteúdo insuficiente para determinar pertinência",
                }.get(result.selected_choice or "", "Julgamento inconclusivo")
            )
            if result.requires_human_review:
                reason = "Pertinência com confiança insuficiente; requer revisão"
            elif result.selected_choice == "CONTEXT" and scoped:
                reason = {
                    "JOB_MARKET": "Conteúdo setorial ou cargo sem competências verificáveis para esta pesquisa; preservado como contexto profissional",
                    "SOCIAL_VOICE": "Contexto de linguagem ou divulgação; não demonstra necessidade profissional específica nem volume de procura",
                    "PAID_COMPETITION": "Conteúdo de anunciante sem oferta educacional concorrente comprovada",
                    "OFFER": "Contexto do setor ou da instituição; não constitui oferta concorrente verificável",
                    "TRENDS": "Metadados ou contexto de busca sem série quantitativa utilizável",
                }.get(
                    row.evidence_type,
                    "Contexto útil à interpretação, sem métrica verificável para o cálculo",
                )
            if own:
                reason = "Conteúdo da própria instituição; preservado como contexto, sem contar como concorrência externa"
            trusted = not result.requires_human_review and not result.is_noul
            use_for = (
                {
                    "JOB_MARKET": ["employability", "curriculum"],
                    "SOCIAL_VOICE": ["audience_needs", "curriculum"],
                    "OFFER": ["competitive_offers", "pricing"],
                    "PAID_COMPETITION": ["paid_competition"],
                    "TRENDS": ["search_interest"],
                    "SEARCH_VOLUME": ["search_interest"],
                }.get(row.evidence_type, [])
                if relevant
                else []
            )
            if own:
                use_for = ["institution_context"]
            elif scoped and result.selected_choice == "CONTEXT" and trusted:
                use_for = ["sector_context"]
            exclusion_codes = []
            if not relevant:
                exclusion_codes = [
                    "own_institution"
                    if own
                    else "geography_unverified_or_out_of_scope"
                    if not scoped
                    else "review_required"
                    if not trusted
                    else "context_only"
                    if result.selected_choice == "CONTEXT"
                    else "insufficient_content"
                    if result.selected_choice == "INCONCLUSIVE"
                    else "irrelevant_signal"
                ]

            # Curadoria por finalidade (Tarefa 3.2): substituir 'accepted' universal por EvidenceUseAssessment
            assessments: dict[str, EvidenceUseAssessment] = {}

            # 1. Descoberta (discovery)
            discovery_usable = scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and not result.is_noul
            assessments[EvidencePurpose.DISCOVERY.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.DISCOVERY,
                usable=discovery_usable,
                confidence=result.confidence if discovery_usable else 0.5,
                observable_factors=["Escopo compatível"] if scoped else ["Escopo geográfico fora ou não comprovado"],
                quote_snippets=[row.title] if row.title else [],
                reason="Sinal útil para descoberta de termos, atores ou contexto" if discovery_usable else "Conteúdo fora de escopo ou inconclusivo para descoberta",
                rejection_cause=None if discovery_usable else ("out_of_scope" if not scoped else "unsupported_or_inconclusive"),
                next_step=None if discovery_usable else ("Revisar escopo geográfico" if not scoped else "Verificar se novos termos de busca são necessários"),
            )

            # 2. Preço (pricing)
            has_price = False
            price_val = None
            if isinstance(data, dict):
                price_val = data.get("total_price") or data.get("price_brl") or data.get("price") or (data.get("pricing") or {}).get("total_price")
                has_price = price_val is not None
            pricing_usable = row.evidence_type == "OFFER" and scoped and has_price and not result.is_noul
            assessments[EvidencePurpose.PRICING.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.PRICING,
                usable=pricing_usable,
                confidence=result.confidence if pricing_usable else 0.0,
                observable_factors=[f"Preço observado: {price_val}"] if has_price else ["Preço total não informado na oferta pública"],
                quote_snippets=[f"{row.title} - R$ {price_val}"] if has_price else [],
                reason="Oferta educacional com preço total observável e verificado" if pricing_usable else ("Oferta educacional sem preço explícito público" if row.evidence_type == "OFFER" else "Tipo de evidência não contém preço de curso"),
                rejection_cause=None if pricing_usable else ("price_missing_or_lead_wall" if row.evidence_type == "OFFER" else "not_a_course_offer"),
                next_step=None if pricing_usable else ("Consultar página de checkout ou contato comercial para obter precificação" if row.evidence_type == "OFFER" else None),
            )

            # 3. Concorrência direta (direct_competition)
            direct_usable = row.evidence_type in {"OFFER", "PAID_COMPETITION"} and not own and scoped and result.selected_choice == "RELEVANT" and trusted
            assessments[EvidencePurpose.DIRECT_COMPETITION.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.DIRECT_COMPETITION,
                usable=direct_usable,
                confidence=result.confidence if direct_usable else 0.5,
                observable_factors=["Concorrente externo verificado"] if (not own and row.evidence_type in {"OFFER", "PAID_COMPETITION"}) else ["Oferta própria ou tipo não concorrente"],
                quote_snippets=[row.title] if row.title else [],
                reason="Concorrente direto na mesma temática e categoria" if direct_usable else ("Oferta da própria instituição não concorre externamente" if own else "Não é concorrente direto"),
                rejection_cause=None if direct_usable else ("own_institution_not_competitor" if own else "not_a_direct_competitor"),
                next_step=None if direct_usable else ("Preservar como contexto interno da instituição" if own else "Analisar se atua como oferta adjacente"),
            )

            # 4. Concorrência adjacente (adjacent_competition)
            adjacent_usable = row.evidence_type in {"OFFER", "PAID_COMPETITION"} and not own and scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and trusted
            assessments[EvidencePurpose.ADJACENT_COMPETITION.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.ADJACENT_COMPETITION,
                usable=adjacent_usable,
                confidence=result.confidence if adjacent_usable else 0.5,
                observable_factors=["Oferta externa adjacente ou substituta"] if adjacent_usable else [],
                quote_snippets=[row.title] if row.title else [],
                reason="Oferta adjacente (cursos livres, extensões ou certificações)" if adjacent_usable else "Não atua como oferta adjacente",
                rejection_cause=None if adjacent_usable else "not_an_adjacent_offer",
            )

            # 5. Competências profissionais (workforce_competencies)
            workforce_usable = row.evidence_type == "JOB_MARKET" and scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and trusted
            assessments[EvidencePurpose.WORKFORCE_COMPETENCIES.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.WORKFORCE_COMPETENCIES,
                usable=workforce_usable,
                confidence=result.confidence if workforce_usable else 0.5,
                observable_factors=["Competências profissionais demandadas em vagas"] if workforce_usable else [],
                quote_snippets=[row.title] if row.title else [],
                reason="Vaga de trabalho expressa competências e requisitos do mercado" if workforce_usable else "Tipo de evidência não é vaga de emprego",
                rejection_cause=None if workforce_usable else "not_a_job_posting",
                next_step=None if workforce_usable else "Buscar vagas de trabalho para mapear competências profissionais",
            )

            # 6. Sinal de empregabilidade (employability_signal)
            employability_usable = row.evidence_type == "JOB_MARKET" and scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and trusted
            assessments[EvidencePurpose.EMPLOYABILITY_SIGNAL.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.EMPLOYABILITY_SIGNAL,
                usable=employability_usable,
                confidence=result.confidence if employability_usable else 0.5,
                observable_factors=["Absorção profissional no mercado"] if employability_usable else [],
                quote_snippets=[row.title] if row.title else [],
                reason="Sinal de absorção profissional e demanda de contratação" if employability_usable else "Não representa sinal de contratação",
                rejection_cause=None if employability_usable else "not_an_employment_signal",
            )

            # 7. Demanda de alunos (learner_demand)
            learner_usable = row.evidence_type in {"SOCIAL_VOICE", "TRENDS", "SEARCH_VOLUME"} and scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and trusted
            assessments[EvidencePurpose.LEARNER_DEMAND.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.LEARNER_DEMAND,
                usable=learner_usable,
                confidence=result.confidence if learner_usable else 0.5,
                observable_factors=["Interesse ou manifestação espontânea"] if learner_usable else [],
                quote_snippets=[row.title] if row.title else [],
                reason="Sinal de interesse ou dúvidas de potenciais alunos" if learner_usable else "Evidência não representa manifestação espontânea ou busca de alunos",
                rejection_cause=None if learner_usable else "not_learner_voice_or_search",
            )

            # 8. Contexto próprio (own_context)
            own_usable = own is True
            assessments[EvidencePurpose.OWN_CONTEXT.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.OWN_CONTEXT,
                usable=own_usable,
                confidence=1.0 if own_usable else 0.0,
                observable_factors=["Domínio ou identidade institucional própria"] if own_usable else [],
                quote_snippets=[row.title] if row.title and own_usable else [],
                reason="Evidência interna da própria instituição" if own_usable else "Evidência proveniente de fonte externa",
                rejection_cause=None if own_usable else "external_source",
            )

            # 9. Contexto de setor (industry_context)
            industry_usable = scoped and result.selected_choice in {"RELEVANT", "CONTEXT"} and not result.is_noul
            assessments[EvidencePurpose.INDUSTRY_CONTEXT.value] = EvidenceUseAssessment(
                purpose=EvidencePurpose.INDUSTRY_CONTEXT,
                usable=industry_usable,
                confidence=result.confidence if industry_usable else 0.5,
                observable_factors=["Contexto setorial geral"] if industry_usable else [],
                quote_snippets=[row.title] if row.title else [],
                reason="Contexto setorial ou profissional pertinente" if industry_usable else "Conteúdo fora de escopo do setor",
                rejection_cause=None if industry_usable else "out_of_scope_or_inconclusive",
            )

            multi_purpose = MultiPurposeAssessment(assessments=assessments)

            data["_qualification"] = {
                "accepted": relevant,
                "context_only": own
                or (
                    scoped
                    and result.selected_choice == "CONTEXT"
                    and not result.requires_human_review
                    and not result.is_noul
                ),
                "own_institution": own,
                "use_for": use_for,
                "usable_purposes": multi_purpose.usable_purposes,
                "use_assessments": {p: a.model_dump() for p, a in multi_purpose.assessments.items()},
                "exclusion_codes": exclusion_codes,
                "reason": reason,
                "decision_id": result.id,
                "pack_id": PACK,
                "qualification_version": QUALIFICATION_VERSION,
                "execution_cache_key": cache_key,
                "component_versions": comp_versions,
                "understanding_hash": understanding.snapshot_hash,
                "institution_hash": identity_hash,
                "review_skill_hash": skill_hash,
                "pack_version": pack.version,
                "pack_hash": pack_hash,
                "skill_snapshots": [skill.snapshot() for skill in [*review_skills, *actor_skills]],
                "confidence": result.confidence,
                "classification": result.selected_choice,
            }
            row.sanitized_data = data
            accepted += int(relevant)
            await self.session.commit()
        return {"accepted": accepted, "rejected": len(rows) - accepted}
