"""Serviço de aplicação para orquestração de julgamentos JEV e governança de decision packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.analyses import Analysis
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
    DecisionType,
)
from prometeus.infrastructure.db.models import DecisionResultModel
from prometeus.infrastructure.jev.client import (
    JEVError,
    JEVServiceUnavailableError,
)

DECISION_PACKS_DIR = Path("config/decision-packs")


class DecisionService:
    """Orquestra a carga de decision packs, execução de julgamentos e persistência."""

    def __init__(
        self,
        decision_model: DecisionModelPort,
        session: AsyncSession | None = None,
        packs_dir: Path | str = DECISION_PACKS_DIR,
    ) -> None:
        self.decision_model = decision_model
        self.session = session
        self.packs_dir = Path(packs_dir)
        self._packs_cache: dict[str, DecisionPack] = {}

    def get_pack(self, pack_id: str) -> DecisionPack:
        """Carrega e valida o decision pack a partir do arquivo YAML."""
        if pack_id in self._packs_cache:
            return self._packs_cache[pack_id]

        file_path = self.packs_dir / f"{pack_id}.yaml"
        if not file_path.exists():
            # Tenta sem extensão se pack_id já contiver sufixo
            alt_path = self.packs_dir / pack_id
            if alt_path.exists():
                file_path = alt_path
            else:
                raise FileNotFoundError(
                    f"Decision pack '{pack_id}' não encontrado em {self.packs_dir}"
                )

        with file_path.open("r", encoding="utf-8") as f:
            raw_data: Any = yaml.safe_load(f)

        pack = DecisionPack.model_validate(raw_data)
        self._packs_cache[pack_id] = pack
        return pack

    async def execute_judgment(
        self,
        pack_id: str,
        context: dict[str, Any],
        analysis: Analysis | None = None,
        correlation_id: str = "none",
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        """Executa um julgamento atômico (Choice/Score).

        Se o JEV estiver indisponível, aciona o estado BLOCKED na análise (ADR-0003).
        """
        pack = self.get_pack(pack_id)

        try:
            if pack.decision_type == DecisionType.CHOICE:
                result = await self.decision_model.execute_choice(
                    pack=pack,
                    context=context,
                    evidence_ids=evidence_ids,
                )
            elif pack.decision_type == DecisionType.SCORE:
                result = await self.decision_model.execute_score(
                    pack=pack,
                    context=context,
                    evidence_ids=evidence_ids,
                )
            else:
                result = DecisionResult.noul(
                    pack_id=pack_id,
                    reason=f"Tipo de decisão não suportado: {pack.decision_type}",
                    evidence_ids=evidence_ids,
                )
        except (JEVServiceUnavailableError, ConnectionError, TimeoutError) as exc:
            # ADR-0003: Indisponibilidade gera BLOCKED; nenhuma LLM substitui silenciosamente o JEV
            if analysis is not None:
                analysis.block(
                    correlation_id=correlation_id,
                    reason=f"JEV indisponível para o decision pack '{pack_id}': {exc}",
                )
            raise JEVServiceUnavailableError(
                f"Falha de disponibilidade do JEV no pack '{pack_id}': {exc}"
            ) from exc
        except Exception as exc:
            raise JEVError(f"Erro inesperado no julgamento do pack '{pack_id}': {exc}") from exc

        # Persistência relacional em PostgreSQL caso session esteja configurada
        if self.session is not None and analysis is not None:
            model = DecisionResultModel(
                id=result.id,
                analysis_id=analysis.id,
                pack_id=result.pack_id,
                decision_type=result.decision_type.value,
                confidence=result.confidence,
                is_noul=result.is_noul,
                selected_choice=result.selected_choice,
                distribution=result.distribution,
                score_value=result.score_value,
                requires_human_review=result.requires_human_review,
                evidence_ids=result.evidence_ids,
                model_version=result.model_version,
                created_at=result.created_at,
            )
            self.session.add(model)
            await self.session.flush()

        return result
