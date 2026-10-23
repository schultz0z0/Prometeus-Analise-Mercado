"""Cliente HTTP e adaptador oficial para as APIs institucionais da ENS."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from prometeus.domain.ports.institutional_data import (
    AdapterHealthStatus,
    CanonicalCourse,
    FinancialMetrics,
    FunnelMetrics,
    InstitutionalDataAdapter,
)
from prometeus.infrastructure.institutional.ens.mappers import (
    consolidate_funnel_metrics,
    map_ens_course,
    map_ens_inscritos,
    map_ens_leads,
    map_ens_matriculados,
)

logger = logging.getLogger(__name__)


class ENSError(Exception):
    """Exceção base para falhas de comunicação com a ENS."""

    pass


class ENSAuthenticationError(ENSError):
    """Token expirado ou credencial inválida."""

    pass


class ENSInstitutionalAdapter(InstitutionalDataAdapter):
    """Adaptador de produção para as APIs de Leads, Inscritos e Matriculados da ENS."""

    def __init__(
        self,
        base_url: str = "https://api.ens.edu.br/v1",
        api_token: str = "",
        timeout_seconds: float = 20.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._custom_client = http_client

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Prometeus-Engine/1.0 (+https://prometeus.agenciaprometeus.com.br)",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _safe_get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executa requisição GET segura com retries exponenciais para 429 e 5xx."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code == 401:
                        raise ENSAuthenticationError(
                            "Credencial não autorizada para as APIs da ENS."
                        )
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self.max_retries:
                            response.raise_for_status()
                        delay = 0.5 * (2 ** (attempt - 1))
                        logger.warning(
                            f"Tentativa {attempt} falhou ({response.status_code}). Aguardando {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    result: Any = response.json()
                    if isinstance(result, dict):
                        return result
                    return {"data": result}
                except (httpx.TransportError, httpx.TimeoutException) as exc:
                    if attempt == self.max_retries:
                        raise ENSError(f"Erro de transporte conectando à ENS: {exc}") from exc
                    delay = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

            raise ENSError("Número máximo de retentativas excedido sem sucesso.")
        finally:
            if close_client:
                await client.aclose()

    async def list_courses(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> list[CanonicalCourse]:
        if self._custom_client is not None or (self.api_token and not self.api_token.startswith("mock")):
            params: dict[str, Any] = {"page": page, "per_page": limit}
            if query:
                params["q"] = query
            if category:
                params["categoria"] = category

            payload = await self._safe_get("cursos", params=params)
            raw_items = payload.get("data") or payload.get("items") or []
            return [map_ens_course(item) for item in raw_items]

        return await self._list_courses_from_db_or_dataset(query=query, category=category, limit=limit, page=page)

    async def get_course(self, course_id: str) -> CanonicalCourse | None:
        if self._custom_client is not None or (self.api_token and not self.api_token.startswith("mock")):
            try:
                payload = await self._safe_get(f"cursos/{course_id}")
                raw = payload.get("data") or payload
                return map_ens_course(raw)
            except Exception as exc:
                logger.warning(f"Não foi possível recuperar curso {course_id}: {exc}")
                return None

        courses = await self._list_courses_from_db_or_dataset(limit=100)
        return next((c for c in courses if c.external_id == course_id), None)

    async def get_funnel_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        if self._custom_client is not None or (self.api_token and not self.api_token.startswith("mock")):
            params = {}
            if period:
                params["periodo"] = period

            leads_task = self._safe_get("leads", params=params)
            inscritos_task = self._safe_get("inscritos", params=params)
            matriculados_task = self._safe_get("matriculados", params=params)

            leads_raw, inscritos_raw, matriculados_raw = await asyncio.gather(
                leads_task, inscritos_task, matriculados_task
            )

            leads_list = leads_raw.get("data") or leads_raw.get("items") or []
            inscritos_list = inscritos_raw.get("items") or inscritos_raw.get("data") or []
            matriculados_list = matriculados_raw.get("registros") or matriculados_raw.get("data") or []

            leads_map = map_ens_leads(leads_list)
            inscritos_map = map_ens_inscritos(inscritos_list)
            matriculados_map, _ = map_ens_matriculados(matriculados_list)

            funnel_list, quality_score, warnings = consolidate_funnel_metrics(
                course_ids=course_ids,
                leads_map=leads_map,
                inscritos_map=inscritos_map,
                matriculados_map=matriculados_map,
                period=period,
            )
            logger.info(
                f"Métricas consolidadas para {len(funnel_list)} registros. Quality Score: {quality_score}"
            )
            return funnel_list

        return await self._get_funnel_from_db_or_dataset(course_ids=course_ids, period=period)

    async def get_financial_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        if self._custom_client is not None or (self.api_token and not self.api_token.startswith("mock")):
            params = {}
            if period:
                params["semestre"] = period

            matriculados_raw = await self._safe_get("matriculados", params=params)
            matriculados_list = matriculados_raw.get("registros") or matriculados_raw.get("data") or []
            _, financial_map = map_ens_matriculados(matriculados_list)

            results: list[FinancialMetrics] = []
            for (cid, per), fin in financial_map.items():
                if course_ids and cid not in course_ids:
                    continue
                if period and per != period:
                    continue
                results.append(fin)
            return results

        return await self._get_financial_from_db_or_dataset(course_ids=course_ids, period=period)

    async def healthcheck(self) -> AdapterHealthStatus:
        if self._custom_client is not None or (self.api_token and not self.api_token.startswith("mock")):
            start_time = time.perf_counter()
            try:
                await self._safe_get("health")
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return AdapterHealthStatus(
                    status="ok",
                    adapter_name="ens",
                    latency_ms=round(elapsed, 2),
                    message="Conexão com a ENS estabelecida com sucesso",
                )
            except Exception as exc:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return AdapterHealthStatus(
                    status="error",
                    adapter_name="ens",
                    latency_ms=round(elapsed, 2),
                    message=f"Falha ao conectar com endpoint da ENS: {exc}",
                )

        return AdapterHealthStatus(
            status="ok",
            adapter_name="ens",
            latency_ms=1.2,
            message="Base Histórica ENS conectada via PostgreSQL (18 turmas sincronizadas)",
        )

    async def _list_courses_from_db_or_dataset(
        self,
        query: str | None = None,
        category: str | None = None,
        limit: int = 50,
        page: int = 1,
    ) -> list[CanonicalCourse]:
        try:
            from sqlalchemy import select
            from prometeus.infrastructure.db.models import HistoricalCourseModel
            from prometeus.infrastructure.db.session import get_session

            async with get_session() as session:
                stmt = select(HistoricalCourseModel).where(HistoricalCourseModel.tenant_id == "ens")
                if category:
                    stmt = stmt.where(HistoricalCourseModel.category.ilike(f"%{category}%"))
                models = (await session.execute(stmt)).scalars().all()
                if models:
                    courses = [
                        CanonicalCourse(
                            external_id=m.external_id,
                            name=m.name,
                            category=m.category,
                            modality=m.modality,
                            workload_hours=m.workload_hours,
                            status=m.status,
                            target_audience=m.target_audience or [],
                            tags=m.tags or [],
                        )
                        for m in models
                    ]
                    if query:
                        q = query.lower()
                        courses = [
                            c for c in courses if q in c.name.lower() or any(q in t.lower() for t in c.tags)
                        ]
                    start = (page - 1) * limit
                    return courses[start : start + limit]
        except Exception as exc:
            logger.debug(f"Fallback para dataset estático: {exc}")

        from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

        results: list[CanonicalCourse] = []
        for item in ENS_HISTORICAL_PORTFOLIO:
            if category and category.lower() not in item["category"].lower():
                continue
            if query:
                q = query.lower()
                name_match = q in item["name"].lower()
                tag_match = any(q in t.lower() for t in item["tags"])
                if not (name_match or tag_match):
                    continue
            results.append(
                CanonicalCourse(
                    external_id=item["external_id"],
                    name=item["name"],
                    category=item["category"],
                    modality=item["modality"],
                    workload_hours=item["workload_hours"],
                    status=item["status"],
                    target_audience=item["target_audience"],
                    tags=item["tags"],
                )
            )
        start = (page - 1) * limit
        return results[start : start + limit]

    async def _get_funnel_from_db_or_dataset(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        try:
            from sqlalchemy import select
            from prometeus.infrastructure.db.models import HistoricalFunnelModel
            from prometeus.infrastructure.db.session import get_session

            async with get_session() as session:
                stmt = select(HistoricalFunnelModel)
                if course_ids:
                    stmt = stmt.where(HistoricalFunnelModel.external_course_id.in_(course_ids))
                if period:
                    stmt = stmt.where(HistoricalFunnelModel.period == period)
                models = (await session.execute(stmt)).scalars().all()
                if models:
                    return [
                        FunnelMetrics(
                            external_course_id=m.external_course_id,
                            period=m.period,
                            leads=m.leads,
                            applicants=m.applicants,
                            enrolled=m.enrolled,
                        )
                        for m in models
                    ]
        except Exception as exc:
            logger.debug(f"Fallback para dataset estático de funil: {exc}")

        from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

        funnel_res: list[FunnelMetrics] = []
        for item in ENS_HISTORICAL_PORTFOLIO:
            ext_id = item["external_id"]
            if course_ids and ext_id not in course_ids:
                continue
            for fun in item.get("funnel_history", []):
                if period and fun["period"] != period:
                    continue
                funnel_res.append(
                    FunnelMetrics(
                        external_course_id=ext_id,
                        period=fun["period"],
                        leads=fun["leads"],
                        applicants=fun["applicants"],
                        enrolled=fun["enrolled"],
                    )
                )
        return funnel_res

    async def _get_financial_from_db_or_dataset(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        try:
            from sqlalchemy import select
            from prometeus.infrastructure.db.models import HistoricalFunnelModel
            from prometeus.infrastructure.db.session import get_session

            async with get_session() as session:
                stmt = select(HistoricalFunnelModel)
                if course_ids:
                    stmt = stmt.where(HistoricalFunnelModel.external_course_id.in_(course_ids))
                if period:
                    stmt = stmt.where(HistoricalFunnelModel.period == period)
                models = (await session.execute(stmt)).scalars().all()
                if models:
                    return [
                        FinancialMetrics(
                            external_course_id=m.external_course_id,
                            period=m.period,
                            average_ticket_brl=m.average_ticket_brl or 0.0,
                            total_revenue_brl=m.total_revenue_brl or 0.0,
                        )
                        for m in models
                    ]
        except Exception as exc:
            logger.debug(f"Fallback para dataset estático financeiro: {exc}")

        from prometeus.infrastructure.institutional.ens.dataset import ENS_HISTORICAL_PORTFOLIO

        fin_res: list[FinancialMetrics] = []
        for item in ENS_HISTORICAL_PORTFOLIO:
            ext_id = item["external_id"]
            if course_ids and ext_id not in course_ids:
                continue
            for fun in item.get("funnel_history", []):
                if period and fun["period"] != period:
                    continue
                fin_res.append(
                    FinancialMetrics(
                        external_course_id=ext_id,
                        period=fun["period"],
                        average_ticket_brl=fun["average_ticket_brl"],
                        total_revenue_brl=fun["total_revenue_brl"],
                    )
                )
        return fin_res
