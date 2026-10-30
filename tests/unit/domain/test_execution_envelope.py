"""Contrato do envelope de execução por tentativa (plano sênior, tarefa 0.3)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from prometeus.domain.execution_envelope import (
    CostStatus,
    ExecutionEnvelope,
    ExecutionOutcome,
    MeasuredCost,
    ProviderCallTelemetry,
    TokenUsage,
    canonical_hash,
    capture_provider_calls,
    compute_cache_key,
    record_provider_call,
    scrub_secrets,
    summarize_costs,
)

VERSIONS = {"normalizer": "n-v1", "projector": "p-v1", "pack": "market-relevance-v1@1.0.0"}


def _key(**overrides: object) -> str:
    params: dict[str, object] = {
        "stage": "evidence_review",
        "operation": "market-relevance-v1",
        "input_hash": canonical_hash({"data": [1, 2, 3]}),
        "component_versions": VERSIONS,
        "model": "gpt-x",
        "mode": "traditional_llm",
    }
    params.update(overrides)
    return compute_cache_key(**params)  # type: ignore[arg-type]


def test_same_input_and_versions_allow_reuse_even_with_reordered_keys() -> None:
    assert canonical_hash({"a": 1, "b": [1, 2]}) == canonical_hash({"b": [1, 2], "a": 1})
    reordered = dict(reversed(list(VERSIONS.items())))
    assert _key() == _key(component_versions=reordered)


@pytest.mark.parametrize(
    "override",
    [
        {"model": "gpt-y"},
        {"mode": "jev"},
        {"component_versions": {**VERSIONS, "projector": "p-v2"}},
        {"component_versions": {**VERSIONS, "normalizer": "n-v2"}},
        {"input_hash": canonical_hash({"data": [1, 2, 4]})},
        {"operation": "syllabus-fit-v1"},
    ],
)
def test_model_projector_normalizer_or_input_change_invalidates_cache_key(
    override: dict[str, object],
) -> None:
    assert _key(**override) != _key()


def test_unknown_usage_and_cost_are_never_reported_as_real_zero() -> None:
    cost = MeasuredCost.unavailable("provider_did_not_return_cost")
    assert cost.status is CostStatus.UNAVAILABLE
    assert cost.amount_usd is None
    with pytest.raises(ValueError):
        MeasuredCost(status=CostStatus.MEASURED, amount_usd=None, source="x")
    with pytest.raises(ValueError):
        MeasuredCost(status=CostStatus.UNAVAILABLE, amount_usd=Decimal("0"), source="x")
    with pytest.raises(ValueError):
        MeasuredCost.measured(Decimal("-0.01"), source="x")

    summary = summarize_costs(
        [MeasuredCost.measured(Decimal("0.002"), source="apify"), cost, cost]
    )
    assert summary["measured_usd"] == "0.002"
    assert summary["unavailable_count"] == 2
    assert summary["complete"] is False
    assert summarize_costs([])["complete"] is True


def test_token_usage_accepts_documented_provider_shapes_only() -> None:
    responses = TokenUsage.from_provider(
        {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    )
    chat = TokenUsage.from_provider(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    )
    assert responses == chat == TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)
    assert TokenUsage.from_provider(None) is None
    assert TokenUsage.from_provider({"input_tokens": True}) is None
    assert TokenUsage.from_provider({"input_tokens": -1}) is None
    assert TokenUsage.from_provider({"unrelated": 3}) is None


def test_scrub_secrets_removes_credentials_but_keeps_token_counts() -> None:
    payload = {
        "api_key": "abc",
        "Authorization": "Bearer xyz",
        "APIFY_TOKEN": "apify_api_12345678abcdef",
        "refresh_token": "r",
        "nested": [{"note": "header Bearer sk-ABCDEFGH12345678 here"}],
        "usage": {"input_tokens": 3, "total_tokens": 4},
        "pack": "market-relevance-v1",
    }
    clean = scrub_secrets(payload)
    dumped = json.dumps(clean)
    for secret in ("abc", "xyz", "apify_api_12345678abcdef", "sk-ABCDEFGH12345678"):
        assert secret not in dumped
    assert clean["usage"] == {"input_tokens": 3, "total_tokens": 4}
    assert clean["pack"] == "market-relevance-v1"


def test_rejected_attempt_envelope_is_auditable_and_snapshot_has_no_secret() -> None:
    started = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    envelope = ExecutionEnvelope.create(
        analysis_id="a1",
        tenant_id="ens",
        stage="evidence_review",
        operation="market-relevance-v1",
        attempt=2,
        input_hash=canonical_hash({"x": 1}),
        cache_key=_key(),
        source_ids=["ev-1"],
        component_versions={**VERSIONS, "token": "sk-SHOULDNOTLEAK123456"},
        provider="OpenAIGenerativeClient",
        model="gpt-x",
        mode="traditional_llm",
        outcome=ExecutionOutcome.REJECTED,
        started_at=started,
        finished_at=started,
        error_code="ValueError",
        error_detail="resposta inválida; Authorization: Bearer sk-SHOULDNOTLEAK123456",
    )
    snapshot = envelope.to_snapshot()
    assert snapshot["outcome"] == "REJECTED"
    assert snapshot["attempt"] == 2
    assert snapshot["decision_id"] is None
    assert snapshot["cost"] == {
        "status": "UNAVAILABLE",
        "amount_usd": None,
        "source": "no_provider_telemetry",
    }
    assert snapshot["usage"] is None
    assert "SHOULDNOTLEAK" not in json.dumps(snapshot)


def test_provider_telemetry_is_scoped_to_the_capture_context() -> None:
    telemetry = ProviderCallTelemetry(
        provider="p", model="m", attempts=1, usage=None, cost=MeasuredCost.unavailable("x")
    )
    record_provider_call(telemetry)  # fora de escopo: ignorado, sem erro
    with capture_provider_calls() as calls:
        record_provider_call(telemetry)
    assert calls == [telemetry]

