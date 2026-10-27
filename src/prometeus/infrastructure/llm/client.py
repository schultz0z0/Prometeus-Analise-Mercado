"""Cliente HTTP para modelos generativos com suporte a prompts versionados."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
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
from prometeus.infrastructure.llm.codex_oauth import (
    ChatGPTCredentialStore,
    refresh_chatgpt_tokens,
)

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
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float = 20.0,
        http_client: httpx.AsyncClient | None = None,
        prompts_dir: Path | str = PROMPTS_DIR,
    ) -> None:
        settings = AppSettings()
        effective_key = api_key or settings.OPENAI_API_KEY

        self.base_url = (
            base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = effective_key
        self.model = model or settings.GEN_LLM_MODEL or "gpt-4o-mini"
        self.reasoning_effort = reasoning_effort or getattr(
            settings, "GEN_LLM_REASONING_EFFORT", ""
        )
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

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        # Modelos com raciocínio (ex.: Codex GPT-6 Astra, GPT-6.1 Sol, GPT-5.6 Sol/Terra/Luna ou o1/o3)
        # usam reasoning_effort e rejeitam o parâmetro 'temperature' na API da OpenAI.
        effort = (self.reasoning_effort or "").strip().lower()
        if effort and effort != "none":
            payload["reasoning_effort"] = effort
        else:
            payload["temperature"] = temperature

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
            "course_understanding": facts.course_understanding,
            "research_plan": facts.research_plan,
            "counterevidence": facts.counterevidence,
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
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, list) or not raw_sections:
            raise GenerativeModelError("A resposta do modelo não contém sections válidas")
        sections: list[DossierSection] = []
        for s in raw_sections:
            if not isinstance(s, dict):
                raise GenerativeModelError("Cada section deve ser um objeto JSON")
            required_section_fields = {
                "section_id",
                "title",
                "target_audience",
                "content",
                "claim_ids",
            }
            if not required_section_fields.issubset(s):
                raise GenerativeModelError("Section sem campos obrigatórios")
            sections.append(
                DossierSection(
                    section_id=str(s["section_id"]),
                    title=str(s["title"]),
                    target_audience=str(s["target_audience"]),
                    content=str(s["content"]),
                    claim_ids=[str(cid) for cid in s["claim_ids"]],
                )
            )

        # Parse claims
        raw_claims = data.get("claims")
        if not isinstance(raw_claims, list) or not raw_claims:
            raise GenerativeModelError("A resposta do modelo não contém claims válidas")
        claims: list[DossierClaim] = []
        for c in raw_claims:
            if not isinstance(c, dict):
                raise GenerativeModelError("Cada claim deve ser um objeto JSON")
            required_claim_fields = {
                "claim_id",
                "statement",
                "claim_type",
                "evidence_ids",
                "support_level",
            }
            if not required_claim_fields.issubset(c):
                raise GenerativeModelError("Claim sem campos obrigatórios")
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
                    claim_id=str(c["claim_id"]),
                    statement=str(c["statement"]),
                    claim_type=claim_type,
                    evidence_ids=[str(eid) for eid in c["evidence_ids"]],
                    support_level=support_level,
                    verification_status=VerificationStatus.PENDING,
                )
            )

        exec_summary = data.get("executive_summary")
        if not isinstance(exec_summary, str) or not exec_summary.strip():
            raise GenerativeModelError("A resposta do modelo não contém executive_summary válido")

        return DossierOutput(
            analysis_id=facts.analysis_id,
            prompt_version=prompt_version,
            model_name=self.model,
            executive_summary=exec_summary,
            sections=sections,
            claims=claims,
            facts_hash=facts.compute_facts_hash(),
            status=DossierStatus.DRAFT,
            cost_usd=0.0,
        )


class ChatGPTPlanGenerativeClient(OpenAIGenerativeClient):
    """Responses API com token OAuth autorizado a consumir o plano ChatGPT."""

    def __init__(
        self,
        *,
        access_token: str,
        model: str,
        reasoning_effort: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
        prompts_dir: Path | str = PROMPTS_DIR,
        credential_store: ChatGPTCredentialStore | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=access_token,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds,
            http_client=http_client,
            prompts_dir=prompts_dir,
        )
        self.credential_store = credential_store
        self._refresh_lock = asyncio.Lock()

    async def _ensure_fresh_access_token(self) -> None:
        if self.credential_store is None:
            return
        async with self._refresh_lock:
            credentials = self.credential_store.load()
            if credentials is None:
                raise GenerativeModelError("Credenciais OAuth locais ausentes ou inválidas.")
            self.model = credentials.selected_model
            if credentials.expires_at > time.time() + 60:
                self.api_key = credentials.access_token
                return
            try:
                refreshed = await refresh_chatgpt_tokens(
                    credentials,
                    http_client=self._custom_client,
                )
            except Exception as exc:
                raise GenerativeModelError(
                    f"Não foi possível renovar a sessão ChatGPT OAuth: {exc}"
                ) from exc
            self.credential_store.save(refreshed)
            self.api_key = refreshed.access_token

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        del temperature  # O fluxo de compartilhamento não aceita temperature.
        await self._ensure_fresh_access_token()
        payload: dict[str, Any] = {
            "model": self.model,
            "input": [{"role": "user", "content": prompt}],
            "store": False,
            "stream": True,
        }
        if system_prompt:
            payload["instructions"] = system_prompt
        effort = (self.reasoning_effort or "").strip().lower()
        if effort and effort != "none":
            payload["reasoning"] = {"effort": effort}

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None
        completed = False
        chunks: list[str] = []
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/responses",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if not raw or raw == "[DONE]":
                        continue
                    event = json.loads(raw)
                    event_type = event.get("type")
                    if event_type == "response.output_text.delta":
                        delta = event.get("delta")
                        if isinstance(delta, str):
                            chunks.append(delta)
                    elif event_type == "response.completed":
                        completed = True
                    elif event_type in {"response.failed", "response.incomplete", "error"}:
                        error = event.get("error") or event.get("response", {}).get("error") or {}
                        code = (
                            error.get("code", event_type) if isinstance(error, dict) else event_type
                        )
                        raise GenerativeModelError(f"Inferência via plano ChatGPT falhou: {code}")
            if not completed:
                raise GenerativeModelError(
                    "Stream do plano ChatGPT terminou sem response.completed."
                )
            text = "".join(chunks).strip()
            if not text:
                raise GenerativeModelError("A inferência concluída retornou texto vazio.")
            return text
        except GenerativeModelError:
            raise
        except Exception as exc:
            raise GenerativeModelError(f"Falha de execução via plano ChatGPT: {exc}") from exc
        finally:
            if close_client:
                await client.aclose()
