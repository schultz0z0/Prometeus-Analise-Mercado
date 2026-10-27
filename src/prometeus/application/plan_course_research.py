"""Planejamento de pesquisa guiado por LLM e validado por política determinística."""

from __future__ import annotations

import json

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
            "com arrays questions e tool_calls compatíveis com os contratos informados."
        )
        prompt = (
            f"Allowlist de capabilities: {json.dumps(allowed, ensure_ascii=False)}\n"
            f"Fontes obrigatórias: {json.dumps(self.settings.required_market_sources)}\n"
            f"Orçamento total USD: {self.settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS}\n"
            "Contrato de parâmetros: country=BR, language=pt, location=Brasil; "
            "web_crawler e youtube_comments aceitam parameters.urls com URLs HTTP(S). "
            "Quando essas URLs ainda não forem conhecidas, planeje antes google_search com "
            "consulta apropriada (inclua site:youtube.com para descobrir vídeos); o executor "
            "resolverá as URLs reais encontradas antes de chamar as ferramentas dependentes. "
            "Não invente URLs, IDs, métricas, atores ou resultados. Cada query deve ser "
            "específica ao curso entendido.\n"
            f"<course_understanding>\n{understanding_json}\n</course_understanding>"
        )
        raw = await self.llm.generate_text(
            prompt=prompt, system_prompt=system_prompt, temperature=0.1
        )
        payload = extract_json_object(raw)

        questions = [ResearchQuestion.model_validate(item) for item in payload.get("questions", [])]
        calls = [PlannedToolCall.model_validate(item) for item in payload.get("tool_calls", [])]
        unknown = sorted({call.capability for call in calls} - set(allowed))
        if unknown:
            raise ResearchPlanValidationError(
                f"O plano tentou usar capabilities fora da allowlist: {unknown}"
            )
        required_present = {call.capability for call in calls if call.required}
        missing = sorted(set(self.settings.required_market_sources) - required_present)
        if missing:
            raise ResearchPlanValidationError(
                f"O plano não cobre todas as fontes obrigatórias: {missing}"
            )
        if not calls:
            raise ResearchPlanValidationError("O plano não contém chamadas de ferramentas reais.")

        return CourseResearchPlan(
            analysis_id=understanding.analysis_id,
            understanding_hash=understanding.snapshot_hash,
            questions=questions,
            tool_calls=calls,
            budget_limit_usd=self.settings.APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS,
            skill_snapshots=[skill.snapshot()],
        )
