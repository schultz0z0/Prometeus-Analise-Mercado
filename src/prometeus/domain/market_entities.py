"""Separação canônica entre Captura (observação pontual) e Entidade (ativo de mercado).

Implementa os requisitos da Tarefa 2.2:
- Preserva múltiplas capturas da mesma entidade ao longo do tempo sem multiplicar contagens de concorrentes
- Identifica atualizações, novas versões e contradições entre capturas
- Suporta deduplicação orientada a entidades para Meta Ads, vagas, comentários e ofertas
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field


def canonicalize_url(value: str) -> str:
    """Normaliza URL removendo parâmetros de rastreamento e mantendo parâmetros semânticos."""
    if not value or not isinstance(value, str):
        return ""
    parsed = urlsplit(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"gclid", "fbclid", "ref", "trackingid"}
    ]
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    return urlunsplit(
        ("https", hostname, parsed.path.rstrip("/") or "/", urlencode(sorted(query)), "")
    )


def extract_canonical_entity_id(capability: str, item: dict[str, Any]) -> str:
    """Extrai chave de identidade canônica da entidade baseada no tipo de fonte."""
    if not isinstance(item, dict):
        return f"entity:unknown_{hashlib.sha256(str(item).encode()).hexdigest()[:12]}"

    if capability == "meta_ads":
        ad_id = item.get("ad_archive_id") or item.get("adId") or item.get("id")
        if ad_id:
            return f"ad:{ad_id}"

    if capability == "linkedin_jobs":
        job_id = item.get("jobId") or item.get("job_id") or item.get("id")
        if job_id:
            return f"job:{job_id}"
        job_url = item.get("jobUrl") or item.get("url")
        if job_url:
            return f"job:{canonicalize_url(str(job_url))}"

    if capability == "youtube_comments":
        cid = item.get("cid") or item.get("commentId") or item.get("id")
        if cid:
            return f"comment:{cid}"

    if capability == "web_crawler":
        url = item.get("url") or item.get("source_url") or item.get("link")
        if url:
            return f"offer:{canonicalize_url(str(url))}"

    if capability == "linkedin_companies":
        company_id = (
            item.get("companyId")
            or item.get("universalName")
            or item.get("linkedinUrl")
            or item.get("name")
        )
        if company_id:
            return f"company:{company_id}"

    if capability == "google_trends":
        term = item.get("term") or item.get("keyword") or item.get("query")
        if term:
            return f"trend:{str(term).strip().lower()}"

    # Fallback determinístico baseado na URL ou conteúdo
    for url_key in ("url", "link", "source_url", "videoUrl"):
        val = item.get(url_key)
        if isinstance(val, str) and val.startswith(("http://", "https://")):
            return f"entity:{canonicalize_url(val)}"

    item_repr = json.dumps(item, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(item_repr.encode("utf-8")).hexdigest()[:16]
    return f"entity:{digest}"


class MarketCapture(BaseModel):
    """Observação pontual de um dado em um determinado momento e tool run."""

    capture_id: str
    entity_id: str
    entity_type: str
    tool_run_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_url: str = ""
    condition_version: int = 1
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    sanitized_data: dict[str, Any] = Field(default_factory=dict)


class MarketEntity(BaseModel):
    """Ativo de mercado canônico agregando histórico e versões de capturas."""

    entity_id: str
    entity_type: str
    canonical_url: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    capture_count: int = 1
    versions: list[str] = Field(default_factory=list)  # Lista de capture_ids
    latest_state: dict[str, Any] = Field(default_factory=dict)
    has_updates: bool = False
    has_contradictions: bool = False


class EntityLineageTracker:
    """Gerencia capturas, agrega linhagem de entidades e detecta atualizações/contradições."""

    def __init__(self) -> None:
        self.captures: list[MarketCapture] = []
        self.entities: dict[str, MarketEntity] = {}

    def record_capture(
        self,
        *,
        capability: str,
        item: dict[str, Any],
        tool_run_id: str,
        capture_id: str | None = None,
        captured_at: datetime | None = None,
        source_url: str | None = None,
        sanitized_data: dict[str, Any] | None = None,
    ) -> MarketCapture:
        import uuid

        cid = capture_id or str(uuid.uuid4())
        ts = captured_at or datetime.now(UTC)
        entity_id = extract_canonical_entity_id(capability, item)
        entity_type = entity_id.split(":", 1)[0]
        url = source_url or item.get("url") or item.get("source_url") or ""

        existing_entity = self.entities.get(entity_id)
        version_num = (len(existing_entity.versions) + 1) if existing_entity else 1

        capture = MarketCapture(
            capture_id=cid,
            entity_id=entity_id,
            entity_type=entity_type,
            tool_run_id=tool_run_id,
            captured_at=ts,
            source_url=str(url),
            condition_version=version_num,
            raw_payload=item,
            sanitized_data=sanitized_data or item,
        )
        self.captures.append(capture)

        if existing_entity is None:
            self.entities[entity_id] = MarketEntity(
                entity_id=entity_id,
                entity_type=entity_type,
                canonical_url=canonicalize_url(str(url)) if url else None,
                first_seen_at=ts,
                last_seen_at=ts,
                capture_count=1,
                versions=[cid],
                latest_state=item,
                has_updates=False,
                has_contradictions=False,
            )
        else:
            existing_entity.capture_count += 1
            existing_entity.versions.append(cid)
            existing_entity.last_seen_at = ts
            existing_entity.has_updates = True
            # Verifica se há divergência/contradição entre payloads observados
            if item != existing_entity.latest_state:
                existing_entity.has_contradictions = True
            existing_entity.latest_state = item

        return capture

    def get_entity(self, entity_id: str) -> MarketEntity | None:
        return self.entities.get(entity_id)

    @property
    def total_captures(self) -> int:
        return len(self.captures)

    @property
    def unique_entities_count(self) -> int:
        return len(self.entities)

    @property
    def duplicate_captures_count(self) -> int:
        return max(0, self.total_captures - self.unique_entities_count)

    @property
    def distinct_entities_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entity in self.entities.values():
            counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
        return counts

