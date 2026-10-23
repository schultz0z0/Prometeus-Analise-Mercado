"""Adaptador de decisão para LLM Tradicional (Modo Fallback / 100% Tradicional).

Permite que uma LLM Tradicional (OpenAI, ChatGPT OAuth, Claude, Gemini) execute
julgamentos do DecisionModelPort (Choice, Score, Noul) via structured outputs
quando o usuário não conecta o TypeSafe JEV.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from prometeus.domain.ports.decision_model import (
    DecisionModelPort,
    DecisionPack,
    DecisionResult,
    DecisionType,
)
from prometeus.domain.ports.generative_model import GenerativeModelPort

logger = logging.getLogger(__name__)


class LLMDecisionAdapter(DecisionModelPort):
    """Executa julgamentos estruturados usando uma LLM Tradicional como System One."""

    def __init__(self, generative_model: GenerativeModelPort) -> None:
        self.generative_model = generative_model

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrai o primeiro objeto JSON de uma resposta textual."""
        cleaned = text.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        raise ValueError("A LLM de decisão não retornou um objeto JSON válido.")

    @staticmethod
    def _required_probability(payload: dict[str, Any], key: str) -> float:
        if key not in payload:
            raise ValueError(f"A resposta estruturada da LLM não contém '{key}'.")
        value = float(payload[key])
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"'{key}' deve estar entre 0.0 e 1.0.")
        return value

    async def execute_choice(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        """Executa um julgamento do tipo Choice via prompt estruturado."""
        logger.info(
            f"[MODO TRADICIONAL] Avaliando Choice no pack '{pack.pack_id}' via LLM Tradicional"
        )
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        system_prompt = (
            "Você é um motor de decisão determinístico para produtos educacionais. "
            "Escolha a opção mais adequada com base estrita no contexto fornecido. "
            "Responda EXCLUSIVAMENTE em formato JSON com as chaves: "
            "'selected_choice' (string exatamente igual a uma das opções), "
            "'confidence' (float entre 0.0 e 1.0) e "
            "'distribution' (objeto mapeando cada opção a uma probabilidade entre 0.0 e 1.0)."
        )
        prompt = (
            f"Pergunta: {pack.question}\n"
            f"Opções disponíveis: {json.dumps(pack.options, ensure_ascii=False)}\n\n"
            f"Contexto avaliado:\n{context_str}\n"
        )
        raw = await self.generative_model.generate_text(
            prompt=prompt, system_prompt=system_prompt, temperature=0.1
        )
        parsed = self._extract_json(raw)
        if "selected_choice" not in parsed:
            raise ValueError("A resposta estruturada da LLM não contém 'selected_choice'.")
        choice = str(parsed["selected_choice"])
        if choice not in pack.options:
            raise ValueError(
                f"A LLM retornou a opção não permitida '{choice}' para o pack '{pack.pack_id}'."
            )
        confidence = self._required_probability(parsed, "confidence")
        dist_raw = parsed.get("distribution")
        if not isinstance(dist_raw, dict):
            raise ValueError("A resposta estruturada da LLM não contém 'distribution' válido.")
        dist = {str(key): float(value) for key, value in dist_raw.items()}

        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=choice,
            confidence=confidence,
            distribution=dist,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="llm-traditional",
        )

    async def execute_score(
        self,
        pack: DecisionPack,
        context: dict[str, Any],
        evidence_ids: list[str] | None = None,
    ) -> DecisionResult:
        """Executa um julgamento do tipo Score via prompt estruturado."""
        logger.info(
            f"[MODO TRADICIONAL] Avaliando Score no pack '{pack.pack_id}' via LLM Tradicional"
        )
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        system_prompt = (
            "Você é um avaliador quantitativo para validação de cursos. "
            "Atribua uma nota numérica baseando-se estritamente na rubrica e nos dados. "
            "Responda EXCLUSIVAMENTE em formato JSON com as chaves: "
            f"'score_value' (float entre {pack.min_score} e {pack.max_score}), "
            "'confidence' (float entre 0.0 e 1.0) e "
            "'requires_human_review' (boolean)."
        )
        prompt = (
            f"Critério de Avaliação: {pack.question}\n"
            f"Escala: {pack.min_score} a {pack.max_score}\n"
            f"Rubrica de Pontuação:\n{json.dumps(pack.rubric, ensure_ascii=False, indent=2)}\n\n"
            f"Contexto avaliado:\n{context_str}\n"
        )
        raw = await self.generative_model.generate_text(
            prompt=prompt, system_prompt=system_prompt, temperature=0.1
        )
        parsed = self._extract_json(raw)
        if "score_value" not in parsed:
            raise ValueError("A resposta estruturada da LLM não contém 'score_value'.")
        score = float(parsed["score_value"])
        if not pack.min_score <= score <= pack.max_score:
            raise ValueError(
                f"O score {score} está fora da escala {pack.min_score}..{pack.max_score}."
            )
        confidence = self._required_probability(parsed, "confidence")

        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=score,
            confidence=confidence,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="llm-traditional",
        )

    async def evaluate(self, pack: DecisionPack, state: dict[str, Any]) -> DecisionResult:
        """Helper compatível para despacho direto de acordo com decision_type."""
        if pack.decision_type == DecisionType.CHOICE:
            return await self.execute_choice(pack, state)
        elif pack.decision_type == DecisionType.SCORE:
            return await self.execute_score(pack, state)
        else:
            context_str = json.dumps(state, ensure_ascii=False, indent=2)
            raw = await self.generative_model.generate_text(
                prompt=f"Pergunta: {pack.question}\nContexto:\n{context_str}",
                system_prompt=(
                    "Avalie se a evidência é insuficiente ou inconclusiva. Responda somente "
                    "JSON com is_noul (boolean), confidence (0..1) e reason (string)."
                ),
                temperature=0.1,
            )
            parsed = self._extract_json(raw)
            if parsed.get("is_noul") is not True:
                raise ValueError(
                    "Um decision pack NOUL só pode produzir resultado quando is_noul=true."
                )
            self._required_probability(parsed, "confidence")
            reason = str(parsed.get("reason") or "Evidência insuficiente segundo a LLM.")
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason=reason,
                model_version="llm-traditional",
            )
