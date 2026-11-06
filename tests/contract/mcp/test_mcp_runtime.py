import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.entrypoints.mcp.server import PrometeusMCPServer
from prometeus.infrastructure.db.models import AnalysisModel, Base, ConfigSnapshotModel


async def test_mcp_creation_uses_canonical_snapshot_idempotency_and_publication():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    published = []
    server = PrometeusMCPServer(
        factory, publisher=lambda analysis_id, correlation_id: published.append(analysis_id)
    )
    args = {
        "course_name": "MCP fixture",
        "tenant_id": "ens",
        "idempotency_key": "mcp-runtime-test",
        "proposal_data": {},
    }
    first = await server.execute_tool("create_course_analysis", args)
    second = await server.execute_tool("create_course_analysis", args)
    assert first["analysis_id"] == second["analysis_id"]
    assert published == [first["analysis_id"]]
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(ConfigSnapshotModel)) == 1
        assert await session.scalar(select(func.count()).select_from(AnalysisModel)) == 1
    await engine.dispose()


async def test_mcp_forbids_tenant_override_and_handles_notifications():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    server = PrometeusMCPServer(async_sessionmaker(engine), publisher=lambda *_: None)
    with pytest.raises(ValueError, match="instituição"):
        await server.execute_tool(
            "create_course_analysis",
            {"course_name": "MCP fixture", "tenant_id": "infnet", "idempotency_key": "x"},
        )
    assert (
        await server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
        is None
    )
    await engine.dispose()
