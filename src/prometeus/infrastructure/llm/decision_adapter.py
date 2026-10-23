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
        return {}

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
        choice = str(parsed.get("selected_choice") or (pack.options[0] if pack.options else "NONE"))
        confidence = float(parsed.get("confidence", 0.85))
        dist = parsed.get("distribution") or ({choice: 1.0} if choice else {})

        return DecisionResult.choice(
            pack_id=pack.pack_id,
            selected=choice,
            confidence=confidence,
            distribution=dist,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="llm-traditional-fallback",
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
        score = float(parsed.get("score_value", (pack.min_score + pack.max_score) / 2))
        score = max(pack.min_score, min(pack.max_score, score))
        confidence = float(parsed.get("confidence", 0.85))

        return DecisionResult.score(
            pack_id=pack.pack_id,
            value=score,
            confidence=confidence,
            review_threshold=pack.review_threshold,
            evidence_ids=evidence_ids,
            model_version="llm-traditional-fallback",
        )

    async def evaluate(self, pack: DecisionPack, state: dict[str, Any]) -> DecisionResult:
        """Helper compatível para despacho direto de acordo com decision_type."""
        if pack.decision_type == DecisionType.CHOICE:
            return await self.execute_choice(pack, state)
        elif pack.decision_type == DecisionType.SCORE:
            return await self.execute_score(pack, state)
        else:
            # NOUL
            return DecisionResult.noul(
                pack_id=pack.pack_id,
                reason="Proposição avaliada como Noul via LLM",
                model_version="llm-traditional-fallback",
            )
