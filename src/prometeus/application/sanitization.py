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
]

# Regex para remoção de tags HTML gerais
HTML_TAG_RE = re.compile(r"<[^>]+>")
EXECUTABLE_HTML_RE = re.compile(
    r"<\s*(script|iframe|style)\b[^>]*>.*?(?:</\s*\1\s*>|$)",
    re.IGNORECASE | re.DOTALL,
)

# Regex para PII básica (CPF, e-mails, telefones comuns)
CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[-.\s]?\d{4}\b")
PUBLIC_ID_FIELDS = frozenset(
    {
        "jobId",
        "job_id",
        "adArchiveId",
        "adArchiveID",
        "ad_archive_id",
        "ad_id",
        "commentId",
        "cid",
        "shortCode",
        "videoId",
    }
)
PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

TEMPORAL_FIELDS = frozenset(
    {
        "time",
        "timestamp",
        "formattedTime",
        "formattedAxisTime",
        "startTime",
        "endTime",
        "date",
        "datetime",
        "dateFrom",
        "dateTo",
        "collected_at",
        "publishedAt",
        "postedAt",
        "startDate",
        "endDate",
        "period",
        "createdAt",
        "updatedAt",
        "published_at",
        "axisTime",
        "axisNote",
        "timeRange",
        "dateRange",
    }
)


class EvidenceSanitizer:
    """Higieniza payloads brutos da web, neutraliza ameaças e calcula escore de qualidade."""

    def sanitize_text(self, text: str, *, is_temporal: bool = False) -> tuple[str, bool]:
        """Limpa texto, neutraliza injeções e indica se havia conteúdo malicioso/suspeito."""
        if not text:
            return "", False

        # Decode before scanning so encoded instructions cannot bypass detection.
        for _ in range(3):
            decoded = html.unescape(text)
            if decoded == text:
                break
            text = decoded
        text = EXECUTABLE_HTML_RE.sub(" ", text)
        text = HTML_TAG_RE.sub(" ", text) if "<|im_start|>" not in text.lower() else text
        text = re.sub(r"javascript\s*:", " ", text, flags=re.IGNORECASE)
        had_injection = False

        # 1. Checa padrões de prompt injection
        for pat in INJECTION_PATTERNS:
            if pat.search(text):
                had_injection = True
                text = pat.sub("[CONTEUDO_REMOVIDO_POR_SEGURANCA]", text)

        # 2. Desescapa e remove tags HTML
        clean_text = HTML_TAG_RE.sub(" ", text)

        # 3. Higieniza dados pessoais (LGPD), exceto campos temporais explícitos
        if not is_temporal:
            clean_text = CPF_RE.sub("[CPF_REDACTED]", clean_text)
            clean_text = EMAIL_RE.sub("[EMAIL_REDACTED]", clean_text)
            clean_text = PHONE_RE.sub("[PHONE_REDACTED]", clean_text)

        # 4. Remove múltiplos espaços em branco
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        return clean_text, had_injection

    def sanitize_payload(self, raw_data: dict[str, Any]) -> tuple[dict[str, Any], float]:
        """Higieniza recursivamente os campos de um dicionário e calcula quality_score."""
        sanitized, penalty = self._sanitize_value(raw_data)
        score = max(0.1, round(1.0 - min(0.9, penalty), 2))
        return sanitized, score

    def _sanitize_value(self, value: Any, key: str | None = None) -> tuple[Any, float]:
        """Internal recursion returns a penalty, never a quality score."""
        if isinstance(value, str):
            is_temp = key in TEMPORAL_FIELDS if key else False
            cleaned, suspicious = self.sanitize_text(value, is_temporal=is_temp)
            return cleaned, 0.35 if suspicious else 0.0
        if isinstance(value, dict):
            cleaned_dict: dict[str, Any] = {}
            penalty = 0.0
            for k, item in value.items():
                if k in TEMPORAL_FIELDS:
                    if isinstance(item, str):
                        cleaned, suspicious = self.sanitize_text(item, is_temporal=True)
                        cleaned_dict[k] = cleaned
                        if suspicious:
                            penalty += 0.35
                    else:
                        cleaned, item_penalty = self._sanitize_value(item, key=k)
                        cleaned_dict[k] = cleaned
                        penalty += item_penalty
                    continue

                # Identifiers in a typed public listing are not contact numbers.
                # Unknown `id` fields and all free text still receive PII removal.
                listing_id = k == "id" and (
                    (
                        "title" in value
                        and any(
                            field in value
                            for field in ("location", "jobLocation", "jobUrl", "companyName")
                        )
                    )
                    or any(
                        field in value
                        for field in ("jobId", "job_id", "shortCode", "commentId", "ad_archive_id")
                    )
                )
                if (
                    (k in PUBLIC_ID_FIELDS or listing_id)
                    and isinstance(item, (str, int))
                    and not isinstance(item, bool)
                    and PUBLIC_ID_RE.fullmatch(str(item))
                ):
                    cleaned_dict[k] = item
                    continue
                cleaned, item_penalty = self._sanitize_value(item, key=k)
                cleaned_dict[k] = cleaned
                penalty += item_penalty
            return cleaned_dict, penalty
        if isinstance(value, list):
            cleaned_list: list[Any] = []
            penalty = 0.0
            for item in value:
                cleaned, item_penalty = self._sanitize_value(item, key=key)
                cleaned_list.append(cleaned)
                penalty += item_penalty
            return cleaned_list, penalty
        return value, 0.0

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
                # Redaction tokens can expand a title beyond its storage bound.
                # The complete content remains in raw_payload/sanitized_data.
                title=clean_title[:256],
                raw_payload=ev.raw_payload,
                sanitized_data=sanitized_data,
                quality_score=quality_score,
                cost_usd=ev.cost_usd,
                collected_at=ev.collected_at,
            )
            clean_evidences.append(sanitized_ev)

        return clean_evidences
