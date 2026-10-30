"""Serviço de aplicação para orquestração de julgamentos JEV e governança de decision packs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.analyses import Analysis
from prometeus.domain.execution_envelope import (
    ExecutionEnvelope,
    ExecutionOutcome,
    MeasuredCost,
    canonical_hash,
    capture_provider_calls,
    compute_cache_key,
)
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
    DecisionType,
)
from prometeus.infrastructure.db.models import DecisionResultModel, ExecutionEnvelopeModel
from prometeus.infrastructure.jev.client import (
    JEVError,
    JEVServiceUnavailableError,
)

DECISION_PACKS_DIR = Path("config/decision-packs")


class DecisionService:
    """Orquestra a carga de decision packs, execução de julgamentos, envelopes e persistência."""

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
        self.envelopes: list[ExecutionEnvelope] = []
        self._attempts_by_key: dict[str, int] = {}

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

    def _build_component_versions(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        explicit_versions: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        versions: dict[str, str] = {
            "pack": f"{pack.pack_id}@{pack.version}",
        }
        adapter_versions = self.decision_model.component_versions(pack.pack_id, context)
        versions.update(adapter_versions)
        if explicit_versions:
            versions.update(explicit_versions)
        return versions

    def cache_key_for(
        self,
        pack_id: str,
        context: dict[str, Any],
        component_versions: Mapping[str, str] | None = None,
    ) -> str:
        pack = self.get_pack(pack_id)
        versions = self._build_component_versions(pack, context, component_versions)
        identity = self.decision_model.model_identity()
        input_hash = canonical_hash({"pack_id": pack_id, "context": context})
        return compute_cache_key(
            stage=pack_id,
            operation=pack_id,
            input_hash=input_hash,
            component_versions=versions,
            model=identity.model,
            mode=identity.mode,
        )

    async def _persist_envelope(self, envelope: ExecutionEnvelope) -> None:
        self.envelopes.append(envelope)
        if self.session is not None:
            env_model = ExecutionEnvelopeModel(
                id=envelope.id,
                analysis_id=envelope.analysis_id,
                tenant_id=envelope.tenant_id,
                stage=envelope.stage,
                operation=envelope.operation,
                attempt=envelope.attempt,
                input_hash=envelope.input_hash,
                cache_key=envelope.cache_key,
                source_ids=list(envelope.source_ids),
                component_versions=envelope.component_versions,
                provider=envelope.provider,
                configured_model=envelope.configured_model,
                model=envelope.model,
                mode=envelope.mode,
                outcome=envelope.outcome.value,
                started_at=envelope.started_at,
                finished_at=envelope.finished_at,
                duration_ms=envelope.duration_ms,
                usage=envelope.usage.to_dict() if envelope.usage else None,
                cost_status=envelope.cost.status.value,
                cost_usd=float(envelope.cost.amount_usd)
                if envelope.cost.amount_usd is not None
                else None,
                cost_source=envelope.cost.source,
                provider_attempts=envelope.provider_attempts,
                decision_id=envelope.decision_id,
                result_kind=envelope.result_kind,
                error_code=envelope.error_code,
                error_detail=envelope.error_detail,
                schema_version=envelope.schema_version,
                created_at=envelope.created_at,
            )
            self.session.add(env_model)
            await self.session.flush()

    async def execute_judgment(
        self,
        pack_id: str,
        context: dict[str, Any],
        analysis: Analysis | None = None,
        correlation_id: str = "none",
        evidence_ids: list[str] | None = None,
        component_versions: Mapping[str, str] | None = None,
        stage: str | None = None,
    ) -> DecisionResult:
        """Executa um julgamento atômico (Choice/Score) registrando envelope auditável."""
        pack = self.get_pack(pack_id)
        effective_stage = stage or pack_id
        identity = self.decision_model.model_identity()
        versions = self._build_component_versions(pack, context, component_versions)
        input_hash = canonical_hash({"pack_id": pack_id, "context": context})
        cache_key = compute_cache_key(
            stage=effective_stage,
            operation=pack_id,
            input_hash=input_hash,
            component_versions=versions,
            model=identity.model,
            mode=identity.mode,
        )
        attempt = self._attempts_by_key.get(cache_key, 0) + 1
        self._attempts_by_key[cache_key] = attempt

        started_at = datetime.now(UTC)
        result: DecisionResult | None = None
        error: BaseException | None = None
        outcome = ExecutionOutcome.SUCCEEDED

        with capture_provider_calls() as provider_calls:
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
                outcome = ExecutionOutcome.UNAVAILABLE
                error = exc
            except ValueError as exc:
                outcome = ExecutionOutcome.REJECTED
                error = exc
            except Exception as exc:
                outcome = ExecutionOutcome.FAILED
                error = exc

        finished_at = datetime.now(UTC)
        effective_call = provider_calls[-1] if provider_calls else None
        effective_model = (
            effective_call.model
            if effective_call and effective_call.model
            else identity.model
        )
        provider_name = (
            effective_call.provider
            if effective_call and effective_call.provider
            else identity.provider
        )
        usage = effective_call.usage if effective_call else None
        cost = effective_call.cost if effective_call else MeasuredCost.unavailable("no_provider_telemetry")
        provider_attempts = effective_call.attempts if effective_call else None

        envelope = ExecutionEnvelope.create(
            analysis_id=analysis.id if analysis else None,
            tenant_id=analysis.tenant_id if analysis else None,
            stage=effective_stage,
            operation=pack_id,
            attempt=attempt,
            input_hash=input_hash,
            cache_key=cache_key,
            source_ids=evidence_ids or [],
            component_versions=versions,
            provider=provider_name,
            configured_model=identity.model,
            model=effective_model,
            mode=identity.mode,
            outcome=outcome,
            started_at=started_at,
            finished_at=finished_at,
            usage=usage,
            cost=cost,
            provider_attempts=provider_attempts,
            decision_id=result.id if result else None,
            result_kind=result.decision_type.value if result else None,
            error_code=type(error).__name__ if error else None,
            error_detail=str(error) if error else None,
        )

        await self._persist_envelope(envelope)

        if error is not None:
            if outcome == ExecutionOutcome.UNAVAILABLE:
                if analysis is not None:
                    analysis.block(
                        correlation_id=correlation_id,
                        reason=f"JEV indisponível para o decision pack '{pack_id}': {error}",
                    )
                raise JEVServiceUnavailableError(
                    f"Falha de disponibilidade do JEV no pack '{pack_id}': {error}"
                ) from error
            raise JEVError(f"Erro inesperado no julgamento do pack '{pack_id}': {error}") from error

        assert result is not None

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
