"""Testes de integração do SectorRadarService (coleta higienizada, cache TTL de 7 dias e resiliência parcial)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.sector_radar import SectorRadarService
from prometeus.domain.configuration import load_tenant_config
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyActorFailedError
from prometeus.infrastructure.apify.schemas import ApifyExecutionResult, ApifyRunMetadata
from prometeus.infrastructure.db.models import Base


class FakeRadarExecutor:
    def __init__(self, *, fail_instagram: bool = False) -> None:
        self.fail_instagram = fail_instagram
        self.calls: list[PlannedToolCall] = []

    async def execute(
        self, call: PlannedToolCall, *, max_total_charge_usd: float
    ) -> ApifyExecutionResult:
        self.calls.append(call)
        if call.capability == "instagram":
            if self.fail_instagram:
                raise ApifyActorFailedError(
                    run_id="run-ig-fail", status="FAILED", message="Actor timeout temporário"
                )
            ig_items = [
                {
                    "url": "https://www.instagram.com/p/porto123/",
                    "ownerUsername": call.query,
                    "caption": (
                        "<script>alert(1)</script> Novo assistente de IA da Porto agiliza cotação "
                        "e regulação de sinistros para corretores parceiros. Contato: joao@porto.com.br"
                    ),
                }
            ]
            return ApifyExecutionResult(
                run=ApifyRunMetadata(
                    run_id=f"run-ig-{len(self.calls)}",
                    dataset_id="ds-ig-1",
                    status="SUCCEEDED",
                    actor_id="apify/instagram-scraper",
                    build_number="0.0.340",
                    cost_usd=0.08,
                ),
                items=ig_items,
                total_items=len(ig_items),
            )

        # google_search
        items: list[dict[str, Any]] = []
        if "portoseguro.com.br" in call.query:
            items.append(
                {
                    "organicResults": [
                        {
                            "title": "Porto Seguro lança jornada digital de subscrição e IA para corretores",
                            "url": "https://www.portoseguro.com.br/corretores/inovacao-ia",
                            "description": "Automação de vistoria e subscrição reduz retrabalho operacional de corretores.",
                        },
                        {
                            "title": "Bradesco Seguros investe em saúde suplementar e atendimento digital",
                            "url": "https://www.bradescoseguros.com.br/clientes/inovacao-sinistros",
                            "description": "Novos fluxos de regulação de sinistros e capacitação consultiva.",
                        },
                    ]
                }
            )
        if "mapfre.com.br" in call.query:
            items.append(
                {
                    "organicResults": [
                        {
                            "title": "MAPFRE expande soluções em agronegócio e grandes riscos",
                            "url": "https://www.linkedin.com/company/mapfre/posts/global-update",
                            "description": "MAPFRE anuncia diretrizes corporativas globais de transformação digital e seguros rurais.",
                        }
                    ]
                }
            )
        return ApifyExecutionResult(
            run=ApifyRunMetadata(
                run_id=f"run-gs-{len(self.calls)}",
                dataset_id="ds-gs-1",
                status="SUCCEEDED",
                actor_id="apify/google-search-scraper",
                build_number="0.0.474",
                cost_usd=0.10,
            ),
            items=items,
            total_items=len(items),
        )


@pytest.mark.asyncio
async def test_sector_radar_refresh_sanitizes_caches_ttl_and_tags_scope() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    executor = FakeRadarExecutor()

    async with session_factory() as session:
        service = SectorRadarService(
            session=session,
            executor=executor,
            allowed_capabilities=["google_search", "instagram"],
        )
        snapshot = await service.refresh_radar(
            tenant_id="ens",
            tenant_config=ens_cfg,
            max_budget_usd=1.50,
            force=False,
        )

        assert snapshot.status == "READY"
        assert snapshot.monitored_actors_count == 10
        assert "porto-seguro" in snapshot.covered_actors
        assert "bradesco-seguros" in snapshot.covered_actors
        assert len(snapshot.signals) >= 3
        assert snapshot.spent_usd > 0.0

        collected = (
            snapshot.collected_at
            if snapshot.collected_at.tzinfo
            else snapshot.collected_at.replace(tzinfo=UTC)
        )
        expires = (
            snapshot.expires_at
            if snapshot.expires_at.tzinfo
            else snapshot.expires_at.replace(tzinfo=UTC)
        )
        assert abs((expires - collected) - timedelta(hours=168)) < timedelta(seconds=5)

        # Verifica sanitização de HTML/script e PII (e-mail removido/mascarado)
        combined_text = " ".join(str(sig) for sig in snapshot.signals)
        assert "<script>" not in combined_text
        assert "joao@porto.com.br" not in combined_text

        # Verifica selo Global (contextual) em sinal do LinkedIn corporativo global da MAPFRE
        mapfre_signals = [s for s in snapshot.signals if s["actor_id"] == "mapfre"]
        assert mapfre_signals
        assert mapfre_signals[0]["scope_badge"] == "Global (contextual)"

        # Verifica que nenhum handle não confirmado de Instagram foi consultado
        ig_calls = [c for c in executor.calls if c.capability == "instagram"]
        ig_handles = {c.query.lower() for c in ig_calls}
        for unconfirmed in ("itau", "itauseguros", "hdiseguros", "yelumseguros", "brasilseg"):
            assert unconfirmed not in ig_handles

        first_call_count = len(executor.calls)

        # Segunda chamada antes do vencimento com force=False retorna cache sem gastar Apify ($0 extra)
        cached = await service.refresh_radar(
            tenant_id="ens",
            tenant_config=ens_cfg,
            max_budget_usd=1.50,
            force=False,
        )
        assert cached.id == snapshot.id
        assert len(executor.calls) == first_call_count

    await engine.dispose()


@pytest.mark.asyncio
async def test_sector_radar_marks_partial_when_one_channel_fails() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ens_cfg = load_tenant_config(Path("config/tenants/ens.example.yaml"))
    executor = FakeRadarExecutor(fail_instagram=True)

    async with session_factory() as session:
        service = SectorRadarService(
            session=session,
            executor=executor,
            allowed_capabilities=["google_search", "instagram"],
        )
        snapshot = await service.refresh_radar(
            tenant_id="ens",
            tenant_config=ens_cfg,
            max_budget_usd=1.50,
            force=True,
        )

        assert snapshot.status == "PARTIAL"
        assert len(snapshot.signals) >= 2
        assert snapshot.error_summary is not None
        assert "instagram" in snapshot.error_summary.lower()

    await engine.dispose()
