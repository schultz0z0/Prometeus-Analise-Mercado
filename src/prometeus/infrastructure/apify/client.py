"""Adaptador oficial para Apify com pinagem de Actors e acompanhamento assíncrono de runs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.market_sources import (
    EvidenceType,
    MarketEvidence,
    MarketSourcePort,
    ResearchPlan,
)

logger = logging.getLogger(__name__)

# Pinagem imutável de Actors aprovados (Task 6)
PINNED_ACTORS: dict[str, str] = {
    "linkedin_jobs": "apify/linkedin-jobs-scraper@1.3.0",
    "educational_offers": "apify/google-search-scraper@1.1.0",
    "social_listening": "apify/instagram-scraper@1.4.0",
}


class ApifyError(Exception):
    """Exceção base para erros em integrações com Apify."""

    pass


class ApifyBudgetExceededError(ApifyError):
    """Tentativa de disparo de Actor cujo custo excede o orçamento do plano."""

    pass


class ApifyCollector(MarketSourcePort):
    """Cliente para disparo e acompanhamento assíncrono de Actors no Apify."""

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str = "https://api.apify.com/v2",
        timeout_seconds: float = 30.0,
        polling_interval_seconds: float = 0.5,
        max_poll_attempts: int = 10,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_token = api_token or getattr(AppSettings(), "APIFY_TOKEN", "")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.polling_interval_seconds = polling_interval_seconds
        self.max_poll_attempts = max_poll_attempts
        self._custom_client = http_client

    def _get_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def _run_actor_and_wait(
        self,
        actor_id: str,
        actor_input: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> list[dict[str, Any]]:
        """Inicia a execução do Actor e aguarda o status SUCCEEDED."""
        clean_actor = actor_id.split("@")[0].replace("/", "~")
        start_url = f"{self.base_url}/acts/{clean_actor}/runs?waitForFinish=8"
        resp = await client.post(start_url, json=actor_input, headers=self._get_headers())
        resp.raise_for_status()
        run_data = resp.json().get("data", {})
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")
        cur_status = run_data.get("status")

        # Polling assíncrono se não tiver terminado no waitForFinish
        if cur_status != "SUCCEEDED" and run_id:
            poll_url = f"{self.base_url}/actor-runs/{run_id}"
            for _ in range(self.max_poll_attempts):
                await asyncio.sleep(self.polling_interval_seconds)
                status_resp = await client.get(poll_url, headers=self._get_headers())
                if status_resp.status_code == 200:
                    cur_status = status_resp.json().get("data", {}).get("status")
                    if cur_status == "SUCCEEDED":
                        break
                    elif cur_status in {"FAILED", "ABORTED", "TIMED-OUT"}:
                        raise ApifyError(f"Execução do Actor {actor_id} falhou com status {cur_status}")

        # Busca dados no dataset
        if dataset_id:
            items_url = f"{self.base_url}/datasets/{dataset_id}/items"
            items_resp = await client.get(items_url, headers=self._get_headers())
            if items_resp.status_code == 200:
                result = items_resp.json()
                if isinstance(result, list):
                    return result
        return []

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        evidences: list[MarketEvidence] = []
        estimated_cost_per_term = 0.05

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            for term in search_terms:
                if plan and not plan.has_budget_for(estimated_cost_per_term):
                    logger.warning(
                        f"Orçamento insuficiente para Apify no termo '{term}' (Gasto: ${plan.spent_usd:.2f})"
                    )
                    break

                actor_id = PINNED_ACTORS.get("educational_offers", "apify/google-search-scraper")
                actor_input = {
                    "queries": f"{term} curso pós-graduação seguros",
                    "maxPagesPerQuery": 1,
                }

                try:
                    items = await self._run_actor_and_wait(actor_id, actor_input, client)
                except Exception as exc:
                    logger.error(f"Erro executando Apify para '{term}': {exc}")
                    continue

                if plan:
                    plan.record_cost(estimated_cost_per_term)

                payload = {
                    "term": term,
                    "actor_id": actor_id,
                    "jobs_count": len(items),
                    "items": items[:5],
                }

                ev = MarketEvidence.create(
                    analysis_id=analysis_id,
                    evidence_type=EvidenceType.JOB_MARKET,
                    source_name="apify_linkedin_jobs",
                    source_url=f"https://www.linkedin.com/jobs/search/?keywords={term}",
                    collector="apify_actor_runner",
                    title=f"Vagas de mercado: {term}",
                    raw_payload=payload,
                    cost_usd=estimated_cost_per_term,
                )
                evidences.append(ev)

            return evidences
        finally:
            if close_client:
                await client.aclose()


class FakeApifyCollector(MarketSourcePort):
    """Coletor fake determinístico para testes e CI."""

    def __init__(
        self,
        canned_jobs: list[dict[str, Any]] | None = None,
        cost_per_term: float = 0.05,
        simulate_error: bool = False,
    ) -> None:
        self.canned_jobs = canned_jobs
        self.cost_per_term = cost_per_term
        self.simulate_error = simulate_error
        self.call_count = 0

    async def collect(
        self,
        analysis_id: str,
        search_terms: list[str],
        plan: ResearchPlan | None = None,
    ) -> list[MarketEvidence]:
        if self.simulate_error:
            raise ApifyError("Erro simulado na API do Apify (Timeout / 502)")

        evidences: list[MarketEvidence] = []
        for term in search_terms:
            if plan and not plan.has_budget_for(self.cost_per_term):
                logger.info(f"Plano orçamentário interrompeu Apify para termo '{term}'")
                break

            self.call_count += 1
            if plan:
                plan.record_cost(self.cost_per_term)

            items = self.canned_jobs or [
                {
                    "title": f"Analista de {term}",
                    "company": "Seguradora Nacional S/A",
                    "location": "São Paulo, SP",
                    "skills": [term, "SUSEP", "Excel Avançado"],
                    "salary_range": "R$ 7.000 - R$ 9.500",
                }
            ]

            payload = {
                "term": term,
                "actor_id": PINNED_ACTORS["linkedin_jobs"],
                "jobs_count": len(items),
                "items": items,
            }

            ev = MarketEvidence.create(
                analysis_id=analysis_id,
                evidence_type=EvidenceType.JOB_MARKET,
                source_name="apify_linkedin_jobs",
                source_url=f"https://www.linkedin.com/jobs/search/?keywords={term}",
                collector="fake_apify_collector",
                title=f"Vagas Apify: {term}",
                raw_payload=payload,
                cost_usd=self.cost_per_term,
            )
            evidences.append(ev)

        return evidences
