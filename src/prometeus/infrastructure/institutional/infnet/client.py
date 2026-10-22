"""Cliente HTTP e adaptador institucional para as APIs do Instituto Infnet (Fase 09 White-label)."""

from __future__ import annotations

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
from prometeus.infrastructure.institutional.infnet.mappers import (
    map_infnet_course,
    map_infnet_financial,
    map_infnet_funnel,
)

logger = logging.getLogger(__name__)


class InfnetError(Exception):
    """Exceção base para falhas de comunicação com as APIs do Infnet."""

    pass


class InfnetAuthenticationError(InfnetError):
    """Credencial inválida ou token expirado na API do Infnet."""

    pass


class InfnetInstitutionalAdapter(InstitutionalDataAdapter):
    """Adaptador de produção para as APIs acadêmicas e de captação do Instituto Infnet."""

    def __init__(
        self,
        base_url: str = "https://api.infnet.edu.br/v1",
        api_token: str = "",
        timeout_seconds: float = 15.0,
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
            "User-Agent": "Prometeus-Market-Intelligence/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = await client.request(
                        method=method,
                        url=url,
                        headers=self._get_headers(),
                        params=params,
                    )
                    if resp.status_code == 401:
                        raise InfnetAuthenticationError(
                            "Falha de autenticação com a API do Infnet (HTTP 401)."
                        )
                    if resp.status_code == 404:
                        return None
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == self.max_retries:
                        raise InfnetError(
                            f"Falha de rede ao conectar à API do Infnet após {self.max_retries} tentativas: {exc}"
                        ) from exc
                    logger.warning(f"Tentativa {attempt} falhou para {url}: {exc}. Reexecutando...")
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
        params: dict[str, Any] = {"limit": limit, "page": page}
        if query:
            params["busca"] = query
        if category:
            params["escola"] = category

        data = await self._request("GET", "/cursos", params=params)
        if not data:
            return []

        items = data if isinstance(data, list) else data.get("items", [])
        return [map_infnet_course(item) for item in items]

    async def get_course(self, course_id: str) -> CanonicalCourse | None:
        data = await self._request("GET", f"/cursos/{course_id}")
        if not data:
            return None
        return map_infnet_course(data)

    async def get_funnel_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FunnelMetrics]:
        params: dict[str, Any] = {"cursos": ",".join(course_ids)}
        if period:
            params["semestre"] = period

        data = await self._request("GET", "/metricas/funil", params=params)
        if not data:
            return []

        items = data if isinstance(data, list) else data.get("metricas", [])
        return [map_infnet_funnel(item) for item in items]

    async def get_financial_metrics(
        self,
        course_ids: list[str],
        period: str | None = None,
    ) -> list[FinancialMetrics]:
        params: dict[str, Any] = {"cursos": ",".join(course_ids)}
        if period:
            params["semestre"] = period

        data = await self._request("GET", "/metricas/financeiro", params=params)
        if not data:
            return []

        items = data if isinstance(data, list) else data.get("financeiro", [])
        return [map_infnet_financial(item) for item in items]

    async def healthcheck(self) -> AdapterHealthStatus:
        start_time = time.time()
        try:
            resp = await self._request("GET", "/health")
            latency_ms = (time.time() - start_time) * 1000.0
            status_str = (
                "ok" if resp and resp.get("status") in ("UP", "ok", "healthy") else "degraded"
            )
            return AdapterHealthStatus(
                status=status_str,
                adapter_name="infnet",
                latency_ms=round(latency_ms, 2),
                message="Conexão com a API Infnet estabelecida com sucesso.",
            )
        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000.0
            return AdapterHealthStatus(
                status="error",
                adapter_name="infnet",
                latency_ms=round(latency_ms, 2),
                message=f"Falha de comunicação com a API Infnet: {exc}",
            )
