"""Teste ponta a ponta (E2E) simulando a jornada completa de integração do Chatbot (Gate E).

Cenário:
1. Chatbot submete proposta de curso (MCP / REST).
2. Pipeline processa etapas (scoring, quality gate, síntese do dossiê).
3. Webhook de conclusão é disparado e validado pelo receptor com HMAC.
4. Chatbot recupera o dossiê executivo e apresenta ao decisor.
5. Decisor institucional registra decisão humana aprovando o lançamento.
6. Chatbot registra os desfechos reais de captação (outcomes) pós-lançamento.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.analyses import AnalysisRecommendation
from prometeus.domain.dossiers import DossierStatus
from prometeus.domain.webhooks import (
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    verify_webhook_signature,
)
from prometeus.entrypoints.mcp.server import PrometeusMCPServer
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import (
    Base,
    MarketEvidenceModel,
    ScoringResultModel,
)
from prometeus.infrastructure.llm.fake import FakeGenerativeModel
from prometeus.infrastructure.webhooks.dispatcher import WebhookDispatcher


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_chatbot_journey_gate_e(session_factory) -> None:
    webhook_secret = "chatbot-staging-secret-key"
    received_webhooks: list[dict[str, Any]] = []

    def chatbot_webhook_receiver(request: httpx.Request) -> httpx.Response:
        sig = request.headers.get("X-Prometeus-Signature", "")
        ts = request.headers.get("X-Prometeus-Timestamp", "")
        body_text = request.content.decode("utf-8")

        # Chatbot valida autenticidade da assinatura
        is_valid = verify_webhook_signature(webhook_secret, sig, ts, body_text)
        assert is_valid is True, "Assinatura do webhook inválida!"

        data = json.loads(body_text)
        received_webhooks.append(data)
        return httpx.Response(200, json={"status": "acknowledged"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(chatbot_webhook_receiver))

    # --- ETAPA 1: Chatbot submete proposta via MCP ---
    mcp_server = PrometeusMCPServer(session_factory)
    req_create = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_course_analysis",
            "arguments": {
                "course_name": "MBA em Sinistros Globais e Riscos ESG",
                "tenant_id": "ens",
                "proposal_data": {
                    "workload_hours": 360,
                    "target_audience": "Líderes de Sinistros e Riscos",
                    "proposed_price_brl": 15000.0,
                },
            },
        },
    }
    resp_create = await mcp_server.handle_request(req_create)
    content_create = json.loads(resp_create["result"]["content"][0]["text"])
    analysis_id = content_create["analysis_id"]
    assert content_create["status"] == "QUEUED"

    # --- ETAPA 2: Pipeline de processamento (Scoring e Dossiê) ---
    async with session_factory() as session:
        repo = AnalysisRepository(session)
        analysis = await repo.get_by_id(analysis_id)
        assert analysis is not None
        analysis.start(correlation_id="corr-e2e")
        await repo.save(analysis)

        # Insere ScoringResult
        scoring = ScoringResultModel(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            profile_id="default-v1",
            viability_score=86.5,
            coverage_score=1.0,
            confidence_score=0.92,
            partial_score=86.5,
            recommendation="APPROVED",
            is_experimental=False,
            pillar_scores={
                "internal_history": {"raw_score": 85.0, "is_present": True},
                "search_and_media": {"raw_score": 88.0, "is_present": True},
            },
            gate_details={"all_passed": True},
            created_at=datetime.now(UTC),
        )
        session.add(scoring)

        # Insere evidência de mercado
        ev = MarketEvidenceModel(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            evidence_type="SEARCH_VOLUME",
            source_name="GoogleAds",
            source_url="https://ads.google.com",
            collector="google_ads",
            content_hash="hash-ev-e2e",
            title="Demanda por Riscos ESG",
            raw_payload={},
            sanitized_data={"monthly_volume": 3400, "cpc_brl": 7.50},
            quality_score=0.95,
            cost_usd=0.01,
            collected_at=datetime.now(UTC),
        )
        session.add(ev)
        await session.commit()

        # Finaliza análise com recomendação APPROVED
        analysis.complete(recommendation=AnalysisRecommendation.APPROVED, correlation_id="corr-e2e")
        await repo.save(analysis)
        await session.commit()

        # Sintetiza dossiê via DossierSynthesisService
        fake_llm = FakeGenerativeModel()
        dossier_svc = DossierSynthesisService(session, fake_llm, DossierVerifier())
        dossier = await dossier_svc.synthesize_and_verify(analysis_id)
        assert dossier.status == DossierStatus.VERIFIED

        # --- ETAPA 3: Disparo de Webhook para o Chatbot ---
        dispatcher = WebhookDispatcher(
            session,
            secret=webhook_secret,
            http_client=mock_client,
        )
        event = WebhookEvent.create(
            event_type=WebhookEventType.ANALYSIS_COMPLETED,
            analysis_id=analysis_id,
            tenant_id="ens",
            payload={
                "viability_score": 86.5,
                "recommendation": "APPROVED",
                "dossier_status": "VERIFIED",
            },
        )
        delivery = await dispatcher.dispatch(event, "https://ens.chatbot/webhooks/market-intel")
        assert delivery.status == WebhookDeliveryStatus.DELIVERED.value

    # Confirma que o chatbot recebeu o evento
    assert len(received_webhooks) == 1
    assert received_webhooks[0]["payload"]["recommendation"] == "APPROVED"

    # --- ETAPA 4: Chatbot recupera o Dossiê via MCP ---
    req_dossier = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "retrieve_course_dossier",
            "arguments": {"analysis_id": analysis_id, "target_audience": "executive"},
        },
    }
    resp_dossier = await mcp_server.handle_request(req_dossier)
    dossier_data = json.loads(resp_dossier["result"]["content"][0]["text"])
    assert dossier_data["status"] == "VERIFIED"
    assert len(dossier_data["sections"]) >= 1

    # --- ETAPA 5: Decisor registra parecer no Chatbot ---
    req_dec = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "submit_decision",
            "arguments": {
                "analysis_id": analysis_id,
                "user_id": "usr-diretor-ens",
                "user_role": "director",
                "decision": "APPROVED",
                "rationale": "Curso aprovado pelo comitê para oferta no portfólio 2026/2027.",
                "adjustments": {"target_enrolled": 60},
            },
        },
    }
    resp_dec = await mcp_server.handle_request(req_dec)
    dec_data = json.loads(resp_dec["result"]["content"][0]["text"])
    assert dec_data["status"] == "RECORDED"

    # --- ETAPA 6: Registro de resultados pós-lançamento (Outcomes) ---
    req_out = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "record_course_outcome",
            "arguments": {
                "analysis_id": analysis_id,
                "external_course_id": "ENS-ESG-2026",
                "launch_date": "2026-10-01",
                "enrolled_count": 65,
                "leads_count": 420,
                "applicants_count": 110,
                "revenue_brl": 975000.0,
                "notes": "Meta superada (65 matriculados vs meta 60).",
            },
        },
    }
    resp_out = await mcp_server.handle_request(req_out)
    out_data = json.loads(resp_out["result"]["content"][0]["text"])
    assert out_data["enrolled_count"] == 65
    assert out_data["status"] == "RECORDED"
