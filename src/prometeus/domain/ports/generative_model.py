"""Porta canônica para modelos generativos (LLM).

Desacopla a geração de texto e de termos de busca da infraestrutura do provedor,
reutilizável na Fase 04 (Keywords TOOL-01) e na Fase 06 (Dossiê).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class GenerativeModelPort(ABC):
    """Porta agnóstica para modelos generativos de linguagem."""

    @abstractmethod
    async def generate_keyword_candidates(
        self,
        course_title: str,
        description: str,
        target_audience: str,
        max_candidates: int = 15,
    ) -> list[str]:
        """Gera termos candidatos para pesquisa de mercado (TOOL-01)."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Executa geração textual livre com restrições e telemetria."""
        pass
