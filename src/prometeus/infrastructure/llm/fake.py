from typing import Any

from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFacts,
    DossierOutput,
    DossierSection,
    DossierStatus,
    SupportLevel,
    VerificationStatus,
)
from prometeus.domain.ports.generative_model import GenerativeModelPort


class FakeGenerativeModel(GenerativeModelPort):
    """Implementação em memória para testes unitários, contratuais e CI."""

    def __init__(
        self,
        canned_keywords: list[str] | None = None,
        canned_text: str = "Texto gerado para teste",
        canned_dossier: DossierOutput | None = None,
        simulate_error: bool = False,
    ) -> None:
        self.canned_keywords = canned_keywords
        self.canned_text = canned_text
        self.canned_dossier = canned_dossier
        self.simulate_error = simulate_error
        self.call_history: list[dict[str, str]] = []

    async def generate_keyword_candidates(
        self,
        course_title: str,
        description: str,
        target_audience: str,
        max_candidates: int = 15,
    ) -> list[str]:
        if self.simulate_error:
            raise ConnectionError("Falha simulada na API generativa")

        self.call_history.append(
            {
                "course_title": course_title,
                "description": description,
                "target_audience": target_audience,
            }
        )

        if self.canned_keywords is not None:
            return self.canned_keywords[:max_candidates]

        # Gera candidatos determinísticos baseados nas palavras do título
        title_lower = course_title.lower()
        candidates = [
            f"curso {title_lower}",
            f"mba {title_lower}",
            f"especializacao {title_lower}",
            f"pos graduacao {title_lower}",
            f"como funciona {title_lower}",
            f"mercado de trabalho {title_lower}",
            f"treinamento {title_lower}",
        ]
        return candidates[:max_candidates]

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        if self.simulate_error:
            raise ConnectionError("Falha simulada na API generativa")

        return self.canned_text

    async def revise_dossier(
        self,
        facts: DossierFacts,
        draft: DossierOutput | dict[str, Any],
        verification_report: dict[str, Any],
        prompt_version: str = "dossier-v1",
    ) -> DossierOutput:
        return await self.synthesize_dossier(facts, prompt_version)

    async def synthesize_dossier(
        self,
        facts: DossierFacts,
        prompt_version: str = "dossier-v1",
    ) -> DossierOutput:
        if self.simulate_error:
            raise ConnectionError("Falha simulada na API generativa")

        if self.canned_dossier is not None:
            return self.canned_dossier

        evidence_ids = [item.evidence_id for item in facts.items]
        first_ev = evidence_ids[0] if evidence_ids else "scoring_result"

        claim1 = DossierClaim(
            claim_id="CLM-01",
            statement=f"O curso {facts.course_name} atingiu score de viabilidade de {facts.viability_score:.1f}.",
            claim_type=ClaimType.QUANTITATIVE,
            evidence_ids=["scoring_result"],
            support_level=SupportLevel.OBSERVED,
            verification_status=VerificationStatus.VERIFIED,
        )
        claim2 = DossierClaim(
            claim_id="CLM-02",
            statement=f"Existe evidência de demanda registrada para o mercado com recomendação {facts.recommendation}.",
            claim_type=ClaimType.QUALITATIVE,
            evidence_ids=[first_ev],
            support_level=SupportLevel.OBSERVED,
            verification_status=VerificationStatus.VERIFIED,
        )

        sections = [
            DossierSection(
                section_id="exec_summary",
                title="Resumo Executivo",
                target_audience="executive",
                content=(
                    f"A análise do curso {facts.course_name} resultou em recomendação {facts.recommendation} "
                    f"com score V={facts.viability_score:.1f} e cobertura de dados de {facts.coverage_score * 100:.0f}%."
                ),
                claim_ids=["CLM-01"],
            ),
            DossierSection(
                section_id="academic_fit",
                title="Parecer Acadêmico e Pedagógico",
                target_audience="academic",
                content="A estrutura programática atende aos requisitos de competências observados no mercado.",
                claim_ids=["CLM-02"],
            ),
            DossierSection(
                section_id="market_strategy",
                title="Estratégia de Posicionamento e Go-to-Market",
                target_audience="marketing",
                content=f"Recomenda-se posicionamento com foco no público-alvo '{facts.target_audience}'.",
                claim_ids=["CLM-02"],
            ),
        ]

        return DossierOutput(
            analysis_id=facts.analysis_id,
            prompt_version=prompt_version,
            model_name="fake-gpt-4o",
            executive_summary=sections[0].content,
            sections=sections,
            claims=[claim1, claim2],
            facts_hash=facts.compute_facts_hash(),
            status=DossierStatus.VERIFIED,
            cost_usd=0.002,
        )
