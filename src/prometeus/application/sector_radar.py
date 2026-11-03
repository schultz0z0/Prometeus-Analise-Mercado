"""Serviço de monitoramento persistente do Radar Setorial Permanente (seguradoras/empregadores)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.collect_market_evidence import ResearchToolExecutor
from prometeus.application.research_scope import match_sector_radar_actor, normalized_text
from prometeus.application.sanitization import EvidenceSanitizer
from prometeus.domain.configuration import SectorRadarActorConfig, TenantConfig
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyError
from prometeus.infrastructure.db.models import SectorRadarSnapshotModel

_THEME_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("IA, Automação & Subscrição", ("ia", "inteligencia artificial", "automacao", "subscricao", "telemetria", "analytics")),
    ("Sinistros & Operações Digitais", ("sinistro", "sinistros", "vistoria", "regulacao", "atendimento digital")),
    ("Canal Corretor & Distribuição", ("corretor", "corretores", "assessoria", "parceiros", "distribuicao", "capacitacao")),
    ("Saúde, Vida & Previdência", ("saude", "vida", "previdencia", "beneficios", "odontologico")),
    ("Grandes Riscos, Rural & ESG", ("grandes riscos", "rural", "agronegocio", "climatic", "ciberseguranca", "cibernetico", "esg")),
)


class SectorRadarSignal(BaseModel):
    """Sinal contextual higienizado capturado de um ator do Radar Setorial."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: str
    actor_id: str
    insurer_name: str
    priority: str
    channel_label: str
    scope_badge: str
    theme_detected: str
    market_or_broker_pain: str
    source_url: str
    collected_at: str


def _ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _detect_theme(text: str, focus_hints: list[str]) -> str:
    norm = normalized_text(text)
    for label, keywords in _THEME_KEYWORDS:
        if any(kw in norm for kw in keywords):
            return label
    if focus_hints:
        return focus_hints[0].capitalize()
    return "Movimentação Institucional & Produtos"


def _channel_and_scope(source_url: str, actor: dict[str, Any]) -> tuple[str, str]:
    host = (urlsplit(source_url).hostname or "").lower().removeprefix("www.")
    social = actor.get("social") if isinstance(actor.get("social"), dict) else {}
    li_scope = str(social.get("linkedin_scope") or "national")

    if "instagram.com" in host:
        return "Instagram", "Brasil"
    if "linkedin.com" in host:
        badge = "Global (contextual)" if li_scope == "global" else "Brasil"
        return "LinkedIn", badge
    return "Web Institucional", "Brasil"


