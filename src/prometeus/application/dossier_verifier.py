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

    def _collect_fact_metrics(self, facts: DossierFacts, evidence_ids: list[str]) -> list[float]:
        """Coleta todos os valores numéricos conhecidos das evidências citadas e dos índices gerais."""
        known_numbers: list[float] = []

        if "scoring_result" in evidence_ids:
            known_numbers.extend(
                [
                    round(facts.viability_score, 1),
                    round(facts.coverage_score * 100, 1),
                    round(facts.confidence_score * 100, 1),
                    round(facts.coverage_score, 2),
                    round(facts.confidence_score, 2),
                ]
            )
            for sub in facts.pillar_summaries.values():
                known_numbers.append(round(sub, 1))

        for eid in evidence_ids:
            item = facts.get_fact_item(eid)
            if item:
                # Extrai das métricas estruturadas
                for val in item.key_metrics.values():
                    if isinstance(val, (int, float)):
                        known_numbers.append(float(val))
                    elif isinstance(val, str):
                        known_numbers.extend(self._extract_numbers(val))
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
            if claim.claim_type == ClaimType.QUANTITATIVE:
                claim.verification_status = VerificationStatus.UNSUPPORTED
                claim.verification_note = (
                    "Claim quantitativa sem nenhum evidence_id de suporte fornecido"
                )
                return claim
            else:
                # Hipótese ou afirmação qualitativa geral sem evidência explícita
                claim.verification_status = VerificationStatus.VERIFIED
                claim.verification_note = (
                    "Afirmação qualitativa sem evidências específicas vinculadas"
                )
                return claim

        # Valida se os IDs citados existem
        invalid_ids = [eid for eid in claim.evidence_ids if eid not in known_ids]
        if invalid_ids:
            claim.verification_status = VerificationStatus.UNSUPPORTED
            claim.verification_note = f"Contém IDs de evidência inexistentes: {invalid_ids}"
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

        # Regra de aprovação do Gate C:
        # Zero alucinações e taxa de claims não suportadas <= 20%
        total_claims = len(dossier.claims) or 1
        unsupported_ratio = unsupported_count / total_claims

        if has_hallucination or unsupported_ratio > 0.20:
            dossier.status = DossierStatus.REVISION_REQUIRED
            logger.warning(
                f"Dossiê da análise {facts.analysis_id} requer revisão: "
                f"hallucination={has_hallucination}, unsupported_ratio={unsupported_ratio:.2%}"
            )
        else:
            dossier.status = DossierStatus.VERIFIED

        return dossier
