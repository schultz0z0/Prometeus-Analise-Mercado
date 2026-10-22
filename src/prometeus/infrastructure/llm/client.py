"""Cliente HTTP para modelos generativos com suporte a prompts versionados."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from prometeus.domain.configuration import AppSettings
from prometeus.domain.dossiers import (
    ClaimType,
    DossierClaim,
    DossierFacts,
    DossierOutput,
    DossierSection,
    DossierStatus,
    SupportLevel,
    VerificationStatus,
)
from prometeus.domain.ports.generative_model import GenerativeModelPort

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path("config/prompts")


class GenerativeModelError(Exception):
    """Exceção base para erros em chamadas a modelos generativos."""

    pass


class OpenAIGenerativeClient(GenerativeModelPort):
    """Cliente generativo compatível com a API OpenAI / OpenRouter."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 20.0,
        http_client: httpx.AsyncClient | None = None,
        prompts_dir: Path | str = PROMPTS_DIR,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or getattr(AppSettings(), "OPENAI_API_KEY", "")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._custom_client = http_client
        self.prompts_dir = Path(prompts_dir)

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _extract_json_array(self, text: str) -> list[str]:
        """Extrai um array JSON mesmo que a resposta venha envolvida em crases ou markdown."""
        cleaned = text.strip()
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        # Fallback de quebra por linhas
        lines = [line.strip().lstrip("-*1234567890. ") for line in cleaned.split("\n")]
        return [line for line in lines if line and not line.startswith("```")]

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            response = await client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            content: str = data["choices"][0]["message"]["content"]
            return content
        except Exception as exc:
            logger.error(f"Erro na chamada da LLM generativa: {exc}")
            raise GenerativeModelError(f"Falha de execução do modelo generativo: {exc}") from exc
        finally:
            if close_client:
                await client.aclose()

    async def generate_keyword_candidates(
        self,
        course_title: str,
        description: str,
        target_audience: str,
        max_candidates: int = 15,
    ) -> list[str]:
        prompt_file = self.prompts_dir / "keyword-candidates-v1.yaml"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_file}")

        with prompt_file.open("r", encoding="utf-8") as f:
            prompt_cfg: Any = yaml.safe_load(f)

        system_prompt = str(prompt_cfg.get("system_prompt", ""))
        user_template = str(prompt_cfg.get("user_template", ""))

        user_prompt = user_template.format(
            course_title=course_title,
            description=description,
            target_audience=target_audience,
            max_candidates=max_candidates,
        )

        response_text = await self.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )

        candidates = self._extract_json_array(response_text)
        return candidates[:max_candidates]

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        """Extrai um objeto JSON ({...}) tratando markdown codeblocks ou preâmbulos."""
        cleaned = text.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        raise GenerativeModelError(
            f"A resposta do modelo não contém um objeto JSON válido: {cleaned[:200]}"
        )

    async def synthesize_dossier(
        self,
        facts: DossierFacts,
        prompt_version: str = "dossier-v1",
    ) -> DossierOutput:
        """Sintetiza dossiê executivo estruturado a partir de fatos aprovados (TOOL-14)."""
        prompt_file = self.prompts_dir / f"{prompt_version}.yaml"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_file}")

        with prompt_file.open("r", encoding="utf-8") as f:
            prompt_cfg: Any = yaml.safe_load(f)

        system_prompt = str(prompt_cfg.get("system_prompt", ""))
        user_template = str(prompt_cfg.get("user_template", ""))

        facts_payload = {
            "analysis_id": facts.analysis_id,
            "course_name": facts.course_name,
            "target_audience": facts.target_audience,
            "recommendation": facts.recommendation,
            "viability_score": round(facts.viability_score, 2),
            "coverage_score": round(facts.coverage_score, 4),
            "confidence_score": round(facts.confidence_score, 4),
            "pillar_summaries": facts.pillar_summaries,
            "facts": [item.to_dict() for item in facts.items],
            "limitations": facts.limitations,
        }
        facts_json = json.dumps(facts_payload, ensure_ascii=False, indent=2)

        user_prompt = user_template.format(
            course_name=facts.course_name,
            facts_json=facts_json,
        )

        response_text = await self.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )

        data = self._extract_json_object(response_text)

        # Parse sections
        raw_sections = data.get("sections", [])
        sections: list[DossierSection] = []
        for s in raw_sections:
            sections.append(
                DossierSection(
                    section_id=str(s.get("section_id", f"sec_{len(sections) + 1}")),
                    title=str(s.get("title", "Seção Analítica")),
                    target_audience=str(s.get("target_audience", "executive")),
                    content=str(s.get("content", "")),
                    claim_ids=[str(cid) for cid in s.get("claim_ids", [])],
                )
            )

        # Parse claims
        raw_claims = data.get("claims", [])
        claims: list[DossierClaim] = []
        for c in raw_claims:
            claim_type_str = str(c.get("claim_type", "qualitative")).lower()
            claim_type = (
                ClaimType.QUANTITATIVE
                if claim_type_str == "quantitative"
                else (
                    ClaimType.STRATEGIC if claim_type_str == "strategic" else ClaimType.QUALITATIVE
                )
            )

            support_level_str = str(c.get("support_level", "observed")).lower()
            support_level = (
                SupportLevel.OBSERVED
                if support_level_str == "observed"
                else (
                    SupportLevel.SUGGESTIVE
                    if support_level_str == "suggestive"
                    else SupportLevel.HYPOTHESIS
                )
            )

            claims.append(
                DossierClaim(
                    claim_id=str(c.get("claim_id", f"CLM-{len(claims) + 1:02d}")),
                    statement=str(c.get("statement", "")),
                    claim_type=claim_type,
                    evidence_ids=[str(eid) for eid in c.get("evidence_ids", [])],
                    support_level=support_level,
                    verification_status=VerificationStatus.VERIFIED,
                )
            )

        # Fallback de executive summary
        exec_summary = str(data.get("executive_summary", ""))
        if not exec_summary and sections:
            exec_summary = sections[0].content

        return DossierOutput(
            analysis_id=facts.analysis_id,
            prompt_version=prompt_version,
            model_name=self.model,
            executive_summary=exec_summary,
            sections=sections,
            claims=claims,
            facts_hash=facts.compute_facts_hash(),
            status=DossierStatus.VERIFIED,
            cost_usd=0.005,  # Estimativa de custo por geração
        )
