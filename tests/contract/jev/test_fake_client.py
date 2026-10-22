"""Testes de contrato para FakeDecisionClient."""

import pytest

from prometeus.domain.ports.decision_model import (
    DecisionPack,
    DecisionType,
)
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient


@pytest.fixture
def choice_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="readiness-v1",
        decision_type=DecisionType.CHOICE,
        question="Curso pronto?",
        options=["READY", "NEEDS_CLARIFICATION", "INSUFFICIENT_INFORMATION"],
        review_threshold=0.75,
    )


@pytest.fixture
def score_pack() -> DecisionPack:
    return DecisionPack(
        pack_id="syllabus-fit-v1",
        decision_type=DecisionType.SCORE,
        question="Nota de adequação?",
        min_score=0.0,
        max_score=100.0,
        review_threshold=0.80,
    )


@pytest.mark.asyncio
async def test_fake_client_choice_default(choice_pack: DecisionPack) -> None:
    client = FakeDecisionClient(default_confidence=0.88)
    res = await client.execute_choice(choice_pack, context={"title": "MBA em Riscos"})

    assert res.pack_id == "readiness-v1"
    assert res.decision_type == DecisionType.CHOICE
    assert res.selected_choice == "READY"
    assert res.confidence == 0.88
    assert res.requires_human_review is False
    assert res.is_noul is False


@pytest.mark.asyncio
async def test_fake_client_choice_canned(choice_pack: DecisionPack) -> None:
    client = FakeDecisionClient(canned_choices={"readiness-v1": "NEEDS_CLARIFICATION"})
    res = await client.execute_choice(choice_pack, context={})

    assert res.selected_choice == "NEEDS_CLARIFICATION"


@pytest.mark.asyncio
async def test_fake_client_score_default(score_pack: DecisionPack) -> None:
    client = FakeDecisionClient(default_confidence=0.85)
    res = await client.execute_score(score_pack, context={})

    assert res.pack_id == "syllabus-fit-v1"
    assert res.decision_type == DecisionType.SCORE
    assert res.score_value == 50.0  # (0 + 100) / 2
    assert res.confidence == 0.85
    assert res.requires_human_review is False


@pytest.mark.asyncio
async def test_fake_client_score_canned(score_pack: DecisionPack) -> None:
    client = FakeDecisionClient(canned_scores={"syllabus-fit-v1": 92.5})
    res = await client.execute_score(score_pack, context={})

    assert res.score_value == 92.5


@pytest.mark.asyncio
async def test_fake_client_simulate_noul(choice_pack: DecisionPack) -> None:
    client = FakeDecisionClient(simulate_noul=True)
    res = await client.execute_choice(choice_pack, context={})

    assert res.is_noul is True
    assert res.decision_type == DecisionType.NOUL
    assert res.requires_human_review is True
    assert res.confidence == 0.0


@pytest.mark.asyncio
async def test_fake_client_simulate_unavailable(choice_pack: DecisionPack) -> None:
    client = FakeDecisionClient(simulate_unavailable=True)

    with pytest.raises(ConnectionError, match="TypeSafe JEV service indisponível"):
        await client.execute_choice(choice_pack, context={})
