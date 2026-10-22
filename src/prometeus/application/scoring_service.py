"""Serviço de aplicação para orquestração de scoring, quality gates e finalização da análise."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

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
        if analysis is not None:
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
            model = ScoringResultModel(
                id=result.id,
                analysis_id=analysis.id,
                profile_id=result.profile_id,
                viability_score=result.viability_score,
                coverage_score=result.coverage_score,
                confidence_score=result.confidence_score,
                partial_score=result.partial_score,
                recommendation=result.recommendation.value,
                is_experimental=result.is_experimental,
                pillar_scores={k: asdict(v) for k, v in result.pillar_scores.items()},
                gate_details=result.gate_details.model_dump(),
                created_at=result.created_at,
            )
            self.session.add(model)
            await self.session.flush()

        return result
