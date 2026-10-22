"""Script de execução e validação de backtest temporal para o Gate D (Score ready).

Avalia o poder preditivo do motor determinístico de scoring frente ao dataset histórico
de lançamentos em `tests/evaluation/scoring/backtest_dataset.json`, comparando acurácia
contra baseline ingênuo, correlação com matrículas reais e detalhamento por modalidade.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prometeus.application.scoring_service import ScoringService
from prometeus.domain.analyses import AnalysisRecommendation

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("run_backtest")


def calculate_pearson_correlation(x: list[float], y: list[float]) -> float:
    """Calcula coeficiente de correlação linear de Pearson de forma determinística."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denom_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    denominator = (denom_x * denom_y) ** 0.5
    if denominator <= 0:
        return 0.0

    return round(numerator / denominator, 4)


def map_recommendation_to_outcome(
    rec: AnalysisRecommendation,
    v_score: float,
    th_approved: float = 75.0,
    th_adjustment: float = 60.0,
) -> str:
    """Mapeia a recomendação para a classe de desfecho esperada com resolução direcional."""
    if rec == AnalysisRecommendation.APPROVED:
        return "SUCCESS"
    elif rec == AnalysisRecommendation.APPROVED_WITH_ADJUSTMENTS:
        return "MARGINAL"
    elif rec == AnalysisRecommendation.HIGH_RISK:
        return "FAILED"
    elif rec == AnalysisRecommendation.REQUIRES_HUMAN_REVIEW:
        # Em revisão de fronteira, resolve para o desfecho direcional do score de viabilidade
        if v_score >= th_approved:
            return "SUCCESS"
        elif v_score >= th_adjustment:
            return "MARGINAL"
        else:
            return "FAILED"
    return "UNCERTAIN"


def run_backtest_evaluation(
    profile_id: str,
    dataset_path: Path,
    report_path: Path,
) -> int:
    if not dataset_path.exists():
        logger.error(f"Dataset de backtest não encontrado em {dataset_path}")
        return 1

    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])
    if not samples:
        logger.error("Nenhuma amostra encontrada no dataset de backtest")
        return 1

    scoring_service = ScoringService()
    profile = scoring_service.get_profile(profile_id)

    logger.info(
        f"Executando backtest com perfil '{profile_id}' em {len(samples)} amostras históricas..."
    )

    correct_predictions = 0
    total_samples = len(samples)
    scores: list[float] = []
    real_enrollments: list[float] = []

    # Estatísticas por modalidade
    by_modality: dict[str, dict[str, int]] = {}

    course_results: list[dict[str, Any]] = []

    for item in samples:
        course_id = item["course_id"]
        course_name = item["course_name"]
        modality = item.get("modality", "EAD")
        actual_outcome = item["actual_outcome"]
        actual_enr = float(item.get("actual_enrollments", 0))

        v_score, cov_score, conf_score, part_score, pillar_scores = (
            scoring_service.calculator.calculate_all(profile, item["pillar_inputs"])
        )

        gate_eval = scoring_service.gate_evaluator.evaluate(
            viability_score=v_score,
            coverage_score=cov_score,
            confidence_score=conf_score,
            pillar_scores=pillar_scores,
            profile=profile,
        )

        predicted_outcome = map_recommendation_to_outcome(
            rec=gate_eval.recommendation,
            v_score=v_score,
            th_approved=profile.thresholds.approved,
            th_adjustment=profile.thresholds.approved_with_adjustments,
        )
        is_correct = predicted_outcome == actual_outcome
        if is_correct:
            correct_predictions += 1

        scores.append(v_score)
        real_enrollments.append(actual_enr)

        if modality not in by_modality:
            by_modality[modality] = {"total": 0, "correct": 0}
        by_modality[modality]["total"] += 1
        if is_correct:
            by_modality[modality]["correct"] += 1

        course_results.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "modality": modality,
                "actual_outcome": actual_outcome,
                "predicted_outcome": predicted_outcome,
                "recommendation": gate_eval.recommendation.value,
                "viability_score": v_score,
                "coverage_score": cov_score,
                "is_correct": is_correct,
                "reasons": gate_eval.reasons,
            }
        )

    model_accuracy = round(correct_predictions / total_samples, 4)

    # Baseline ingênuo: sempre prever a classe majoritária
    outcome_counts: dict[str, int] = {}
    for item in samples:
        outc = item["actual_outcome"]
        outcome_counts[outc] = outcome_counts.get(outc, 0) + 1
    majority_count = max(outcome_counts.values()) if outcome_counts else 0
    naive_baseline_accuracy = round(majority_count / total_samples, 4)

    # Correlação Pearson Viability x Matrículas Reais
    pearson_corr = calculate_pearson_correlation(scores, real_enrollments)

    # Critérios do Gate D
    baseline_beaten = model_accuracy >= (naive_baseline_accuracy + 0.15)
    strong_correlation = pearson_corr >= 0.85
    gate_d_approved = baseline_beaten and strong_correlation and model_accuracy >= 0.80

    modality_breakdown = {
        mod: {
            "total": stats["total"],
            "accuracy": round(stats["correct"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
        }
        for mod, stats in by_modality.items()
    }

    final_report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "gate": "Gate D — Score ready",
        "profile_id": profile_id,
        "sample_count": total_samples,
        "metrics": {
            "model_accuracy": model_accuracy,
            "naive_baseline_accuracy": naive_baseline_accuracy,
            "baseline_improvement": round(model_accuracy - naive_baseline_accuracy, 4),
            "pearson_correlation_with_enrollments": pearson_corr,
        },
        "modality_breakdown": modality_breakdown,
        "criteria": {
            "baseline_beaten": baseline_beaten,
            "strong_correlation": strong_correlation,
            "accuracy_above_80pct": model_accuracy >= 0.80,
        },
        "gate_status": "APPROVED" if gate_d_approved else "REJECTED",
        "evaluations": course_results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("PROMETEUS - RELATORIO DE BACKTEST TEMPORAL E CALIBRACAO (GATE D)")
    print("=" * 80)
    print(f"Perfil de Scoring Avaliado : {profile_id}")
    print(f"Total de Cursos Avaliados  : {total_samples}")
    print(f"Acuracia do Modelo         : {model_accuracy:.2%}")
    print(f"Acuracia do Baseline Naive : {naive_baseline_accuracy:.2%}")
    print(f"Ganho sobre Baseline       : +{(model_accuracy - naive_baseline_accuracy):.2%}")
    print(f"Correlacao com Matriculas  : {pearson_corr:.4f} (Pearson)")
    print("-" * 80)
    print("Desempenho por Modalidade:")
    for mod, stats in modality_breakdown.items():
        print(f"  - {mod:<12}: {stats['accuracy']:.1%} ({stats['total']} cursos)")
    print("=" * 80)
    print(f"Relatorio gerado em: {report_path}")
    print(f"Status do Gate D: {'APROVADO (10/10)' if gate_d_approved else 'REPROVADO'}")
    print("=" * 80 + "\n")

    return 0 if gate_d_approved else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Execução de backtest temporal para o Gate D")
    parser.add_argument(
        "--profile",
        type=str,
        default="default-v1",
        help="ID do perfil de scoring a ser avaliado",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/evaluation/scoring/backtest_dataset.json"),
        help="Caminho do dataset histórico de backtest",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/backtest-v1.json"),
        help="Caminho do relatório JSON de saída",
    )
    args = parser.parse_args()

    exit_code = run_backtest_evaluation(args.profile, args.dataset, args.report)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
