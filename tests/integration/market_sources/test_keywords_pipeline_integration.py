"""Testes de integração para o pipeline de keywords (TOOL-01 + TOOL-02 + Seleção em código)."""

import pytest

from prometeus.application.decision_service import DecisionService
from prometeus.application.keywords import KeywordPipeline
from prometeus.domain.ports.market_sources import KeywordCategory
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient
from prometeus.infrastructure.llm.fake import FakeGenerativeModel


@pytest.mark.asyncio
async def test_keyword_pipeline_execution_and_categorization() -> None:
    # 1. Configura modelo generativo fake com 5 termos candidatos
    llm = FakeGenerativeModel(
        canned_keywords=[
            "mba em subscrição de riscos",
            "pos graduacao em resseguros ens",
            "como funciona subscritor",
            "comprar seguro auto barato",
            "tabela fipe carros 2026",
        ]
    )

    # 2. Configura fake JEV para classificar termos
    # Sobrescreve julgamentos para os termos específicos
    class MockDecisionClient(FakeDecisionClient):
        async def execute_choice(self, pack, context, evidence_ids=None):
            term = context.get("search_term", "")
            if "subscrição" in term or "resseguros" in term:
                choice = "HIGH_RELEVANCE"
                conf = 0.95
            elif "como funciona" in term:
                choice = "MEDIUM_RELEVANCE"
                conf = 0.85
            else:
                choice = "IRRELEVANT"
                conf = 0.92

            from prometeus.domain.ports.decision_model import DecisionResult

            return DecisionResult.choice(
                pack_id=pack.pack_id,
                selected=choice,
                confidence=conf,
                review_threshold=pack.review_threshold,
            )

    decision_service = DecisionService(decision_model=MockDecisionClient())

    # 3. Executa pipeline
    pipeline = KeywordPipeline(
        generative_model=llm,
        decision_service=decision_service,
        max_primary=2,
        max_secondary=5,
    )

    keyword_set = await pipeline.build_keyword_set(
        course_title="MBA em Subscrição e Resseguros",
        description="Capacitação em análise de grandes riscos",
        target_audience="Subscritores e analistas",
        correlation_id="corr-kw-1",
    )

    # 4. Asserções sobre a categorização determinística
    assert len(keyword_set.primary_keywords) == 2
    assert "mba em subscrição de riscos" in keyword_set.primary_keywords
    assert "pos graduacao em resseguros ens" in keyword_set.primary_keywords

    assert len(keyword_set.secondary_keywords) == 1
    assert "como funciona subscritor" in keyword_set.secondary_keywords

    assert len(keyword_set.negative_keywords) == 2
    assert "comprar seguro auto barato" in keyword_set.negative_keywords
    assert "tabela fipe carros 2026" in keyword_set.negative_keywords

    # Valida candidatos avaliados
    assert len(keyword_set.evaluated_candidates) == 5
    evaluated_terms = {c.term: c.category for c in keyword_set.evaluated_candidates}
    assert evaluated_terms["mba em subscrição de riscos"] == KeywordCategory.PRIMARY
    assert evaluated_terms["comprar seguro auto barato"] == KeywordCategory.NEGATIVE
