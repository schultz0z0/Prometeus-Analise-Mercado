"""Serviço de aplicação para geração, julgamento e seleção de termos de busca (Etapa 04).

Implementa a composição entre TOOL-01 (candidatos via LLM), TOOL-02 (relevância via JEV)
e seleção determinística por regra em código (KeywordSet).
"""

from __future__ import annotations

import logging
from typing import Any

from prometeus.application.decision_service import DecisionService
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.domain.ports.market_sources import (
    KeywordCandidate,
    KeywordCategory,
    KeywordSet,
)

logger = logging.getLogger(__name__)


class KeywordPipeline:
    """Orquestra a geração, filtragem semântica e montagem do KeywordSet canônico."""

    def __init__(
        self,
        generative_model: GenerativeModelPort,
        decision_service: DecisionService,
        max_primary: int = 5,
        max_secondary: int = 10,
    ) -> None:
        self.generative_model = generative_model
        self.decision_service = decision_service
        self.max_primary = max_primary
        self.max_secondary = max_secondary

    async def build_keyword_set(
        self,
        course_title: str,
        description: str,
        target_audience: str,
        correlation_id: str = "none",
        candidate_count: int = 15,
    ) -> KeywordSet:
        """Executa o pipeline completo da Etapa 04 do workflow."""
        # TOOL-01: Geração de candidatos via LLM generativa
        candidates_raw = await self.generative_model.generate_keyword_candidates(
            course_title=course_title,
            description=description,
            target_audience=target_audience,
            max_candidates=candidate_count,
        )

        # Higienização inicial de termos
        cleaned_terms: list[str] = []
        seen = set()
        for term in candidates_raw:
            norm = term.strip().lower()
            if norm and norm not in seen:
                seen.add(norm)
                cleaned_terms.append(norm)

        # TOOL-02: Julgamento atômico de relevância de cada termo no JEV
        evaluated_candidates: list[KeywordCandidate] = []
        primary_list: list[str] = []
        secondary_list: list[str] = []
        negative_list: list[str] = []

        for term in cleaned_terms:
            context: dict[str, Any] = {
                "course_title": course_title,
                "search_term": term,
            }

            try:
                jev_res = await self.decision_service.execute_judgment(
                    pack_id="keywords-relevance-v1",
                    context=context,
                    correlation_id=correlation_id,
                )
                relevance = jev_res.selected_choice or "IRRELEVANT"
                confidence = jev_res.confidence
            except Exception as exc:
                logger.warning(f"Falha avaliando relevância do termo '{term}' no JEV: {exc}")
                relevance = "IRRELEVANT"
                confidence = 0.0

            # Regra em código para classificação e categorização
            if relevance == "HIGH_RELEVANCE":
                if len(primary_list) < self.max_primary:
                    category = KeywordCategory.PRIMARY
                    primary_list.append(term)
                elif len(secondary_list) < self.max_secondary:
                    category = KeywordCategory.SECONDARY
                    secondary_list.append(term)
                else:
                    category = KeywordCategory.SECONDARY
            elif relevance == "MEDIUM_RELEVANCE":
                if len(secondary_list) < self.max_secondary:
                    category = KeywordCategory.SECONDARY
                    secondary_list.append(term)
                else:
                    category = KeywordCategory.SECONDARY
            else:
                # IRRELEVANT é marcado como negativa para descarte em campanhas
                category = KeywordCategory.NEGATIVE
                negative_list.append(term)

            candidate = KeywordCandidate(
                term=term,
                relevance=relevance,
                confidence=confidence,
                category=category,
                notes="Revisão necessária" if confidence < 0.70 else "",
            )
            evaluated_candidates.append(candidate)

        return KeywordSet(
            primary_keywords=primary_list,
            secondary_keywords=secondary_list,
            negative_keywords=negative_list,
            evaluated_candidates=evaluated_candidates,
        )
