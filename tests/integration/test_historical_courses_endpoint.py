import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.models import Base
from prometeus.infrastructure.db.session import get_db_session
from prometeus.infrastructure.institutional.ens.seeder import seed_historical_courses


@pytest.fixture
async def test_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Semeia a base sintética versionada na sessão isolada de teste.
        await seed_historical_courses(session, tenant_id="ens", reset=True)
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> httpx.AsyncClient:
    async def override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_institutional_courses_returns_enriched_test_courses(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    resp = await client.get("/v1/institutional/courses?tenant_id=ens")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "ens"
    assert data["total"] == 33
    assert all(c["is_synthetic"] is True for c in data["courses"])
    assert all(c["curriculum_modules"] and c["family"] for c in data["courses"])

    ext_ids = [c["external_id"] for c in data["courses"]]
    assert "ENS-MBA-SEG-01" in ext_ids
    assert "ENS-ESP-CYBER-02" in ext_ids
    assert "ENS-EXT-SIN-03" in ext_ids
    assert "ENS-CAP-VEND-04" in ext_ids
    assert "ENS-APERF-DIR-05" in ext_ids


@pytest.mark.asyncio
async def test_get_institutional_course_detail_with_cancelled_quorum(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    resp = await client.get("/v1/institutional/courses/ENS-APERF-DIR-05?tenant_id=ens")
    assert resp.status_code == 200
    course = resp.json()
    assert course["external_id"] == "ENS-APERF-DIR-05"
    assert course["status"] == "archived"

    funnels = course["funnel_history"]
    assert len(funnels) == 2

    f24 = next(f for f in funnels if f["period"] == "2024")
    f25 = next(f for f in funnels if f["period"] == "2025")

    assert f24["enrolled"] == 15
    assert f24["total_revenue_brl"] == 58500.0

    # Oferta 2025 cancelada por quórum insuficiente (6 alunos vs 15 necessários)
    assert f25["enrolled"] == 6
    assert f25["total_revenue_brl"] == 0.0


@pytest.mark.asyncio
async def test_successful_course_metrics(
    client: httpx.AsyncClient, test_session: AsyncSession
) -> None:
    resp = await client.get("/v1/institutional/courses/ENS-MBA-SEG-01?tenant_id=ens")
    assert resp.status_code == 200
    course = resp.json()
    assert course["external_id"] == "ENS-MBA-SEG-01"
    assert course["curriculum_modules"]
    assert course["is_synthetic"] is True
    assert course["academic_reference"]["verified_fields"] == ["name", "category"]
    assert course["status"] == "active"

    funnels = course["funnel_history"]
    assert len(funnels) == 2
    f24 = next(f for f in funnels if f["period"] == "2024")
    f25 = next(f for f in funnels if f["period"] == "2025")

    assert f24["enrolled"] == 84
    assert f25["enrolled"] == 102
    assert f25["total_revenue_brl"] > f24["total_revenue_brl"]
    assert f25["price_period"] == "total"
    assert f25["cohort_status"] == "COMPLETED"
