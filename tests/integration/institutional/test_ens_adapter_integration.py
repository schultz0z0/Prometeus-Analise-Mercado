import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.infrastructure.db.models import (
    Base,
    HistoricalCourseModel,
    HistoricalFunnelModel,
)
from prometeus.infrastructure.institutional.mock import MockInstitutionalAdapter


@pytest.fixture
async def int_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def test_synchronize_and_persist_courses_and_funnel(int_session: AsyncSession) -> None:
    adapter = MockInstitutionalAdapter()

    # 1. Busca cursos do conector institucional
    courses = await adapter.list_courses()
    assert len(courses) > 0

    course_ids = [c.external_id for c in courses]
    funnel_metrics = await adapter.get_funnel_metrics(course_ids, period="2025-1")
    financial_metrics = await adapter.get_financial_metrics(course_ids, period="2025-1")

    # 2. Persiste cursos históricos no banco de dados
    fin_map = {f.external_course_id: f for f in financial_metrics}

    for c in courses:
        course_model = HistoricalCourseModel(
            id=str(uuid.uuid4()),
            tenant_id="ens",
            external_id=c.external_id,
            name=c.name,
            category=c.category,
            modality=c.modality,
            workload_hours=c.workload_hours,
            status=c.status,
            tags=c.tags,
            target_audience=c.target_audience,
        )
        int_session.add(course_model)
        await int_session.flush()

        # Adiciona registros de funil vinculados
        matching_funnel = [m for m in funnel_metrics if m.external_course_id == c.external_id]
        for fm in matching_funnel:
            fin = fin_map.get(c.external_id)
            funnel_model = HistoricalFunnelModel(
                id=str(uuid.uuid4()),
                course_id=course_model.id,
                external_course_id=c.external_id,
                period=fm.period,
                leads=fm.leads,
                applicants=fm.applicants,
                enrolled=fm.enrolled,
                conversion_lead_to_applicant=fm.conversion_lead_to_applicant,
                conversion_applicant_to_enrolled=fm.conversion_applicant_to_enrolled,
                conversion_lead_to_enrolled=fm.conversion_lead_to_enrolled,
                average_ticket_brl=fin.average_ticket_brl if fin else None,
                total_revenue_brl=fin.total_revenue_brl if fin else None,
            )
            int_session.add(funnel_model)

    await int_session.commit()

    # 3. Consulta e validação de persistência
    stmt = select(HistoricalCourseModel).where(HistoricalCourseModel.tenant_id == "ens")
    persisted_courses = (await int_session.execute(stmt)).scalars().all()
    assert len(persisted_courses) == 3

    # Busca curso específico e valida integridade do funil
    stmt_funnel = select(HistoricalFunnelModel).where(
        HistoricalFunnelModel.external_course_id == "ENS-SEG-01"
    )
    funnel_rec = (await int_session.execute(stmt_funnel)).scalar_one_or_none()
    assert funnel_rec is not None
    assert funnel_rec.leads == 1400
    assert funnel_rec.applicants == 280
    assert funnel_rec.enrolled == 98
    assert funnel_rec.conversion_lead_to_applicant == 0.20
    assert funnel_rec.conversion_applicant_to_enrolled == 0.35
    assert funnel_rec.conversion_lead_to_enrolled == 0.07
    assert funnel_rec.average_ticket_brl == 16500.00
    assert funnel_rec.total_revenue_brl == 1617000.00
