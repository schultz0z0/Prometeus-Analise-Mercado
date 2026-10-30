"""Lógica de semeadura idempotente para cursos e funis históricos da ENS."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.infrastructure.db.models import HistoricalCourseModel, HistoricalFunnelModel
from prometeus.infrastructure.institutional.ens.dataset import (
    DATASET_VERSION,
    ENS_HISTORICAL_PORTFOLIO,
)

logger = logging.getLogger("prometeus.seed_historical")


async def seed_historical_courses(
    session: AsyncSession,
    tenant_id: str = "ens",
    reset: bool = False,
) -> dict[str, Any]:
    """Popula cursos históricos e registros de funil de forma transacional e idempotente."""
    if reset:
        logger.info(f"Modo reset ativado. Excluindo cursos históricos do tenant '{tenant_id}'...")
        await session.execute(
            delete(HistoricalCourseModel).where(HistoricalCourseModel.tenant_id == tenant_id)
        )
        await session.flush()

    stmt_exist = select(HistoricalCourseModel.external_id).where(
        HistoricalCourseModel.tenant_id == tenant_id
    )
    existing_ext_ids = set((await session.execute(stmt_exist)).scalars().all())

    courses_created = 0
    courses_updated = 0
    funnel_created = 0
    total_enrolled = 0
    total_revenue = 0.0

    for item in ENS_HISTORICAL_PORTFOLIO:
        ext_id = item["external_id"]
        funnel_history = item.get("funnel_history", [])

        if ext_id in existing_ext_ids:
            stmt_c = select(HistoricalCourseModel).where(
                HistoricalCourseModel.tenant_id == tenant_id,
                HistoricalCourseModel.external_id == ext_id,
            )
            course_model = (await session.execute(stmt_c)).scalar_one()
            course_model.name = item["name"]
            course_model.category = item["category"]
            course_model.modality = item["modality"]
            course_model.workload_hours = item["workload_hours"]
            course_model.status = item["status"]
            course_model.tags = item["tags"]
            course_model.target_audience = item["target_audience"]
            course_model.family = str(item.get("family", ""))
            course_model.curriculum_text = str(item.get("curriculum_text", ""))
            course_model.curriculum_modules = list(item.get("curriculum_modules", []))
            course_model.updated_at = datetime.now(UTC)
            courses_updated += 1
        else:
            course_id = f"hc_{uuid.uuid4().hex[:16]}"
            course_model = HistoricalCourseModel(
                id=course_id,
                tenant_id=tenant_id,
                external_id=ext_id,
                name=item["name"],
                category=item["category"],
                modality=item["modality"],
                workload_hours=item["workload_hours"],
                status=item["status"],
                tags=item["tags"],
                target_audience=item["target_audience"],
                family=str(item.get("family", "")),
                curriculum_text=str(item.get("curriculum_text", "")),
                curriculum_modules=list(item.get("curriculum_modules", [])),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(course_model)
            await session.flush()
            courses_created += 1

        for fun in funnel_history:
            period = fun["period"]
            leads = int(fun.get("leads") or 0)
            applicants = int(fun.get("applicants") or 0)
            enrolled = int(fun.get("enrolled") or 0)
            ticket = float(fun.get("average_ticket_brl", 0.0))
            # This seeder exclusively owns the declared synthetic ENS fixture:
            # its tickets are full-course tuition (revenue = ticket * enrolled).
            price_period = str(fun.get("price_period", "total"))
            data_complete = all(
                fun.get(key) is not None for key in ("leads", "applicants", "enrolled")
            )
            cohort_status = str(fun.get("status", "UNKNOWN"))
            revenue = float(fun.get("total_revenue_brl", ticket * enrolled))

            lead_to_app = round((applicants / leads), 4) if leads > 0 else 0.0
            app_to_enr = round((enrolled / applicants), 4) if applicants > 0 else 0.0
            lead_to_enr = round((enrolled / leads), 4) if leads > 0 else 0.0

            stmt_f = select(HistoricalFunnelModel).where(
                HistoricalFunnelModel.external_course_id == ext_id,
                HistoricalFunnelModel.period == period,
            )
            funnel_model = (await session.execute(stmt_f)).scalar_one_or_none()

            if funnel_model:
                funnel_model.leads = leads
                funnel_model.applicants = applicants
                funnel_model.enrolled = enrolled
                funnel_model.conversion_lead_to_applicant = lead_to_app
                funnel_model.conversion_applicant_to_enrolled = app_to_enr
                funnel_model.conversion_lead_to_enrolled = lead_to_enr
                funnel_model.average_ticket_brl = ticket
                funnel_model.total_revenue_brl = revenue
                funnel_model.price_period = price_period
                funnel_model.data_complete = data_complete
                funnel_model.cohort_status = cohort_status
            else:
                funnel_id = f"hf_{uuid.uuid4().hex[:16]}"
                funnel_model = HistoricalFunnelModel(
                    id=funnel_id,
                    course_id=course_model.id,
                    external_course_id=ext_id,
                    period=period,
                    leads=leads,
                    applicants=applicants,
                    enrolled=enrolled,
                    conversion_lead_to_applicant=lead_to_app,
                    conversion_applicant_to_enrolled=app_to_enr,
                    conversion_lead_to_enrolled=lead_to_enr,
                    average_ticket_brl=ticket,
                    total_revenue_brl=revenue,
                    price_period=price_period,
                    data_complete=data_complete,
                    cohort_status=cohort_status,
                    created_at=datetime.now(UTC),
                )
                session.add(funnel_model)
                funnel_created += 1

            total_enrolled += enrolled
            total_revenue += revenue

    await session.commit()

    return {
        "tenant_id": tenant_id,
        "is_synthetic": True,
        "dataset_version": DATASET_VERSION,
        "courses_created": courses_created,
        "courses_updated": courses_updated,
        "total_courses": len(ENS_HISTORICAL_PORTFOLIO),
        "funnel_records_processed": funnel_created,
        "total_historical_enrolled": total_enrolled,
        "total_historical_revenue_brl": total_revenue,
    }
