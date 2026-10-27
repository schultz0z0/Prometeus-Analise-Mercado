"""Planejamento de pesquisa guiado por LLM e validado por política determinística."""

from __future__ import annotations

import json
from typing import Any

from prometeus.application.course_understanding import extract_json_object
from prometeus.application.runtime_preflight import ACTOR_SETTING_BY_SOURCE
from prometeus.application.skill_registry import SkillRegistry
from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.generative_model import GenerativeModelPort
from prometeus.domain.research import (
    CourseResearchPlan,
    CourseUnderstanding,
    PlannedToolCall,
    ResearchQuestion,
)


class ResearchPlanValidationError(ValueError):
    pass


def _normalize_priority(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return max(1, min(5, value))
    if isinstance(value, float):
        return max(1, min(5, int(round(value))))
    if isinstance(value, str):
        mapping = {"high": 1, "alta": 1, "critical": 1, "medium": 2, "media": 2, "média": 2, "low": 3, "baixa": 3}
        lowered = value.strip().lower()
        if lowered in mapping:
            return mapping[lowered]
        if lowered.isdigit():
            return max(1, min(5, int(lowered)))
    return 1


def _normalize_question(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "id": f"q-{index + 1}",
            "question": str(item),
            "evidence_need": "Evidência empírica de mercado",
            "priority": 1,
        }
    question_text = str(item.get("question") or item.get("text") or f"Questão {index + 1}").strip()
    evidence_need = str(
        item.get("evidence_need")
        or item.get("rationale")
        or item.get("need")
        or question_text
    ).strip()
    result: dict[str, Any] = {
        "question": question_text,
        "evidence_need": evidence_need,
        "priority": _normalize_priority(item.get("priority", 1)),
    }
    if item.get("id"):
        result["id"] = str(item["id"])
    return result


def _normalize_call(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ResearchPlanValidationError(f"Item {index} de tool_calls inválido.")
    capability = str(item.get("capability") or "").strip()
    query = str(item.get("query") or "").strip()
    rationale = str(
        item.get("rationale")
        or item.get("reason")
        or item.get("purpose")
        or f"Coletar evidências em {capability}"
    ).strip()
    raw_max = item.get("max_items", 5)
    try:
        max_items = max(1, min(1000, int(raw_max)))
    except (TypeError, ValueError):
        max_items = 5
    params = item.get("parameters")
    parameters = dict(params) if isinstance(params, dict) else {}
    q_ids = item.get("question_ids")
    if isinstance(q_ids, list):
        question_ids = [str(q) for q in q_ids if q]
    elif isinstance(q_ids, str) and q_ids.strip():
        question_ids = [q_ids.strip()]
    else:
        question_ids = []
    result: dict[str, Any] = {
        "capability": capability,
        "query": query,
        "required": bool(item.get("required", True)),
        "rationale": rationale,
        "max_items": max_items,
        "parameters": parameters,
        "question_ids": question_ids,
    }
    if item.get("id"):
        result["id"] = str(item["id"])
    return result


class CourseResearchPlanner:
    def __init__(
        self,
        llm: GenerativeModelPort,
        skills: SkillRegistry,
        settings: AppSettings,
    ) -> None:
        self.llm = llm
        self.skills = skills
        self.settings = settings

    async def plan(self, understanding: CourseUnderstanding) -> CourseResearchPlan:
        skill = self.skills.for_stage("research_planning")[0]
        allowed = sorted(ACTOR_SETTING_BY_SOURCE)
        understanding_json = understanding.model_dump_json(exclude={"created_at"}, indent=2)
        system_prompt = (
            f"{skill.instructions}\n\n"
            "Use somente capabilities da allowlist fornecida. Responda exclusivamente em JSON "
            "com arrays questions e tool_calls compatíveis com o seguinte schema exato:\n"
            "{\n"
            '  "questions": [\n'
            '    {"id": "q-1", "question": "string", "evidence_need": "string", "priority": 1}\n'
            "  ],\n"
            '  "tool_calls": [\n'
            "    {\n"
            '      "id": "call-1",\n'
            '      "capability": "nome_da_capability",\n'
            '      "query": "termo curto de busca",\n'
            '      "required": true,\n'
            '      "rationale": "justificativa objetiva",\n'
            '      "max_items": 5,\n'
            '      "parameters": {"country": "BR", "language": "pt", "location": "Brasil"},\n'
            '      "question_ids": ["q-1"]\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        prompt = (
            f"Allowlist de capabilities: {json.dumps(allowed, ensure_ascii=False)}\n"
            f"Fontes obrigatórias (todas devem ter pelo menos uma chamada com required=true): "
            f"{json.dumps(self.settings.required_market_sources)}\n"
            f"Orçamento total USD: {self.settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS}\n"
            "Regras de execução:\n"
            "1. Inclua todas as fontes obrigatórias listadas acima com required=true.\n"
            "2. Use max_items entre 3 e 5 por chamada para respeitar o orçamento.\n"
            "3. Use queries curtas e de alta abrangência no mercado (2 a 3 palavras, ex.: "
            "'direito securitário', 'pós-graduação seguros', 'advogado seguros'), nunca o título "
            "inteiro do curso. Para instagram, use uma única palavra de hashtag sem '#' nem espaços "
            "(ex.: 'seguros').\n"
            "4. Contrato de parâmetros: country=BR, language=pt, location=Brasil; "
            "web_crawler e youtube_comments NÃO devem receber URLs inventadas em parameters — "
            "deixe parameters sem 'urls' para que o executor use as URLs reais descobertas pelo "
            "google_search. Planeje uma chamada google_search adicional com 'site:youtube.com/watch' "
            "mais o tema curto para descobrir vídeos reais para youtube_comments.\n"
            "5. Não invente URLs, IDs, métricas, atores ou resultados. Cada query deve ser "
            "específica ao domínio do curso entendido.\n"
            f"<course_understanding>\n{understanding_json}\n</course_understanding>"
        )
        raw = await self.llm.generate_text(
            prompt=prompt, system_prompt=system_prompt, temperature=0.1
        )
        payload = extract_json_object(raw)

        raw_questions = payload.get("questions", [])
        raw_calls = payload.get("tool_calls", [])
        questions = [
            ResearchQuestion.model_validate(_normalize_question(item, idx))
            for idx, item in enumerate(raw_questions if isinstance(raw_questions, list) else [])
        ]
        calls = [
            PlannedToolCall.model_validate(_normalize_call(item, idx))
            for idx, item in enumerate(raw_calls if isinstance(raw_calls, list) else [])
        ]
        unknown = sorted({call.capability for call in calls} - set(allowed))
        if unknown:
            raise ResearchPlanValidationError(
                f"O plano tentou usar capabilities fora da allowlist: {unknown}"
            )
        required_set = set(self.settings.required_market_sources)
        seen_required_caps: set[str] = set()
        normalized_calls: list[PlannedToolCall] = []
        for call in calls:
            is_req = call.required and (call.capability in required_set) and (call.capability not in seen_required_caps)
            if is_req:
                seen_required_caps.add(call.capability)
            normalized_calls.append(call.model_copy(update={"required": is_req}))
        calls = normalized_calls

        required_present = {call.capability for call in calls if call.required}
        missing = sorted(set(self.settings.required_market_sources) - required_present)
        if missing:
            raise ResearchPlanValidationError(
                f"O plano não cobre todas as fontes obrigatórias: {missing}"
            )
        if not calls:
            raise ResearchPlanValidationError("O plano não contém chamadas de ferramentas reais.")

        yt_calls_without_urls = [
            call
            for call in calls
            if call.capability == "youtube_comments"
            and not call.parameters.get("urls")
            and not call.parameters.get("start_urls")
        ]
        has_youtube_search = any(
            call.capability == "google_search" and "youtube" in call.query.lower()
            for call in calls
        )
        if yt_calls_without_urls and not has_youtube_search and "google_search" in allowed:
            yt_query = yt_calls_without_urls[0].query
            calls.append(
                PlannedToolCall(
                    id="google-youtube-discovery",
                    capability="google_search",
                    query=f"site:youtube.com/watch {yt_query}",
                    required=False,
                    rationale="Descobrir URLs reais de vídeos do YouTube para coleta de comentários",
                    max_items=3,
                    parameters={"country": "BR", "language": "pt"},
                    question_ids=yt_calls_without_urls[0].question_ids,
                )
            )

        return CourseResearchPlan(
            analysis_id=understanding.analysis_id,
            understanding_hash=understanding.snapshot_hash,
            questions=questions,
            tool_calls=calls,
            budget_limit_usd=self.settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS,
            skill_snapshots=[skill.snapshot()],
        )
