"""Serviço de higienização, deduplicação e segurança de evidências externas (Etapa 08).

Trata conteúdo coletado da web como dado não confiável e potencialmente malicioso (AGENTS.md):
remove injeções de prompt, scripts HTML, PII e deduplica por content_hash.
"""

from __future__ import annotations

import html
import re
from typing import Any

from prometeus.domain.ports.market_sources import MarketEvidence

# Padrões suspeitos de prompt injection e jailbreak
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an?\s+)?unrestricted", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
    re.compile(r"<\s*iframe[^>]*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
]

# Regex para remoção de tags HTML gerais
HTML_TAG_RE = re.compile(r"<[^>]+>")

# Regex para PII básica (CPF, e-mails, telefones comuns)
CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[-.\s]?\d{4}\b")


class EvidenceSanitizer:
    """Higieniza payloads brutos da web, neutraliza ameaças e calcula escore de qualidade."""

    def sanitize_text(self, text: str) -> tuple[str, bool]:
        """Limpa texto, neutraliza injeções e indica se havia conteúdo malicioso/suspeito."""
        if not text:
            return "", False

        had_injection = False

        # 1. Checa padrões de prompt injection
        for pat in INJECTION_PATTERNS:
            if pat.search(text):
                had_injection = True
                text = pat.sub("[CONTEUDO_REMOVIDO_POR_SEGURANCA]", text)

        # 2. Desescapa e remove tags HTML
        clean_text = html.unescape(text)
        clean_text = HTML_TAG_RE.sub(" ", clean_text)

        # 3. Higieniza dados pessoais (LGPD)
        clean_text = CPF_RE.sub("[CPF_REDACTED]", clean_text)
        clean_text = EMAIL_RE.sub("[EMAIL_REDACTED]", clean_text)
        clean_text = PHONE_RE.sub("[PHONE_REDACTED]", clean_text)

        # 4. Remove múltiplos espaços em branco
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        return clean_text, had_injection

    def sanitize_payload(self, raw_data: dict[str, Any]) -> tuple[dict[str, Any], float]:
        """Higieniza recursivamente os campos de um dicionário e calcula quality_score."""
        sanitized: dict[str, Any] = {}
        penalty = 0.0

        for key, val in raw_data.items():
            if isinstance(val, str):
                cleaned, suspicious = self.sanitize_text(val)
                sanitized[key] = cleaned
                if suspicious:
                    penalty += 0.35
            elif isinstance(val, dict):
                sub_san, sub_pen = self.sanitize_payload(val)
                sanitized[key] = sub_san
                penalty += sub_pen
            elif isinstance(val, list):
                new_list: list[Any] = []
                for item in val:
                    if isinstance(item, str):
                        cl, susp = self.sanitize_text(item)
                        new_list.append(cl)
                        if susp:
                            penalty += 0.15
                    elif isinstance(item, dict):
                        cl_d, p_d = self.sanitize_payload(item)
                        new_list.append(cl_d)
                        penalty += p_d
                    else:
                        new_list.append(item)
                sanitized[key] = new_list
            else:
                sanitized[key] = val

        score = max(0.1, round(1.0 - min(0.9, penalty), 2))
        return sanitized, score

    def process_and_deduplicate(
        self,
        evidences: list[MarketEvidence],
    ) -> list[MarketEvidence]:
        """Aplica higienização completa e remove duplicatas com base no content_hash."""
        seen_hashes = set()
        clean_evidences: list[MarketEvidence] = []

        for ev in evidences:
            if ev.content_hash in seen_hashes:
                # Evidência duplicada descartada
                continue

            seen_hashes.add(ev.content_hash)

            sanitized_data, quality_score = self.sanitize_payload(ev.raw_payload)
            clean_title, _ = self.sanitize_text(ev.title)

            # Preserva imutabilidade recriando com dados sanitizados
            sanitized_ev = MarketEvidence(
                id=ev.id,
                analysis_id=ev.analysis_id,
                evidence_type=ev.evidence_type,
                source_name=ev.source_name,
                source_url=ev.source_url,
                collector=ev.collector,
                content_hash=ev.content_hash,
                title=clean_title,
                raw_payload=ev.raw_payload,
                sanitized_data=sanitized_data,
                quality_score=quality_score,
                cost_usd=ev.cost_usd,
                collected_at=ev.collected_at,
            )
            clean_evidences.append(sanitized_ev)

        return clean_evidences
