"""Cliente HTTP para a API TypeSafe AI / JEV (Judgment Execution Vector)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
)

logger = logging.getLogger(__name__)


class JEVError(Exception):
    """Exceção base para erros na integração com o JEV."""

    pass


class JEVServiceUnavailableError(JEVError):
    """JEV fora do ar ou inacessível após retentativas (aciona estado BLOCKED no ADR-0003)."""

    pass


class TypeSafeJEVClient(DecisionModelPort):
    """Cliente oficial de integração com o motor determinístico TypeSafe AI."""

    def __init__(
        self,
        base_url: str = "https://api.typesafe.ai/v1",
        api_key: str | None = None,
        model: str = "jev-2026.1",
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or AppSettings().TYPESAFE_API_KEY
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._custom_client = http_client

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Prometeus-Engine/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _post_with_retry(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self.max_retries:
                            raise JEVServiceUnavailableError(
                                f"TypeSafe JEV indisponível após {attempt} tentativas (HTTP {response.status_code})."
                            )
                        delay = 0.5 * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    result: Any = response.json()
                    if isinstance(result, dict):
                        return result
                    return {"result": result}
                except (httpx.TransportError, httpx.TimeoutException) as exc:
                    if attempt == self.max_retries:
                        raise JEVServiceUnavailableError(
                            f"Falha de transporte conectando ao JEV: {exc}"
                        ) from exc
                    delay = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

            raise JEVServiceUnavailableError("Número máximo de retries excedido para o JEV.")
        finally:
            if close_client:
                await client.aclose()

    async def execute_choice(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        payload = {
            "model": self.model,
            "pack_id": pack.pack_id,
            "question": pack.question,
            "options": pack.options,
            "context": context,
        }

        try:
            data = await self._post_with_retry("judgments/choice", payload)
        except Exception as exc:
            logger.error(f"Erro executando choice no JEV pack {pack.pack_id}: {exc}")
            raise

        if data.get("is_noul") or data.get("status") == "NOUL":
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason=data.get("reason", "Evidência insuficiente declarada pelo JEV"),
                evidence_ids=evidence_ids,
                model_version=self.model,
            )

        selected = str(data.get("selected") or data.get("choice") or pack.options[0])
        confidence = float(data.get("confidence", 0.0))
        dist = data.get("distribution") or {}

        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=selected,
            confidence=confidence,
            distribution=dist,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version=self.model,
        )

    async def execute_score(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        payload = {
            "model": self.model,
            "pack_id": pack.pack_id,
            "question": pack.question,
            "min_score": pack.min_score,
            "max_score": pack.max_score,
            "context": context,
        }

        try:
            data = await self._post_with_retry("judgments/score", payload)
        except Exception as exc:
            logger.error(f"Erro executando score no JEV pack {pack.pack_id}: {exc}")
            raise

        if data.get("is_noul") or data.get("status") == "NOUL":
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason=data.get("reason", "Evidência insuficiente para julgamento numérico"),
                evidence_ids=evidence_ids,
                model_version=self.model,
            )

        value = float(data.get("score") or data.get("value") or 0.0)
        confidence = float(data.get("confidence", 0.0))

        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=value,
            confidence=confidence,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version=self.model,
        )

    async def healthcheck(self) -> dict[str, Any]:
        start_time = time.perf_counter()
        try:
            payload = {"model": self.model, "ping": True}
            await self._post_with_retry("health", payload)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "ok",
                "model": self.model,
                "latency_ms": round(elapsed, 2),
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "error",
                "model": self.model,
                "latency_ms": round(elapsed, 2),
                "error": str(exc),
            }
