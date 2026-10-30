"""Envelope de execução auditável por tentativa de modelo/decisão (plano sênior, tarefa 0.3).

O envelope registra *como* uma etapa foi executada — input efetivo por hash, IDs de
origem, versões dos componentes, modelo/modo efetivos, tempo, resultado, uso e custo —
sem armazenar prompts, payloads ou credenciais. Uso e custo desconhecidos permanecem
explicitamente indisponíveis; nunca são convertidos em zero "real".
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

ENVELOPE_SCHEMA_VERSION = 1
SECRET_PLACEHOLDER = "[SECRET_REMOVED]"
MAX_ERROR_DETAIL = 500


class ExecutionOutcome(StrEnum):
    """Resultado técnico de uma tentativa; não é julgamento de mercado."""

    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"  # resposta recebida e recusada pelo contrato em código
    FAILED = "FAILED"  # erro técnico não classificado como indisponibilidade
    UNAVAILABLE = "UNAVAILABLE"  # provedor fora do ar, timeout ou transporte


class CostStatus(StrEnum):
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class MeasuredCost:
    """Custo com origem explícita. ``amount_usd`` é ``None`` quando indisponível."""

    status: CostStatus
    amount_usd: Decimal | None
    source: str

    def __post_init__(self) -> None:
        if self.status is CostStatus.UNAVAILABLE:
            if self.amount_usd is not None:
                raise ValueError("Custo indisponível não pode carregar valor numérico.")
            return
        if self.amount_usd is None:
            raise ValueError("Custo medido ou estimado exige valor.")
        if not self.amount_usd.is_finite() or self.amount_usd < 0:
            raise ValueError("Custo deve ser finito e não negativo.")

    @classmethod
    def unavailable(cls, source: str) -> MeasuredCost:
        return cls(status=CostStatus.UNAVAILABLE, amount_usd=None, source=source)

    @classmethod
    def measured(cls, amount_usd: Decimal, *, source: str) -> MeasuredCost:
        return cls(status=CostStatus.MEASURED, amount_usd=amount_usd, source=source)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "amount_usd": None if self.amount_usd is None else str(self.amount_usd),
            "source": self.source,
        }


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


@dataclass(frozen=True)
class TokenUsage:
    """Uso de tokens tal como retornado pelo provedor; campos ausentes ficam ``None``."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    @classmethod
    def from_provider(cls, raw: Any) -> TokenUsage | None:
        """Aceita os formatos documentados de Responses e Chat Completions.

        Responses: ``input_tokens``/``output_tokens``/``total_tokens``.
        Chat Completions: ``prompt_tokens``/``completion_tokens``/``total_tokens``.
        Valores booleanos, negativos ou não inteiros são descartados.
        """
        if not isinstance(raw, Mapping):
            return None
        usage = cls(
            input_tokens=_non_negative_int(raw.get("input_tokens", raw.get("prompt_tokens"))),
            output_tokens=_non_negative_int(
                raw.get("output_tokens", raw.get("completion_tokens"))
            ),
            total_tokens=_non_negative_int(raw.get("total_tokens")),
        )
        if usage.input_tokens is None and usage.output_tokens is None and usage.total_tokens is None:
            return None
        return usage

    def to_dict(self) -> dict[str, int | None]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class ProviderCallTelemetry:
    """Telemetria técnica de uma chamada a provedor, sem conteúdo nem credenciais."""

    provider: str
    model: str | None
    attempts: int
    usage: TokenUsage | None
    cost: MeasuredCost


_ACTIVE_CALLS: ContextVar[list[ProviderCallTelemetry] | None] = ContextVar(
    "prometeus_provider_calls", default=None
)


@contextmanager
def capture_provider_calls() -> Iterator[list[ProviderCallTelemetry]]:
    """Coleta a telemetria das chamadas feitas no contexto assíncrono atual."""
    calls: list[ProviderCallTelemetry] = []
    token = _ACTIVE_CALLS.set(calls)
    try:
        yield calls
    finally:
        _ACTIVE_CALLS.reset(token)


def record_provider_call(telemetry: ProviderCallTelemetry) -> None:
    """Registra telemetria se houver captura ativa; fora dela é ignorada."""
    calls = _ACTIVE_CALLS.get()
    if calls is not None:
        calls.append(telemetry)


def canonical_hash(payload: Any) -> str:
    """SHA-256 de JSON canônico; reordenar chaves não altera o hash."""
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_cache_key(
    *,
    stage: str,
    operation: str,
    input_hash: str,
    component_versions: Mapping[str, str],
    model: str,
    mode: str,
) -> str:
    """Chave de reuso: muda com input efetivo, versões de componentes, modelo ou modo."""
    return canonical_hash(
        {
            "schema": ENVELOPE_SCHEMA_VERSION,
            "stage": stage,
            "operation": operation,
            "input_hash": input_hash,
            "component_versions": dict(component_versions),
            "model": model,
            "mode": mode,
        }
    )


