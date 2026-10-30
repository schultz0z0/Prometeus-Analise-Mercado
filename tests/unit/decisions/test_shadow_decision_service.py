"""Testes unitários para execução em Shadow Mode e isolamento de falhas (Fase 6)."""

from __future__ import annotations

from typing import Any

import pytest

from prometeus.application.decision_service import DecisionService
from prometeus.application.shadow_decision_service import ShadowDecisionService
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
    ModelIdentity,
)
from prometeus.domain.shadow_decisions import DivergenceCategory


class MockPrimaryDecisionModel(DecisionModelPort):
    def __init__(self, choice: str = "DIRECT", confidence: float = 0.9) -> None:
        self.choice = choice
        self.confidence = confidence

    def model_identity(self) -> ModelIdentity:
        return ModelIdentity(provider="openai", model="gpt-4o-mini", mode="llm")

    def component_versions(self, pack_id: str, context: dict[str, Any]) -> dict[str, str]:
        return {"adapter": "v1"}

    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=self.choice,
            confidence=self.confidence,
            evidence_ids=evidence_ids,
        )

    async def execute_score(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=80.0,
            confidence=self.confidence,
            evidence_ids=evidence_ids,
        )


class MockShadowDecisionModel(DecisionModelPort):
    def __init__(
        self,
        choice: str = "DIRECT",
        confidence: float = 0.9,
        should_fail: bool = False,
        is_noul: bool = False,
    ) -> None:
        self.choice = choice
        self.confidence = confidence
        self.should_fail = should_fail
        self.is_noul = is_noul

    def model_identity(self) -> ModelIdentity:
        return ModelIdentity(provider="typesafe_jev", model="jev-2026.1", mode="jev")

    def component_versions(self, pack_id: str, context: dict[str, Any]) -> dict[str, str]:
        return {"client": "jev-v1"}

    async def execute_choice(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        if self.should_fail:
            raise ConnectionError("Falha de rede simulada com servidor JEV")
        if self.is_noul:
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason="Evidência inconclusiva no shadow",
                evidence_ids=evidence_ids,
            )
        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=self.choice,
            confidence=self.confidence,
            evidence_ids=evidence_ids,
        )

    async def execute_score(
        self, pack: DecisionPack, context: dict[str, Any], evidence_ids: list[str] | None = None
    ) -> DecisionResult:
        if self.should_fail:
            raise TimeoutError("Timeout simulado no JEV")
        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=85.0,
            confidence=self.confidence,
            evidence_ids=evidence_ids,
        )


