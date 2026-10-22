"""Testes unitários para portas e modelos de decisão (DecisionResult, DecisionPack, DecisionType)."""

from prometeus.domain.ports.decision_model import (
    DecisionPack,
    DecisionResult,
    DecisionType,
)


def test_decision_type_values() -> None:
    assert DecisionType.CHOICE == "CHOICE"
    assert DecisionType.SCORE == "SCORE"
    assert DecisionType.NOUL == "NOUL"


def test_decision_result_choice_above_threshold() -> None:
    result = DecisionResult.choice(
        pack_id="taxonomy-v1",
        selected="SEGUROS_E_RESSEGUROS",
        confidence=0.88456,
        distribution={"SEGUROS_E_RESSEGUROS": 0.88456, "OUTROS": 0.11544},
        review_threshold=0.80,
        evidence_ids=["ev-1", "ev-2"],
        model_version="jev-2026.1",
    )
    assert result.pack_id == "taxonomy-v1"
    assert result.decision_type == DecisionType.CHOICE
    assert result.selected_choice == "SEGUROS_E_RESSEGUROS"
    assert result.confidence == 0.8846
    assert result.is_noul is False
    assert result.score_value is None
    assert result.requires_human_review is False
    assert result.evidence_ids == ["ev-1", "ev-2"]
    assert result.model_version == "jev-2026.1"


def test_decision_result_choice_below_threshold_triggers_review() -> None:
    result = DecisionResult.choice(
        pack_id="readiness-v1",
        selected="NEEDS_CLARIFICATION",
        confidence=0.65,
        review_threshold=0.75,
    )
    assert result.decision_type == DecisionType.CHOICE
    assert result.requires_human_review is True


def test_decision_result_score_above_threshold() -> None:
    result = DecisionResult.score(
        pack_id="syllabus-fit-v1",
        value=87.555,
        confidence=0.92,
        review_threshold=0.80,
    )
    assert result.pack_id == "syllabus-fit-v1"
    assert result.decision_type == DecisionType.SCORE
    assert result.score_value == 87.56
    assert result.confidence == 0.92
    assert result.is_noul is False
    assert result.selected_choice is None
    assert result.distribution == {}
    assert result.requires_human_review is False


def test_decision_result_score_below_threshold_triggers_review() -> None:
    result = DecisionResult.score(
        pack_id="comparable-fit-v1",
        value=65.0,
        confidence=0.70,
        review_threshold=0.75,
    )
    assert result.requires_human_review is True


def test_decision_result_noul_always_requires_human_review() -> None:
    result = DecisionResult.noul(
        pack_id="evidence-support-v1",
        reason="Evidência ausente no documento de referência",
        evidence_ids=["missing-doc-1"],
        model_version="jev-2026.1",
    )
    assert result.pack_id == "evidence-support-v1"
    assert result.decision_type == DecisionType.NOUL
    assert result.is_noul is True
    assert result.confidence == 0.0
    assert result.selected_choice is None
    assert result.score_value is None
    assert result.requires_human_review is True
    assert result.evidence_ids == ["missing-doc-1"]


def test_decision_pack_instantiation() -> None:
    pack = DecisionPack(
        pack_id="test-pack-v1",
        version="1.0.0",
        decision_type=DecisionType.CHOICE,
        question="Teste de viabilidade?",
        options=["SIM", "NAO"],
        review_threshold=0.85,
    )
    assert pack.pack_id == "test-pack-v1"
    assert pack.decision_type == DecisionType.CHOICE
    assert pack.review_threshold == 0.85
    assert pack.options == ["SIM", "NAO"]
