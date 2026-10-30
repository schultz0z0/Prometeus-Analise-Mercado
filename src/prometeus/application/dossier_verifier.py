"""Verificador determinístico de factualidade, referências e números do dossiê (TOOL-15).

Implementa a etapa 13 do workflow: bloqueia afirmações não sustentadas, detecta números
inventados (alucinação) e neutraliza tentativas de manipulação ou prompt injection.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from prometeus.domain.dossiers import (
    DataIntegrityReview,
    DossierClaim,
    DossierFacts,
    DossierOutput,
    DossierStatus,
    FactualDraftingReview,
    ReviewStatus,
    SeniorAnalyticalReview,
    ThreeFoldDossierReview,
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

    def __init__(self, tolerance_pct: float = 0.0) -> None:
        self.tolerance_pct = tolerance_pct

    def _extract_numbers(self, text: str) -> list[float]:
        """Extrai números inteiros e decimais (incluindo formato brasileiro 1.000,50 e 1000.50)."""
        numbers: list[float] = []
        # Normaliza formato brasileiro 1.500,00 -> 1500.00
        normalized = re.sub(r"(\d+)\.(\d{3})", r"\1\2", text)
        normalized = re.sub(r"(\d+),(\d+)", r"\1.\2", normalized)

        for token in re.findall(
            r"(?<![\w\d])[+-]?\d+(?:\.\d+)?(?=\b|(?:h|horas?|x)\b)", normalized, re.I
        ):
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
        known_numbers: list[float] = []

        if "scoring_result" in evidence_ids:
            known_numbers.extend(
                [
                    round(facts.viability_score, 1),
                    round(facts.viability_score, 2),
                    round(facts.viability_score),
                    round(facts.coverage_score * 100),
                    round(facts.coverage_score * 100, 1),
                    round(facts.coverage_score * 100, 2),
                    round(facts.confidence_score * 100, 1),
                    round(facts.confidence_score * 100, 2),
                    round(facts.confidence_score * 100),
                    round(facts.coverage_score, 2),
                    round(facts.coverage_score, 4),
                    round(facts.confidence_score, 2),
                    round(facts.confidence_score, 4),
                ]
            )
            for sub in facts.pillar_summaries.values():
                known_numbers.append(round(sub, 1))
                known_numbers.append(round(sub, 2))

        for eid in evidence_ids:
            item = facts.get_fact_item(eid)
            if item:
                # Extrai das métricas estruturadas
                for val in item.key_metrics.values():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
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
            if abs(claimed - known) < 0.000001:
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
        if self._extract_numbers(claim.statement):
            numeric_text = claim.statement
            if "scoring_result" in claim.evidence_ids:
                # O denominador da escala é metadado do índice, não observação de mercado.
                numeric_text = re.sub(r"(?<=\d)\s*/\s*100\b", "", numeric_text)
            claim_numbers = self._extract_numbers(numeric_text)
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

    def verify_data_integrity(self, facts: DossierFacts) -> DataIntegrityReview:
        """Revisão 1: Integridade dos dados (source -> observation -> brief).

        Verifica se o conteúdo essencial foi preservado sem perdas determinísticas silenciosas.
        """
        report = facts.analysis_audit.get("integrity_report", {})
        source_count = int(report.get("source_count", len(facts.items)))
        observations_count = int(report.get("observations_count", len(facts.items)))
        brief_facts_count = int(report.get("brief_facts_count", len(facts.items)))
        missing_desc = int(report.get("missing_descriptions_count", 0))
        omissions = list(report.get("omissions", []))
        raw_status = str(report.get("status", "INTACT")).upper()

        issues: list[dict[str, Any]] = []
        notes: list[str] = []

        if missing_desc > 0:
            issues.append(
                {
                    "path": "integrity.job_descriptions",
                    "code": "missing_job_descriptions",
                    "message": f"{missing_desc} descrições de vagas não foram preservadas no brief.",
                }
            )

        if raw_status == "FAILED":
            status = ReviewStatus.FAIL
            issues.append(
                {
                    "path": "integrity",
                    "code": "data_integrity_failed",
                    "message": "Falha crítica de integridade na passagem source -> observation -> brief.",
                }
            )
        elif raw_status == "DEGRADED" or missing_desc > 0 or omissions:
            status = ReviewStatus.WARN
            notes.append("Ocorrência de perda de campos ou descrições parciais preservadas como limitações.")
        else:
            status = ReviewStatus.PASS

        return DataIntegrityReview(
            status=status,
            source_count=source_count,
            observations_count=observations_count,
            brief_facts_count=brief_facts_count,
            missing_descriptions_count=missing_desc,
            omissions=omissions,
            issues=issues,
            notes=notes,
        )

    def verify_senior_analytical_quality(
        self, dossier: DossierOutput, facts: DossierFacts
    ) -> SeniorAnalyticalReview:
        """Revisão 2: Qualidade analítica sênior.

        Verifica adequação à pergunta, independência, materialidade, alternativas, proxies e contraprovas.
        """
        issues: list[dict[str, Any]] = []
        actionable_recommendations: list[str] = []

        # 1. Pergunta de decisão e cobertura temática
        question_coverage: dict[str, bool] = {
            "portfolio_fit": bool(
                dossier.highlights.curriculum_alignment
                or any(
                    re.search(r"\b(?:ementa|curricular|curr[íi]culo|portf[óo]lio)\b", s.title, re.I)
                    for s in dossier.sections
                )
            ),
            "competitors": bool(
                dossier.highlights.competitors
                or any(
                    re.search(r"\b(?:concorr[êe]ncia|concorrentes?)\b", s.title + " " + s.content, re.I)
                    for s in dossier.sections
                )
            ),
            "professional_demand": any(
                re.search(r"\b(?:vagas?|compet[êe]ncias?|profissional|empregabilidade)\b", c.statement, re.I)
                for c in dossier.claims
            ),
            "learner_demand": any(
                re.search(r"\b(?:p[úu]blico|demanda|interesse|alunos?)\b", s.title + " " + s.content, re.I)
                for s in dossier.sections
            ),
            "economics_and_pricing": bool(
                any(
                    re.search(r"\b(?:pre[çc]o|investimento|viabilidade|mensalidade|parcelas?)\b", c.statement, re.I)
                    for c in dossier.claims
                )
                or any(
                    re.search(r"\b(?:viabilidade|pre[çc]o|investimento)\b", s.title, re.I)
                    for s in dossier.sections
                )
            ),
            "strategic_options_and_risks": bool(
                dossier.highlights.cons
                or dossier.highlights.validation_criteria
                or dossier.highlights.action_recommendations
                or any(
                    re.search(r"\b(?:riscos?|limita[çc][õo]es?|amea[çc]as?|fraquezas?)\b", s.content, re.I)
                    for s in dossier.sections
                )
            ),
        }

        # 2. Independência e não-canibalização: ENS não é concorrente externo
        independence_verified = True
        declared_inst = str(
            facts.analysis_audit.get("declared_offer", {}).get("institution") or "ENS"
        ).strip().lower()
        for comp in dossier.highlights.competitors:
            label_lower = comp.label.strip().lower()
            if "ens" in label_lower or "escola nacional de seguros" in label_lower or (declared_inst and declared_inst in label_lower):
                if "própria" not in label_lower and "interna" not in label_lower:
                    independence_verified = False
                    issues.append(
                        {
                            "path": f"highlights.competitors.{comp.label}",
                            "code": "own_institution_as_competitor",
                            "message": f"A própria instituição '{comp.label}' foi listada como concorrente externo sem qualificação de oferta interna.",
                        }
                    )
                    actionable_recommendations.append(
                        "Módulo de competidores: filtrar e separar ofertas internas do quadro de concorrência externa."
                    )

        # 3. Qualificação de proxies e inferências analíticas sênior
        proxies_properly_qualified = True
        disallowed_analytical_patterns = [
            (
                re.compile(
                    r"\b(?:vagas?|postos?|buscas?|pesquisas?|trends?|picos?)\b.*?(?:comprovam?|provam?|garantem?|geram?|convertem?|indicam?)\b.*?(?:matr[íi]culas?|alunos?|demanda\s+direta|demanda\s+correspondente)\b",
                    re.IGNORECASE,
                ),
                "job_or_search_not_enrollment_demand",
                "Vagas de emprego e interesse de busca são proxies de competência e atenção, não comprovação de matrículas ou demanda direta por MBA.",
                "Módulo de demanda: diferenciar demanda de competências do mercado de trabalho de intenção real de matrícula educacional.",
            ),
            (
                re.compile(
                    r"\b(?:ens|escola nacional de seguros|an[úu]ncio da ens)\b.*?(?:concorrente\s+externo|press[ãa]o\s+do\s+mercado|pressionando\s+o\s+mercado)\b",
                    re.IGNORECASE,
                ),
                "own_institution_as_external_competitor",
                "Comunicação própria da ENS não comprova concorrente externo pressionando o mercado.",
                "Módulo de concorrentes: separar comunicação da própria instituição do mapeamento concorrencial externo.",
            ),
            (
                re.compile(
                    r"\b(?:curso\s+livre|16h|workshop|curta\s+dura[çc][ãa]o)\b.*?(?:concorre\s+diretamente|mesma\s+titula[çc][ãa]o)\b.*?(?:mba|p[óo]s-gradua[çc][ãa]o|360h)\b",
                    re.IGNORECASE,
                ),
                "category_degree_mismatch",
                "Cursos livres de curta carga horária não equivalem a programas acadêmicos de MBA ou titulação de pós-graduação.",
                "Módulo de categorização: respeitar hierarquia de titulação e carga horária na comparação de ofertas.",
            ),
            (
                re.compile(
                    r"\b(?:culin[áa]ria|receitas?|gastronomia)\b.*?(?:mercado\s+de\s+seguros|setor\s+securit[áa]rio)\b",
                    re.IGNORECASE,
                ),
                "thematic_false_cognate",
                "Conteúdo de culinária é falso cognato temático sem pertinência com o mercado securitário.",
                "Módulo de qualificação: filtrar falsos cognatos temáticos antes da consolidação de evidências.",
            ),
            (
                re.compile(
                    r"\b(?:peticionamento\s+em\s+massa)\b.*?(?:demanda\s+por\s+profissionais\s+p[óo]s-graduados)\b",
                    re.IGNORECASE,
                ),
                "workforce_skill_mismatch",
                "Atividades operacionais de peticionamento em massa não caracterizam demanda por profissionais especialistas pós-graduados.",
                "Módulo de competências: mapear requisitos de formação de vagas e descartar rotinas puramente operacionais.",
            ),
            (
                re.compile(
                    r"\b(?:404|p[áa]gina\s+n[ãa]o\s+encontrada|url\s+404)\b.*?(?:oferta\s+ativa|pre[çc]o)\b|\b(?:oferta\s+ativa|pre[çc]o)\b.*?(?:404|url\s+404)\b",
                    re.IGNORECASE,
                ),
                "failed_source_cannot_support_active_offer",
                "Página com erro 404 ou falha de coleta não sustenta oferta ativa ou preço de mercado.",
                "Módulo de aquisição: descartar URLs com código HTTP 404 da base de ofertas ativas e precificação.",
            ),
            (
                re.compile(
                    r"\baus[êe]ncia\s+de\s+concorrente\b.*?(?:inexist[êe]ncia\s+de\s+concorr[êe]ncia|demanda\s+zero)\b",
                    re.IGNORECASE,
                ),
                "absence_of_exact_title_not_zero_competition",
                "Ausência de concorrente com título exato não equivale à inexistência de concorrência temática ampla ou demanda zero.",
                "Módulo estratégico: classificar ausência de concorrência como oportunidade a validar, não garantia de monopólio.",
            ),
            (
                re.compile(
                    r"\b(?:artigo|blog|not[íi]cia)\b.*?(?:indicador\s+quantitativo\s+recente)\b",
                    re.IGNORECASE,
                ),
                "qualitative_source_not_recent_indicator",
                "Artigo opinativo ou de blog não comprova indicador quantitativo recente do setor.",
                "Módulo de evidências: não transformar postagens de blog ou artigos opinativos em métricas quantitativas.",
            ),
            (
                re.compile(
                    r"\bpre[çc]o\s+estimado\s+por\s+hora-aula\b",
                    re.IGNORECASE,
                ),
                "unsupported_price_metric",
                "Preço estimado por hora-aula não observado nos dados coletados constitui métrica não sustentada.",
                "Módulo de precificação: utilizar apenas valores e periodicidades efetivamente observados na fonte.",
            ),
            (
                re.compile(
                    r"\b(?:crescimento|volume|pr[êe]mios?)\b.*?(?:segurador|susep)\b.*?(?:converte|multiplica|garante)\b.*?(?:matr[íi]culas?|alunos?)\b",
                    re.IGNORECASE,
                ),
                "macro_stats_not_enrollment",
                "Estatísticas macroeconômicas ou de prêmio de seguros informam contexto setorial, não taxa de conversão em matrículas.",
                "Módulo de demanda: dados setoriais informam contexto de mercado, não multiplicadores de matrícula.",
            ),
        ]

        for claim in dossier.claims:
            stmt = claim.statement
            for pattern, code, msg, rec in disallowed_analytical_patterns:
                if pattern.search(stmt):
                    proxies_properly_qualified = False
                    issues.append(
                        {
                            "path": f"claims.{claim.claim_id}",
                            "code": code,
                            "message": msg,
                            "text_excerpt": stmt[:300],
                        }
                    )
                    if rec not in actionable_recommendations:
                        actionable_recommendations.append(rec)
            if re.search(r"\bmatr[íi]culas? garantidas?\b", stmt, re.IGNORECASE):
                proxies_properly_qualified = False
                issues.append(
                    {
                        "path": f"claims.{claim.claim_id}",
                        "code": "guaranteed_enrollment_prohibited",
                        "message": "Promessa de matrículas garantidas é expressamente vedada na análise de inteligência educacional.",
                        "text_excerpt": stmt[:300],
                    }
                )

        # 4. Materialidade e alternativas
        material_alternatives_present = True
        if not dossier.highlights.validation_criteria and not dossier.highlights.action_recommendations:
            actionable_recommendations.append(
                "Redator: estruturar validações prévias e ações recomendadas para a decisão institucional."
            )

        # 5. Contraprovas e limites explicitados
        counterevidence_analyzed = True
        if facts.counterevidence:
            has_cons = bool(dossier.highlights.cons)
            risk_counterevidence_pattern = re.compile(
                r"\b(?:contraprovas?|limita[çc][õo]es?|pontos?\s+fracos?|riscos?\s+(?:comerciais?|de\s+mercado|do\s+curso|da\s+oferta)|desvantagens?)\b",
                re.IGNORECASE,
            )
            has_counterevidence_in_text = any(
                bool(risk_counterevidence_pattern.search(s.content)) for s in dossier.sections
            )
            if not has_cons and not has_counterevidence_in_text:
                counterevidence_analyzed = False
                issues.append(
                    {
                        "path": "highlights.cons",
                        "code": "unacknowledged_counterevidence",
                        "message": "Contraprovas ou limitações documentadas nos fatos aprovados não foram avaliadas nos riscos ou leituras do dossiê.",
                    }
                )
                actionable_recommendations.append(
                    "Redator: registrar explicitamente as limitações e contraprovas identificadas na seção de riscos e pontos fracos."
                )

        if not independence_verified or not proxies_properly_qualified:
            status = ReviewStatus.FAIL
        elif not counterevidence_analyzed or not all(question_coverage.values()):
            status = ReviewStatus.WARN
        else:
            status = ReviewStatus.PASS

        return SeniorAnalyticalReview(
            status=status,
            question_coverage=question_coverage,
            independence_verified=independence_verified,
            material_alternatives_present=material_alternatives_present,
            counterevidence_analyzed=counterevidence_analyzed,
            proxies_properly_qualified=proxies_properly_qualified,
            issues=issues,
            actionable_recommendations=actionable_recommendations,
        )

    def verify_factual_drafting(
        self, dossier: DossierOutput, facts: DossierFacts
    ) -> FactualDraftingReview:
        """Revisão 3: Factualidade da redação.

        Verifica números, unidades, identidades, claims e ausência de alucinações e prompt injection.
        """
        issues: list[dict[str, Any]] = []
        notes: list[str] = []
        numeric_consistency = True
        no_injection = True
        unsupported_count = 0
        hallucination_count = 0

        # 1. Identidade e hash dos fatos
        identity_consistency = (
            dossier.analysis_id == facts.analysis_id
            and dossier.facts_hash == facts.compute_facts_hash()
        )
        if not identity_consistency:
            issues.append(
                {
                    "path": "identity",
                    "code": "facts_mismatch",
                    "message": "Análise ou hash diverge dos fatos aprovados.",
                }
            )

        # 2. Varredura e verificação de cada claim
        verified_claims: list[DossierClaim] = []
        for claim in dossier.claims:
            for pattern in INJECTION_PATTERNS:
                if re.search(pattern, claim.statement, re.IGNORECASE):
                    no_injection = False
                    issues.append(
                        {
                            "path": f"claims.{claim.claim_id}",
                            "code": "prompt_injection_detected",
                            "message": "Padrão de injeção ou manipulação de instruções detectado na claim.",
                            "text_excerpt": claim.statement[:300],
                        }
                    )
                    break

            verified = self.verify_claim(claim, facts)
            verified_claims.append(verified)

            if verified.verification_status == VerificationStatus.FLAGGED_HALLUCINATION:
                numeric_consistency = False
                hallucination_count += 1
                issues.append(
                    {
                        "path": f"claims.{verified.claim_id}",
                        "code": verified.verification_status.value,
                        "message": verified.verification_note or "Alucinação numérica detectada.",
                        "text_excerpt": verified.statement[:300],
                        "evidence_ids": verified.evidence_ids,
                    }
                )
            elif verified.verification_status in (
                VerificationStatus.UNSUPPORTED,
                VerificationStatus.REJECTED,
            ):
                unsupported_count += 1
                issues.append(
                    {
                        "path": f"claims.{verified.claim_id}",
                        "code": verified.verification_status.value,
                        "message": verified.verification_note or "Afirmação sem suporte factual.",
                        "text_excerpt": verified.statement[:300],
                        "evidence_ids": verified.evidence_ids,
                    }
                )

        dossier.claims = verified_claims

        # 3. Verificação de blocos de texto referenciados
        def check_text(text: str, refs: list[str]) -> DossierClaim:
            evidence_ids = list(
                dict.fromkeys(
                    eid
                    for claim in verified_claims
                    if claim.claim_id in refs
                    for eid in claim.evidence_ids
                )
            )
            candidate = DossierClaim(statement=text, evidence_ids=evidence_ids)
            return self.verify_claim(candidate, facts)

        for index, (text, refs) in enumerate(dossier.referenced_blocks()):
            checked_text = check_text(text, refs)
            if checked_text.verification_status != VerificationStatus.VERIFIED:
                if checked_text.verification_status == VerificationStatus.FLAGGED_HALLUCINATION:
                    numeric_consistency = False
                    hallucination_count += 1
                else:
                    unsupported_count += 1
                issues.append(
                    {
                        "path": f"blocks.{index}",
                        "code": checked_text.verification_status.value,
                        "message": checked_text.verification_note or "Texto sem suporte verificado.",
                        "text_excerpt": text[:300],
                        "evidence_ids": checked_text.evidence_ids,
                    }
                )

        # 4. Proibição de identificadores técnicos visíveis no schema >= 2
        if dossier.schema_version >= 2:
            technical = re.compile(
                r"\b(?:viability_score|coverage_score|confidence_score|scoring_result|syllabus_fit|paid_competition|internal_history|search_and_media|evidence_ids?|INSUFFICIENT_EVIDENCE|APPROVED_WITH_ADJUSTMENTS)\b",
                re.I,
            )
            visible = [text for text, _ in dossier.referenced_blocks()] + [
                claim.statement for claim in dossier.claims
            ]
            for text in visible:
                if technical.search(text):
                    issues.append(
                        {
                            "path": "visible_text",
                            "code": "technical_identifier",
                            "message": "Identificador técnico no texto executivo.",
                            "text_excerpt": text[:300],
                        }
                    )

        if (
            not identity_consistency
            or not numeric_consistency
            or not no_injection
            or hallucination_count > 0
            or unsupported_count > 0
            or any(issue["code"] == "technical_identifier" for issue in issues)
        ):
            status = ReviewStatus.FAIL
        else:
            status = ReviewStatus.PASS

        return FactualDraftingReview(
            status=status,
            numeric_consistency=numeric_consistency,
            identity_consistency=identity_consistency,
            no_hallucinations=(hallucination_count == 0),
            no_injection=no_injection,
            unsupported_claims_count=unsupported_count,
            hallucinations_count=hallucination_count,
            issues=issues,
            notes=notes,
        )

    def verify(self, dossier: DossierOutput, facts: DossierFacts) -> DossierOutput:
        """Audita integralmente todas as claims, seções e três dimensões de revisão do dossiê."""
        # Recomputed by code; never trust diagnostics supplied by a model.
        dossier.verification_issues = []

        def issue(
            path: str,
            code: str,
            message: str,
            text: str = "",
            evidence_ids: list[str] | None = None,
        ) -> None:
            dossier.verification_issues.append(
                {
                    "path": path,
                    "code": code,
                    "message": message[:500],
                    "text_excerpt": text[:300],
                    "evidence_ids": list(evidence_ids or []),
                }
            )

        structural_error = False

        if (
            dossier.analysis_id != facts.analysis_id
            or dossier.facts_hash != facts.compute_facts_hash()
        ):
            structural_error = True
            issue("identity", "facts_mismatch", "Análise ou hash diverge dos fatos aprovados.")
        if not dossier.executive_summary.strip() or not dossier.sections or not dossier.claims:
            structural_error = True
            issue(
                "structure", "required_content_missing", "Resumo, seções e claims são obrigatórios."
            )

        claim_ids = [claim.claim_id for claim in dossier.claims]
        if len(claim_ids) != len(set(claim_ids)):
            structural_error = True
            issue("claims", "duplicate_claim_id", "Identificadores de claims duplicados.")
        known_claim_ids = set(claim_ids)
        highlights = dossier.highlights
        extra_refs = [*highlights.pros, *highlights.cons, *dossier.executive_summary_claim_ids]
        for block in highlights.validation_criteria:
            extra_refs.extend(block.claim_ids)
        for action in highlights.action_recommendations:
            extra_refs.extend(action.claim_ids)
        if not set(extra_refs).issubset(known_claim_ids):
            structural_error = True
            issue(
                "highlights",
                "unknown_claim_reference",
                "Destaques ou resumo citam claims inexistentes.",
            )
        if dossier.schema_version >= 2 and not dossier.executive_summary_claim_ids:
            structural_error = True
            issue(
                "executive_summary", "missing_claim_reference", "Resumo sem referências próprias."
            )
        referenced_claim_ids = {
            claim_id for section in dossier.sections for claim_id in section.claim_ids
        }
        if not referenced_claim_ids.issubset(known_claim_ids):
            structural_error = True
            issue("sections", "unknown_claim_reference", "Seções citam claims inexistentes.")
        if known_claim_ids - referenced_claim_ids:
            structural_error = True
            issue("sections", "unreferenced_claim", "Há claims sem vínculo com nenhuma seção.")

        # Executa as três revisões especializadas
        integrity_review = self.verify_data_integrity(facts)
        drafting_review = self.verify_factual_drafting(dossier, facts)
        analytical_review = self.verify_senior_analytical_quality(dossier, facts)

        # Consolida issues das 3 revisões em dossier.verification_issues sem duplicação
        existing_signatures = {
            (iss.get("path"), iss.get("code")) for iss in dossier.verification_issues
        }
        for rev_issues in (
            integrity_review.issues,
            drafting_review.issues,
            analytical_review.issues,
        ):
            for iss in rev_issues:
                sig = (iss.get("path"), iss.get("code"))
                if sig not in existing_signatures:
                    existing_signatures.add(sig)
                    dossier.verification_issues.append(iss)

        has_failure = (
            structural_error
            or drafting_review.status == ReviewStatus.FAIL
            or analytical_review.status == ReviewStatus.FAIL
            or integrity_review.status == ReviewStatus.FAIL
        )

        if has_failure:
            dossier.status = DossierStatus.REVISION_REQUIRED
            overall_status = DossierStatus.REVISION_REQUIRED
            summary = "Dossiê requer revisão em uma ou mais frentes de auditoria especializada."
            logger.warning(
                f"Dossiê da análise {facts.analysis_id} requer revisão: "
                f"structural_error={structural_error}, "
                f"drafting={drafting_review.status}, "
                f"analytical={analytical_review.status}, "
                f"integrity={integrity_review.status}"
            )
        else:
            dossier.status = DossierStatus.VERIFIED
            overall_status = DossierStatus.VERIFIED
            summary = "Dossiê verificado e homologado com sucesso nas três frentes de revisão."

        actionable_feedback = list(analytical_review.actionable_recommendations)
        if integrity_review.status == ReviewStatus.FAIL:
            actionable_feedback.append(
                "Normalizador / Coleta: restaurar dados essenciais omitidos da fonte para o brief."
            )
        if drafting_review.status == ReviewStatus.FAIL:
            actionable_feedback.append(
                "Redator: corrigir inconsistências numéricas ou claims sem suporte identificadas."
            )

        dossier.three_fold_review = ThreeFoldDossierReview(
            data_integrity=integrity_review,
            senior_analytical=analytical_review,
            factual_drafting=drafting_review,
            overall_status=overall_status,
            summary=summary,
            actionable_feedback=actionable_feedback,
        )

        return dossier