class TestShadowDecisionService:
    """Suíte de testes para ShadowDecisionService."""

    @pytest.mark.asyncio
    async def test_shadow_execution_concordant(self, tmp_path: Any) -> None:
        """Quando primário e shadow concordam, registra CONCORDANT e retorna primário inalterado."""
        primary_model = MockPrimaryDecisionModel(choice="RELEVANT", confidence=0.92)
        shadow_model = MockShadowDecisionModel(choice="RELEVANT", confidence=0.90)

        # Configura pack real
        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        pack_file = packs_dir / "test-pack.yaml"
        pack_file.write_text(
            """
pack_id: test-pack
version: "1.0.0"
decision_type: CHOICE
question: "O item é relevante?"
options: ["RELEVANT", "IRRELEVANT"]
rubric: {}
notes: []
""",
            encoding="utf-8",
        )

        primary_service = DecisionService(decision_model=primary_model, packs_dir=packs_dir)
        shadow_service = ShadowDecisionService(
            primary_service=primary_service,
            shadow_model=shadow_model,
            enabled=True,
        )

        result = await shadow_service.execute_judgment(
            pack_id="test-pack",
            context={"title": "Curso relevante"},
            evidence_ids=["ev-01"],
        )

        # 1. O resultado da produção é estritamente o do modelo primário
        assert result.selected_choice == "RELEVANT"
        assert result.confidence == 0.92

        # 2. Shadow gerou registro de comparação
        assert len(shadow_service.comparison_records) == 1
        record = shadow_service.comparison_records[0]
        assert record.is_concordant is True
        assert record.divergence_category == DivergenceCategory.CONCORDANT
        assert record.primary_choice == "RELEVANT"
        assert record.shadow_choice == "RELEVANT"
        assert record.primary_model == "gpt-4o-mini"
        assert record.shadow_model == "jev-2026.1"

    @pytest.mark.asyncio
    async def test_shadow_detects_choice_divergence_without_altering_production(
        self, tmp_path: Any
    ) -> None:
        """Quando shadow diverge na escolha, registra CHOICE_DIVERGENCE sem afetar produção."""
        primary_model = MockPrimaryDecisionModel(choice="RELEVANT", confidence=0.88)
        shadow_model = MockShadowDecisionModel(choice="IRRELEVANT", confidence=0.85)

        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        pack_file = packs_dir / "test-pack.yaml"
        pack_file.write_text(
            """
pack_id: test-pack
version: "1.0.0"
decision_type: CHOICE
question: "O item é relevante?"
options: ["RELEVANT", "IRRELEVANT"]
rubric: {}
notes: []
""",
            encoding="utf-8",
        )

        primary_service = DecisionService(decision_model=primary_model, packs_dir=packs_dir)
        shadow_service = ShadowDecisionService(
            primary_service=primary_service,
            shadow_model=shadow_model,
            enabled=True,
        )

        result = await shadow_service.execute_judgment(
            pack_id="test-pack",
            context={"title": "Curso ambíguo"},
        )

        # Produção permanece inalterada (RELEVANT)
        assert result.selected_choice == "RELEVANT"

        # Shadow registrou divergência
        assert len(shadow_service.comparison_records) == 1
        record = shadow_service.comparison_records[0]
        assert record.is_concordant is False
        assert record.divergence_category == DivergenceCategory.CHOICE_DIVERGENCE
        assert record.primary_choice == "RELEVANT"
        assert record.shadow_choice == "IRRELEVANT"

    @pytest.mark.asyncio
    async def test_shadow_detects_abstention_divergence(self, tmp_path: Any) -> None:
        """Quando shadow abstém (NOUL), registra ABSTENTION_DIVERGENCE."""
        primary_model = MockPrimaryDecisionModel(choice="RELEVANT", confidence=0.85)
        shadow_model = MockShadowDecisionModel(is_noul=True)

        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        pack_file = packs_dir / "test-pack.yaml"
        pack_file.write_text(
            """
pack_id: test-pack
version: "1.0.0"
decision_type: CHOICE
question: "O item é relevante?"
options: ["RELEVANT", "IRRELEVANT"]
rubric: {}
notes: []
""",
            encoding="utf-8",
        )

        primary_service = DecisionService(decision_model=primary_model, packs_dir=packs_dir)
        shadow_service = ShadowDecisionService(
            primary_service=primary_service,
            shadow_model=shadow_model,
            enabled=True,
        )

        result = await shadow_service.execute_judgment(
            pack_id="test-pack",
            context={"title": "Curso"},
        )

        assert result.selected_choice == "RELEVANT"
        record = shadow_service.comparison_records[0]
        assert record.is_concordant is False
        assert record.divergence_category == DivergenceCategory.ABSTENTION_DIVERGENCE
        assert record.shadow_is_noul is True

    @pytest.mark.asyncio
    async def test_shadow_failure_does_not_break_primary(self, tmp_path: Any) -> None:
        """Falha de rede ou timeout no JEV shadow JAMAIS quebra a execução primária."""
        primary_model = MockPrimaryDecisionModel(choice="RELEVANT", confidence=0.95)
        shadow_model = MockShadowDecisionModel(should_fail=True)

        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        pack_file = packs_dir / "test-pack.yaml"
        pack_file.write_text(
            """
pack_id: test-pack
version: "1.0.0"
decision_type: CHOICE
question: "O item é relevante?"
options: ["RELEVANT", "IRRELEVANT"]
rubric: {}
notes: []
""",
            encoding="utf-8",
        )

        primary_service = DecisionService(decision_model=primary_model, packs_dir=packs_dir)
        shadow_service = ShadowDecisionService(
            primary_service=primary_service,
            shadow_model=shadow_model,
            enabled=True,
        )

        # Não deve lançar exceção!
        result = await shadow_service.execute_judgment(
            pack_id="test-pack",
            context={"title": "Curso seguro"},
        )

        assert result.selected_choice == "RELEVANT"
        record = shadow_service.comparison_records[0]
        assert record.is_concordant is False
        assert record.divergence_category == DivergenceCategory.SHADOW_ERROR
        assert "Falha de rede" in str(record.divergence_notes)
