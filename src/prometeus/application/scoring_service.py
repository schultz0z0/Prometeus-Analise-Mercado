"""Serviço de aplicação para orquestração de scoring, quality gates e finalização da análise."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.evidence_features import EvidenceFeatureSet, VerifiedFeature
from prometeus.domain.analyses import Analysis, AnalysisStatus
from prometeus.domain.configuration import ConfigurationError, ScoringProfileConfig
from prometeus.domain.scoring.calculator import ScoringCalculator
from prometeus.domain.scoring.models import ScoringResult
from prometeus.domain.scoring.quality_gates import QualityGateEvaluator
from prometeus.infrastructure.db.models import ScoringResultModel

SCORING_PROFILES_DIR = Path("config/scoring")


class ScoringService:
    """Orquestra o carregamento de perfis, cálculo determinístico de scores e gates de release."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        profiles_dir: Path | str = SCORING_PROFILES_DIR,
        calculator: ScoringCalculator | None = None,
        gate_evaluator: QualityGateEvaluator | None = None,
    ) -> None:
        self.session = session
        self.profiles_dir = Path(profiles_dir)
        self.calculator = calculator or ScoringCalculator()
        self.gate_evaluator = gate_evaluator or QualityGateEvaluator()
        self._profiles_cache: dict[str, ScoringProfileConfig] = {}

    @staticmethod
    def _pillar_from_features(
        feature_set: EvidenceFeatureSet,
        mapping: dict[str, str],
        *,
        required_any: set[str],
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        provenance: dict[str, list[str]] = {}
        evidence_ids: list[str] = []

        for input_name, feature_name in mapping.items():
            feature: VerifiedFeature | None = feature_set.get(feature_name)
            if feature is None:
                continue
            values[input_name] = feature.value
            provenance[input_name] = list(feature.evidence_ids)
            for evidence_id in feature.evidence_ids:
                if evidence_id not in evidence_ids:
                    evidence_ids.append(evidence_id)

        is_present = any(name in values for name in required_any)
        return {
            **values,
            "is_present": is_present,
            "evidence_ids": evidence_ids,
            "feature_provenance": provenance,
            **(
                {}
                if is_present
                else {"missing_reason": "Nenhuma feature verificada mínima para o pilar"}
            ),
        }

    def build_pillar_inputs(
        self,
        feature_set: EvidenceFeatureSet,
        *,
        proposed_price_brl: float | None = None,
        proposed_price_source_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Mapeia somente features verificadas para o contrato do scoring.

        O preço proposto vem do entendimento imutável do curso e só é aceito com
        um identificador de proveniência desse snapshot.
        """
        pillars = {
            "internal_history": self._pillar_from_features(
                feature_set,
                {
                    "comparable_fit_score": "comparable_fit_score",
                    "conversion_rate": "conversion_rate",
                    "enrollments_count": "enrollments_count",
                },
                required_any={"comparable_fit_score"},
            ),
            "paid_competition": self._pillar_from_features(
                feature_set,
                {
                    "ad_count": "ad_count",
                    "competition_index": "competition_index",
                    "cpc_brl": "cpc_brl",
                },
                required_any={"ad_count", "competition_index"},
            ),
            "search_and_media": self._pillar_from_features(
                feature_set,
                {
                    "monthly_volume": "monthly_search_volume",
                    "growth_trend_pct": "growth_trend_pct",
                    "average_interest": "average_interest",
                },
                required_any={"monthly_volume", "average_interest"},
            ),
            "employability": self._pillar_from_features(
                feature_set,
                {
                    "open_jobs_count": "open_jobs_count",
                    "salary_median_brl": "salary_median_brl",
                },
                required_any={"open_jobs_count"},
            ),
            "syllabus_fit": self._pillar_from_features(
                feature_set,
                {
                    "syllabus_fit_score": "syllabus_fit_score",
                    "market_pain_points_covered_pct": "market_pain_points_covered_pct",
                },
                required_any={"syllabus_fit_score"},
            ),
            "pricing": self._pillar_from_features(
                feature_set,
                {"market_median_price_brl": "market_median_price_brl"},
                required_any={"market_median_price_brl"},
            ),
        }

        pricing = pillars["pricing"]
        if proposed_price_brl is None or proposed_price_source_id is None:
            pricing["is_present"] = False
            pricing["missing_reason"] = "Preço proposto sem valor ou proveniência verificável"
        else:
            pricing["proposed_price_brl"] = proposed_price_brl
            pricing["feature_provenance"]["proposed_price_brl"] = [proposed_price_source_id]
            pricing["evidence_ids"] = [
                proposed_price_source_id,
                *pricing["evidence_ids"],
            ]

        return pillars

    def get_profile(self, profile_id: str) -> ScoringProfileConfig:
        """Carrega e valida o perfil de scoring a partir de arquivo YAML."""
        if profile_id in self._profiles_cache:
            return self._profiles_cache[profile_id]

        file_path = self.profiles_dir / f"{profile_id}.yaml"
        if not file_path.exists():
            # Tenta com sufixo .example se arquivo limpo não existir
            alt_path = self.profiles_dir / f"{profile_id}.example.yaml"
            if alt_path.exists():
                file_path = alt_path
            else:
                raise ConfigurationError(
                    f"Perfil de scoring '{profile_id}' não encontrado em {self.profiles_dir}"
                )

        with file_path.open("r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        profile = ScoringProfileConfig.model_validate(raw_data)
        self._profiles_cache[profile_id] = profile
        return profile

    async def execute_scoring(
        self,
        pillar_inputs: dict[str, dict[str, Any]],
        analysis: Analysis | None = None,
        profile_id: str = "default-v1",
        correlation_id: str = "none",
        is_experimental: bool = True,
        finalize_analysis: bool = True,
    ) -> ScoringResult:
        """Executa o cálculo completo de viabilidade e gates (Etapas 10 e 11 do workflow)."""
        profile = self.get_profile(profile_id)

        # Etapa 10: Cálculo dos sub-scores e índices
        v_score, cov_score, conf_score, part_score, pillar_scores = self.calculator.calculate_all(
            profile=profile,
            pillar_inputs=pillar_inputs,
        )

        # Etapa 11: Avaliação dos Quality Gates e recomendação
        gate_eval = self.gate_evaluator.evaluate(
            viability_score=v_score,
            coverage_score=cov_score,
            confidence_score=conf_score,
            pillar_scores=pillar_scores,
            profile=profile,
        )

        analysis_id = analysis.id if analysis else "standalone-scoring"

        result = ScoringResult.create(
            analysis_id=analysis_id,
            profile_id=profile_id,
            viability_score=v_score,
            coverage_score=cov_score,
            confidence_score=conf_score,
            partial_score=part_score,
            recommendation=gate_eval.recommendation,
            pillar_scores=pillar_scores,
            gate_details=gate_eval,
            is_experimental=is_experimental,
        )

        # Transição de estado na análise (ADR-0005)
        if analysis is not None and finalize_analysis:
            if analysis.status == AnalysisStatus.QUEUED:
                analysis.start(
                    correlation_id=correlation_id, reason="Início do processamento de scoring"
                )

            analysis.complete(
                recommendation=gate_eval.recommendation,
                correlation_id=correlation_id,
                reason=f"Scoring concluído com recomendação {gate_eval.recommendation.value} (V={v_score:.1f}, Cov={cov_score:.1%})",
            )

        # Persistência relacional em PostgreSQL se session fornecida
        if self.session is not None and analysis is not None:
            model = (
                await self.session.execute(
                    select(ScoringResultModel).where(ScoringResultModel.analysis_id == analysis.id)
                )
            ).scalar_one_or_none()
            payload = {
                "profile_id": result.profile_id,
                "viability_score": result.viability_score,
                "coverage_score": result.coverage_score,
                "confidence_score": result.confidence_score,
                "partial_score": result.partial_score,
                "recommendation": result.recommendation.value,
                "is_experimental": result.is_experimental,
                "pillar_scores": {k: asdict(v) for k, v in result.pillar_scores.items()},
                "gate_details": result.gate_details.model_dump(),
            }
            if model is None:
                model = ScoringResultModel(
                    id=result.id,
                    analysis_id=analysis.id,
                    created_at=result.created_at,
                    **payload,
                )
                self.session.add(model)
            else:
                for key, value in payload.items():
                    setattr(model, key, value)
            await self.session.flush()

        return result
