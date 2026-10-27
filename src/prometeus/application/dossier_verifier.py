"""Verificador determinístico de factualidade, referências e números do dossiê (TOOL-15).

Implementa a etapa 13 do workflow: bloqueia afirmações não sustentadas, detecta números
inventados (alucinação) e neutraliza tentativas de manipulação ou prompt injection.
"""

from __future__ import annotations

import logging
import re

from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFacts,
    DossierOutput,
    DossierStatus,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

# Padrões suspeitos de prompt injection em claims
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+(override|prompt)",
    r"desconsidere\s+(as\s+)?instru[çc][õo]es",
    r"voc[êe]\s+agora\s+[ée]\s+um",
    r"alterar\s+score\s+para",
]


class DossierVerifier:
    """Verificador factual que audita cada claim do dossiê contra o DossierFacts canônico."""

    def __init__(self, tolerance_pct: float = 0.05) -> None:
        self.tolerance_pct = tolerance_pct

    def _extract_numbers(self, text: str) -> list[float]:
        """Extrai números inteiros e decimais (incluindo formato brasileiro 1.000,50 e 1000.50)."""
        numbers: list[float] = []
        # Normaliza formato brasileiro 1.500,00 -> 1500.00
        normalized = re.sub(r"(\d+)\.(\d{3})", r"\1\2", text)
        normalized = re.sub(r"(\d+),(\d+)", r"\1.\2", normalized)

        for token in re.findall(r"\b\d+(?:\.\d+)?\b", normalized):
            try:
                numbers.append(float(token))
            except ValueError:
                continue
        return numbers

    @staticmethod
    def _extract_urls(text: str) -> list[str]:
        return re.findall(r"https?://[^\s)\]}>]+", text)

    def _collect_fact_metrics(self, facts: DossierFacts, evidence_ids: list[str]) -> list[float]:
        """Coleta todos os valores numéricos conhecidos das evidências citadas e dos índices gerais."""
        known_numbers: list[float] = [float(len(evidence_ids))]

        if "scoring_result" in evidence_ids:
            known_numbers.extend(
                [
                    round(facts.viability_score, 1),
                    round(facts.viability_score, 2),
                    round(facts.coverage_score * 100, 1),
                    round(facts.coverage_score * 100, 2),
                    round(facts.confidence_score * 100, 1),
                    round(facts.confidence_score * 100, 2),
                    round(facts.coverage_score, 2),
                    round(facts.coverage_score, 4),
                    round(facts.confidence_score, 2),
                    round(facts.confidence_score, 4),
                    float(len(facts.items)),
                    float(len(facts.pillar_summaries)),
                ]
            )
            for sub in facts.pillar_summaries.values():
                known_numbers.append(round(sub, 1))
                known_numbers.append(round(sub, 2))
            if facts.course_understanding:
                known_numbers.extend(self._extract_numbers(str(facts.course_understanding)))
            if facts.research_plan:
                known_numbers.extend(self._extract_numbers(str(facts.research_plan)))
            if facts.limitations:
                known_numbers.extend(self._extract_numbers(" ".join(facts.limitations)))

        for eid in evidence_ids:
            item = facts.get_fact_item(eid)
            if item:
                # Extrai das métricas estruturadas
                for val in item.key_metrics.values():
                    if isinstance(val, (int, float)):
                        fval = float(val)
                        known_numbers.append(fval)
                        if 0 < fval <= 1.0:
                            known_numbers.append(round(fval * 100, 1))
                            known_numbers.append(round(fval * 100, 2))
                    elif isinstance(val, str):
                        known_numbers.extend(self._extract_numbers(val))
                if item.title:
                    known_numbers.extend(self._extract_numbers(item.title))
                # Extrai do resumo textual
                if item.summary:
                    known_numbers.extend(self._extract_numbers(item.summary))

        return known_numbers

    def _is_number_supported(self, claimed: float, known_numbers: list[float]) -> bool:
        """Checa se o número alegado possui correspondência próxima em algum número conhecido."""
        for known in known_numbers:
            if known == 0 and claimed == 0:
                return True
            if known > 0 and abs(claimed - known) / known <= self.tolerance_pct:
                return True
            if abs(claimed - known) < 0.1:
                return True
        return False

    def verify_claim(self, claim: DossierClaim, facts: DossierFacts) -> DossierClaim:
        """Audita uma claim individual e atualiza seu status de verificação."""
        # 1. Checagem de Prompt Injection no texto da claim
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, claim.statement, re.IGNORECASE):
                claim.verification_status = VerificationStatus.REJECTED
                claim.verification_note = (
                    "Padrão de injeção ou manipulação de instruções detectado na claim"
                )
                return claim

        # 2. Checagem de referências a evidências
        known_ids = facts.get_all_known_ids()
        if not claim.evidence_ids:
            claim.verification_status = VerificationStatus.UNSUPPORTED
            claim.verification_note = "Claim sem nenhum evidence_id de suporte fornecido"
            return claim

        # Valida se os IDs citados existem
        invalid_ids = [eid for eid in claim.evidence_ids if eid not in known_ids]
        if invalid_ids:
            claim.verification_status = VerificationStatus.UNSUPPORTED
            claim.verification_note = f"Contém IDs de evidência inexistentes: {invalid_ids}"
            return claim

        claimed_urls = self._extract_urls(claim.statement)
        if claimed_urls:
            cited_urls = {
                item.source_url
                for evidence_id in claim.evidence_ids
                if (item := facts.get_fact_item(evidence_id)) is not None and item.source_url
            }
            invalid_urls = [url for url in claimed_urls if url not in cited_urls]
            if invalid_urls:
                claim.verification_status = VerificationStatus.UNSUPPORTED
                claim.verification_note = (
                    f"Contém URLs não presentes nas evidências citadas: {invalid_urls}"
                )
                return claim

        # 3. Checagem de consistência numérica para claims quantitativas
        if claim.claim_type == ClaimType.QUANTITATIVE:
            claim_numbers = self._extract_numbers(claim.statement)
            if not claim_numbers:
                claim.verification_status = VerificationStatus.VERIFIED
                return claim

            known_numbers = self._collect_fact_metrics(facts, claim.evidence_ids)

            unsupported_numbers = []
            for num in claim_numbers:
                if not self._is_number_supported(num, known_numbers):
                    unsupported_numbers.append(num)

            if unsupported_numbers:
                claim.verification_status = VerificationStatus.FLAGGED_HALLUCINATION
                claim.verification_note = f"Números alegados ({unsupported_numbers}) não foram encontrados nas evidências citadas"
                return claim

        claim.verification_status = VerificationStatus.VERIFIED
        claim.verification_note = "Claim verificada e consistente com as evidências"
        return claim

    def verify(self, dossier: DossierOutput, facts: DossierFacts) -> DossierOutput:
        """Audita integralmente todas as claims e seções do dossiê."""
        has_hallucination = False
        unsupported_count = 0
        structural_error = False

        if (
            dossier.analysis_id != facts.analysis_id
            or dossier.facts_hash != facts.compute_facts_hash()
        ):
            structural_error = True
        if not dossier.executive_summary.strip() or not dossier.sections or not dossier.claims:
            structural_error = True

        claim_ids = [claim.claim_id for claim in dossier.claims]
        if len(claim_ids) != len(set(claim_ids)):
            structural_error = True
        known_claim_ids = set(claim_ids)
        referenced_claim_ids = {
            claim_id for section in dossier.sections for claim_id in section.claim_ids
        }
        if not referenced_claim_ids.issubset(known_claim_ids):
            structural_error = True
        if known_claim_ids - referenced_claim_ids:
            structural_error = True

        verified_claims: list[DossierClaim] = []
        for claim in dossier.claims:
            verified = self.verify_claim(claim, facts)
            verified_claims.append(verified)

            if verified.verification_status in (
                VerificationStatus.FLAGGED_HALLUCINATION,
                VerificationStatus.REJECTED,
            ):
                has_hallucination = True
            elif verified.verification_status == VerificationStatus.UNSUPPORTED:
                unsupported_count += 1

        dossier.claims = verified_claims

        if structural_error or has_hallucination or unsupported_count:
            dossier.status = DossierStatus.REVISION_REQUIRED
            logger.warning(
                f"Dossiê da análise {facts.analysis_id} requer revisão: "
                f"structural_error={structural_error}, hallucination={has_hallucination}, "
                f"unsupported_claims={unsupported_count}"
            )
        else:
            dossier.status = DossierStatus.VERIFIED

        return dossier
