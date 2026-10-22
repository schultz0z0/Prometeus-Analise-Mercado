"""Adaptador fake determinístico para GenerativeModelPort."""

from __future__ import annotations

from prometeus.domain.ports.generative_model import GenerativeModelPort


class FakeGenerativeModel(GenerativeModelPort):
    """Implementação em memória para testes unitários, contratuais e CI."""

    def __init__(
        self,
        canned_keywords: list[str] | None = None,
        canned_text: str = "Texto gerado para teste",
        simulate_error: bool = False,
    ) -> None:
        self.canned_keywords = canned_keywords
        self.canned_text = canned_text
        self.simulate_error = simulate_error
        self.call_history: list[dict[str, str]] = []

    async def generate_keyword_candidates(
        self,
        course_title: str,
        description: str,
        target_audience: str,
        max_candidates: int = 15,
    ) -> list[str]:
        if self.simulate_error:
            raise ConnectionError("Falha simulada na API generativa")

        self.call_history.append(
            {
                "course_title": course_title,
                "description": description,
                "target_audience": target_audience,
            }
        )

        if self.canned_keywords is not None:
            return self.canned_keywords[:max_candidates]

        # Gera candidatos determinísticos baseados nas palavras do título
        title_lower = course_title.lower()
        candidates = [
            f"curso {title_lower}",
            f"mba {title_lower}",
            f"especializacao {title_lower}",
            f"pos graduacao {title_lower}",
            f"como funciona {title_lower}",
            f"mercado de trabalho {title_lower}",
            f"treinamento {title_lower}",
        ]
        return candidates[:max_candidates]

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        if self.simulate_error:
            raise ConnectionError("Falha simulada na API generativa")

        return self.canned_text