def serialize_radar_snapshot(snapshot: SectorRadarSnapshotModel | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    now = datetime.now(UTC)
    expires = _ensure_utc(snapshot.expires_at)
    collected = _ensure_utc(snapshot.collected_at)
    return {
        "id": snapshot.id,
        "tenant_id": snapshot.tenant_id,
        "status": snapshot.status,
        "is_fresh": expires > now,
        "collected_at": collected.isoformat(),
        "expires_at": expires.isoformat(),
        "monitored_actors_count": snapshot.monitored_actors_count,
        "covered_actors": list(snapshot.covered_actors or []),
        "signals_count": len(snapshot.signals or []),
        "signals": list(snapshot.signals or []),
        "trending_themes": list(snapshot.trending_themes or []),
        "spent_usd": round(float(snapshot.spent_usd or 0.0), 4),
        "error_summary": snapshot.error_summary,
    }


class SectorRadarService:
    """Gerencia coleta periódica/sob demanda, sanitização e cache TTL do Radar Setorial."""

    def __init__(
        self,
        session: AsyncSession,
        executor: ResearchToolExecutor | None = None,
        sanitizer: EvidenceSanitizer | None = None,
        allowed_capabilities: list[str] | None = None,
    ) -> None:
        self.session = session
        self.executor = executor
        self.sanitizer = sanitizer or EvidenceSanitizer()
        self.allowed_capabilities = (
            set(allowed_capabilities) if allowed_capabilities is not None else {"google_search", "instagram"}
        )

    @staticmethod
    def _config_hash(actors: list[SectorRadarActorConfig]) -> str:
        payload = [actor.model_dump(mode="json") for actor in actors]
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get_latest_snapshot(
        self, tenant_id: str, *, include_expired: bool = False
    ) -> SectorRadarSnapshotModel | None:
        stmt = (
            select(SectorRadarSnapshotModel)
            .where(
                SectorRadarSnapshotModel.tenant_id == tenant_id,
                SectorRadarSnapshotModel.status.in_(("READY", "PARTIAL")),
            )
            .order_by(SectorRadarSnapshotModel.collected_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        now = datetime.now(UTC)
        for row in rows:
            if include_expired or _ensure_utc(row.expires_at) > now:
                return row
        return None

    def _build_radar_calls(
        self, actors: list[SectorRadarActorConfig], max_budget_usd: float
    ) -> list[PlannedToolCall]:
        calls: list[PlannedToolCall] = []
        primary = [a for a in actors if a.priority == "primary"]
        secondary = [a for a in actors if a.priority != "primary"]
        ordered = [*primary, *secondary]

        if "google_search" in self.allowed_capabilities and ordered:
            # Inclui domínios institucionais e LinkedIn corporativo (para atores monitorados) em chunks <= 5
            domains = [a.domains[0] for a in ordered if a.domains]
            for idx in range(0, len(domains), 5):
                chunk = domains[idx : idx + 5]
                site_clause = " OR ".join(f"site:{d}" for d in chunk)
                calls.append(
                    PlannedToolCall(
                        id=f"radar-gsearch-{idx // 5 + 1}",
                        capability="google_search",
                        query=f"({site_clause}) corretores inovacao sinistros produtos",
                        required=False,
                        rationale="Coleta periódica do Radar Setorial (web institucional e comunicados)",
                        max_items=10,
                        parameters={"country": "BR", "language": "pt-BR", "ecosystem_role": "sector_radar"},
                    )
                )

        if "instagram" in self.allowed_capabilities and max_budget_usd >= 0.40:
            # Somente handles de Instagram confirmados (ignora None / Não confirmado)
            confirmed_ig = [
                a for a in ordered if a.social.instagram_handle and a.social.instagram_handle.strip()
            ]
            max_ig_profiles = 4 if max_budget_usd >= 1.0 else 2
            for actor in confirmed_ig[:max_ig_profiles]:
                handle = str(actor.social.instagram_handle).strip().lstrip("@")
                calls.append(
                    PlannedToolCall(
                        id=f"radar-ig-{actor.id}",
                        capability="instagram",
                        query=handle,
                        required=False,
                        rationale=f"Pulso social confirmado de {actor.name} (@{handle})",
                        max_items=5,
                        parameters={
                            "search_type": "user",
                            "results_type": "posts",
                            "ecosystem_role": "sector_radar",
                            "actor_id": actor.id,
                        },
                    )
                )
        return calls

    async def refresh_radar(
        self,
        tenant_id: str,
        tenant_config: TenantConfig,
        *,
        max_budget_usd: float = 1.50,
        force: bool = False,
    ) -> SectorRadarSnapshotModel:
        actors = list(tenant_config.ecosystem.sector_radar)
        cfg_hash = self._config_hash(actors)
        if not force:
            cached = await self.get_latest_snapshot(tenant_id, include_expired=False)
            if cached is not None and cached.config_hash == cfg_hash:
                return cached

        if self.executor is None:
            raise ValueError("Executor de ferramentas Apify não configurado para refresh do Radar Setorial.")

        now = datetime.now(UTC)
        ttl_hours = tenant_config.ecosystem.radar_ttl_hours
        expires_at = now + timedelta(hours=ttl_hours)
        actor_dicts = [a.model_dump(mode="json") for a in actors]
        actor_by_id = {a["id"]: a for a in actor_dicts}
        ctx = {
            "id": tenant_config.institution.id,
            "name": tenant_config.institution.display_name,
            "domains": list(tenant_config.institution.domains),
            "sector_radar": actor_dicts,
        }

        calls = self._build_radar_calls(actors, max_budget_usd)
        spent_usd = 0.0
        signals: list[SectorRadarSignal] = []
        seen_keys: set[tuple[str, str]] = set()
        errors: list[str] = []
        succeeded_channels = 0

        for call in calls:
            remaining = round(max_budget_usd - spent_usd, 4)
            if remaining < 0.03:
                break
            try:
                result = await self.executor.execute(call, max_total_charge_usd=remaining)
                call_cost = float(
                    getattr(getattr(result, "run", None), "cost_usd", getattr(result, "cost_usd", 0.0))
                    or 0.0
                )
                spent_usd = round(spent_usd + call_cost, 4)
                succeeded_channels += 1
            except (ApifyError, httpx.HTTPError, TimeoutError, RuntimeError) as exc:
                errors.append(f"{call.capability} ({call.id}): {str(exc)[:180]}")
                continue

            for raw_item in result.items:
                if not isinstance(raw_item, dict):
                    continue
                clean_item, _ = self.sanitizer.sanitize_payload(raw_item)
                organic = clean_item.get("organicResults")
                candidates: list[dict[str, Any]] = (
                    [entry for entry in organic if isinstance(entry, dict)]
                    if isinstance(organic, list) and organic
                    else [clean_item]
                )
                for entry in candidates:
                    url = str(entry.get("url") or entry.get("link") or "").strip()
                    if not url.startswith(("https://", "http://")):
                        continue
                    matched = match_sector_radar_actor(entry, url, ctx)
                    if matched is None and call.parameters.get("actor_id") in actor_by_id:
                        matched = actor_by_id[str(call.parameters["actor_id"])]
                    if matched is None:
                        continue

                    dedup_key = (str(matched["id"]), url.rstrip("/").lower())
                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)

                    raw_title = str(entry.get("title") or "").strip()
                    raw_body = str(
                        entry.get("description")
                        or entry.get("caption")
                        or entry.get("text")
                        or ""
                    ).strip()
                    clean_title, _ = self.sanitizer.sanitize_text(raw_title)
                    clean_body, _ = self.sanitizer.sanitize_text(raw_body)
                    combined = " — ".join(p for p in (clean_title, clean_body) if p)[:360]
                    if not combined:
                        continue

                    channel_label, scope_badge = _channel_and_scope(url, matched)
                    theme = _detect_theme(
                        combined, list(matched.get("monitoring_focus") or [])
                    )
                    signals.append(
                        SectorRadarSignal(
                            signal_id=f"sig-{uuid.uuid4().hex[:10]}",
                            actor_id=str(matched["id"]),
                            insurer_name=str(matched["name"]),
                            priority=str(matched.get("priority") or "secondary"),
                            channel_label=channel_label,
                            scope_badge=scope_badge,
                            theme_detected=theme,
                            market_or_broker_pain=combined,
                            source_url=url,
                            collected_at=now.isoformat(),
                        )
                    )

        if succeeded_channels == 0 and errors:
            status = "FAILED"
        elif errors:
            status = "PARTIAL"
        else:
            status = "READY"

        covered_actors = list(dict.fromkeys(sig.actor_id for sig in signals))
        theme_counts: dict[str, int] = {}
        for sig in signals:
            theme_counts[sig.theme_detected] = theme_counts.get(sig.theme_detected, 0) + 1
        trending_themes = [
            theme for theme, _ in sorted(theme_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

        model = SectorRadarSnapshotModel(
            id=f"rdr-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            status=status,
            collected_at=now,
            expires_at=expires_at,
            monitored_actors_count=len(actors),
            covered_actors=covered_actors,
            signals=[sig.model_dump(mode="json") for sig in signals],
            trending_themes=trending_themes,
            spent_usd=spent_usd,
            config_hash=cfg_hash,
            error_summary="; ".join(errors)[:1000] if errors else None,
        )
        self.session.add(model)
        await self.session.commit()
        return model
