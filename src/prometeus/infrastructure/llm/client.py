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