_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "secret",
    "password",
    "passwd",
    "cookie",
    "credential",
    "bearer",
)
_SECRET_VALUE_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._~+/=-]+"
    r"|sk-[A-Za-z0-9_-]{8,}"
    r"|apify_api_[A-Za-z0-9]{8,}"
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,})"
)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    if lowered.endswith("_tokens"):  # contagens de uso, não credenciais
        return False
    if any(part in lowered for part in _SECRET_KEY_PARTS):
        return True
    return lowered == "token" or lowered.endswith("_token") or lowered.endswith("-token")


def scrub_secrets(value: Any) -> Any:
    """Remove credenciais por nome de campo e padrões de valor conhecidos."""
    if isinstance(value, Mapping):
        return {
            str(k): SECRET_PLACEHOLDER if _is_secret_key(str(k)) else scrub_secrets(v)
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [scrub_secrets(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub(SECRET_PLACEHOLDER, value)
    return value


def summarize_costs(costs: Iterable[MeasuredCost]) -> dict[str, Any]:
    """Soma apenas custos conhecidos e informa quantos ficaram indisponíveis."""
    measured = Decimal("0")
    known = 0
    unavailable = 0
    for cost in costs:
        if cost.amount_usd is None:
            unavailable += 1
        else:
            measured += cost.amount_usd
            known += 1
    return {
        "measured_usd": str(measured),
        "known_count": known,
        "unavailable_count": unavailable,
        "complete": unavailable == 0,
    }


@dataclass(frozen=True)
class ExecutionEnvelope:
    """Registro imutável de uma tentativa de execução de etapa com modelo."""

    id: str
    analysis_id: str | None
    tenant_id: str | None
    stage: str
    operation: str
    attempt: int
    input_hash: str
    cache_key: str
    source_ids: tuple[str, ...]
    component_versions: dict[str, str]
    provider: str
    configured_model: str
    model: str
    mode: str
    outcome: ExecutionOutcome
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    usage: TokenUsage | None
    cost: MeasuredCost
    provider_attempts: int | None = None
    decision_id: str | None = None
    result_kind: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    schema_version: int = ENVELOPE_SCHEMA_VERSION
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        analysis_id: str | None,
        tenant_id: str | None,
        stage: str,
        operation: str,
        attempt: int,
        input_hash: str,
        cache_key: str,
        source_ids: Iterable[str],
        component_versions: Mapping[str, str],
        provider: str,
        model: str,
        mode: str,
        outcome: ExecutionOutcome,
        started_at: datetime,
        finished_at: datetime,
        configured_model: str | None = None,
        duration_ms: float | None = None,
        usage: TokenUsage | None = None,
        cost: MeasuredCost | None = None,
        provider_attempts: int | None = None,
        decision_id: str | None = None,
        result_kind: str | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> ExecutionEnvelope:
        if attempt < 1:
            raise ValueError("A tentativa começa em 1.")
        versions = scrub_secrets({str(k): str(v) for k, v in component_versions.items()})
        detail = None
        if error_detail:
            detail = str(scrub_secrets(error_detail))[:MAX_ERROR_DETAIL]
        elapsed = (
            duration_ms
            if duration_ms is not None
            else (finished_at - started_at).total_seconds() * 1000.0
        )
        return cls(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            tenant_id=tenant_id,
            stage=stage,
            operation=operation,
            attempt=attempt,
            input_hash=input_hash,
            cache_key=cache_key,
            source_ids=tuple(str(item) for item in source_ids),
            component_versions=versions,
            provider=provider,
            configured_model=configured_model or model,
            model=model,
            mode=mode,
            outcome=outcome,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=round(max(elapsed, 0.0), 3),
            usage=usage,
            cost=cost or MeasuredCost.unavailable("no_provider_telemetry"),
            provider_attempts=provider_attempts,
            decision_id=decision_id,
            result_kind=result_kind,
            error_code=error_code,
            error_detail=detail,
        )

    def to_snapshot(self) -> dict[str, Any]:
        """Representação JSON sem segredos para auditoria e replay."""
        snapshot: dict[str, Any] = {
            "schema_version": self.schema_version,
            "id": self.id,
            "analysis_id": self.analysis_id,
            "tenant_id": self.tenant_id,
            "stage": self.stage,
            "operation": self.operation,
            "attempt": self.attempt,
            "input_hash": self.input_hash,
            "cache_key": self.cache_key,
            "source_ids": list(self.source_ids),
            "component_versions": dict(self.component_versions),
            "provider": self.provider,
            "configured_model": self.configured_model,
            "model": self.model,
            "mode": self.mode,
            "outcome": self.outcome.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_ms": self.duration_ms,
            "usage": None if self.usage is None else self.usage.to_dict(),
            "cost": self.cost.to_dict(),
            "provider_attempts": self.provider_attempts,
            "decision_id": self.decision_id,
            "result_kind": self.result_kind,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
        }
        scrubbed: dict[str, Any] = scrub_secrets(snapshot)
        return scrubbed

