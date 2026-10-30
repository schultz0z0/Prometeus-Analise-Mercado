"""Testes para o runner de avaliação de inteligência de mercado (Fase 5 — Tarefa 5.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate_market_intelligence import (
    EvaluationMetricSummary,
    MarketIntelligenceEvaluator,
)


class TestEvaluatorRunner:
    """Suíte de testes para o script de avaliação offline e release de qualidade."""

    def test_evaluator_runs_offline_cleanly(self, tmp_path: Path) -> None:
        manifest_path = (
            Path(__file__).resolve().parent / "manifest.json"
        )
        assert manifest_path.exists(), "Manifesto de referência deve existir para teste."

        output_dir = tmp_path / "evaluation_test_output"
        evaluator = MarketIntelligenceEvaluator(
            manifest_path=manifest_path,
            output_dir=output_dir,
            mode="offline",
        )

        summary: EvaluationMetricSummary = evaluator.evaluate_offline()

        assert summary.total_examples == 10
        assert summary.passed is True
        assert summary.critical_fields_preservation_rate == 1.0
        assert summary.disallowed_claims_flagged == summary.disallowed_claims_evaluated
        assert summary.allowed_claims_accepted == summary.allowed_claims_evaluated

        # Verifica arquivos gerados
        summary_file = output_dir / "evaluation_summary.json"
        diag_file = output_dir / "evaluation_diagnostics.json"
        md_file = output_dir / "evaluation_report.md"

        assert summary_file.exists()
        assert diag_file.exists()
        assert md_file.exists()

        with open(summary_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["mode"] == "offline"
        assert data["passed"] is True
        assert data["critical_fields_preservation_rate"] == 1.0

    def test_evaluator_fails_on_missing_manifest(self, tmp_path: Path) -> None:
        evaluator = MarketIntelligenceEvaluator(
            manifest_path=tmp_path / "non_existent_manifest.json",
            output_dir=tmp_path / "output",
            mode="offline",
        )
        with pytest.raises(FileNotFoundError):
            evaluator.load_manifest()

