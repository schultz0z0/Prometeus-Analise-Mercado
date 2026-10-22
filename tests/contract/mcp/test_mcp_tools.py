"""Testes de contrato para ferramentas e protocolo MCP (Fase 07)."""

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.entrypoints.mcp.server import PrometeusMCPServer
from prometeus.infrastructure.db.models import Base


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_mcp_initialize_and_ping(session_factory) -> None:
    server = PrometeusMCPServer(session_factory)

    init_resp = await server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp["result"]["protocolVersion"] == "2024-11-05"
    assert "Prometeus" in init_resp["result"]["serverInfo"]["name"]

    ping_resp = await server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert ping_resp["result"] == {}


@pytest.mark.asyncio
async def test_mcp_tools_list_contains_high_level_tools(session_factory) -> None:
    server = PrometeusMCPServer(session_factory)

    resp = await server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    assert len(tools) == 5
    assert "create_course_analysis" in tool_names
    assert "check_analysis_progress" in tool_names
    assert "retrieve_course_dossier" in tool_names
    assert "submit_decision" in tool_names
    assert "record_course_outcome" in tool_names

    # Não deve expor ferramentas internas de baixo nível (ADR-0007)
    assert "scrape_apify" not in tool_names
    assert "query_raw_google_ads" not in tool_names


@pytest.mark.asyncio
async def test_mcp_tools_call_lifecycle(session_factory) -> None:
    server = PrometeusMCPServer(session_factory)

    # 1. create_course_analysis
    call_create = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "create_course_analysis",
            "arguments": {
                "course_name": "MBA em Sinistros Cibernéticos",
                "tenant_id": "ens",
                "proposal_data": {"price": 1400.0},
            },
        },
    }
    resp_create = await server.handle_request(call_create)
    create_content = json.loads(resp_create["result"]["content"][0]["text"])
    analysis_id = create_content["analysis_id"]
    assert create_content["status"] == "QUEUED"

    # 2. check_analysis_progress
    call_progress = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "check_analysis_progress",
            "arguments": {"analysis_id": analysis_id},
        },
    }
    resp_progress = await server.handle_request(call_progress)
    progress_content = json.loads(resp_progress["result"]["content"][0]["text"])
    assert progress_content["analysis_id"] == analysis_id
    assert progress_content["status"] == "QUEUED"

    # 3. submit_decision
    call_dec = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "submit_decision",
            "arguments": {
                "analysis_id": analysis_id,
                "user_id": "usr-coord-01",
                "user_role": "coordinator",
                "decision": "APPROVED",
                "rationale": "Excelente oportunidade de mercado.",
            },
        },
    }
    resp_dec = await server.handle_request(call_dec)
    dec_content = json.loads(resp_dec["result"]["content"][0]["text"])
    assert dec_content["status"] == "RECORDED"

    # 4. record_course_outcome
    call_out = {
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "record_course_outcome",
            "arguments": {
                "analysis_id": analysis_id,
                "external_course_id": "ENS-CYBER-01",
                "launch_date": "2026-09-01",
                "enrolled_count": 52,
                "revenue_brl": 420000.0,
            },
        },
    }
    resp_out = await server.handle_request(call_out)
    out_content = json.loads(resp_out["result"]["content"][0]["text"])
    assert out_content["enrolled_count"] == 52
