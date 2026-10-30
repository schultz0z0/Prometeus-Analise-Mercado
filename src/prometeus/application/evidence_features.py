"""Extração determinística de métricas observadas em evidências persistidas."""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from prometeus.application.research_scope import matches_narrow_geography, normalize_geography
from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence


@dataclass(frozen=True)
class VerifiedFeature:
    name: str
    value: int | float
    evidence_ids: list[str]
    method: str


@dataclass(frozen=True)
class EvidenceFeatureSet:
    features: dict[str, VerifiedFeature]

    def get(self, name: str) -> VerifiedFeature | None:
        return self.features.get(name)

    def require(self, name: str) -> VerifiedFeature:
        feature = self.get(name)
        if feature is None:
            raise KeyError(f"Feature verificada ausente: {name}")
        return feature


_BRL_PRICE_RE = re.compile(
    r"(?:R\$|BRL)\s*((?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,[0-9]{1,2})?)(?![0-9])", re.I
)


def observed_price_period(payload: dict[str, Any]) -> str | None:
    explicit = payload.get("price_period")
    if explicit in {"total", "monthly"}:
        return str(explicit)
    text = " ".join(
        str(payload.get(key, "")) for key in ("price", "text", "markdown", "description", "caption")
    )
    monthly = bool(re.search(r"mensalidade|mensal|/m[eê]s|por\s+m[eê]s", text, re.I))
    total = bool(re.search(r"investimento\s+total|valor\s+total|[àa]\s+vista", text, re.I))
    # Uma página com mensalidade e valor total exige seleção de oferta estruturada, não o primeiro preço.
    if monthly == total:
        return None
    return "monthly" if monthly else "total"


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float) and math.isfinite(value) and value >= 0:
        return float(value)
    return None


def _price_brl(payload: dict[str, Any]) -> float | None:
    for field_name in ("price_brl", "priceBrl", "tuition_brl"):
        value = _positive_number(payload.get(field_name))
        if value is not None and value > 0:
            return value
    candidate_texts: list[str] = []
    for text_field in ("price", "text", "markdown", "description", "caption"):
        raw = payload.get(text_field)
        if isinstance(raw, str) and raw.strip():
            candidate_texts.append(raw)
    organic = payload.get("organicResults")
    if isinstance(organic, list):
        for entry in organic:
            if isinstance(entry, dict):
                desc = entry.get("description")
                if isinstance(desc, str) and desc.strip():
                    candidate_texts.append(desc)
    amounts = {
        float(match.group(1).replace(".", "").replace(",", "."))
        for raw in candidate_texts
        for match in _BRL_PRICE_RE.finditer(raw)
    }
    # Vários valores podem ser matrícula, parcelas, promoção ou ofertas distintas.
    # Sem seleção estruturada de preço, não atribuir a periodicidade da página ao primeiro valor.
    if len(amounts) == 1:
        amount = next(iter(amounts))
        return amount if amount > 0 else None
    return None


class EvidenceFeatureExtractor:
    """Não estima valores ausentes; apenas agrega campos observados e tipados."""

    def __init__(self, *, geography: str | None = None, price_period: str | None = None) -> None:
        # The understanding may append a delivery note to the country. Match
        # the explicit country, rather than requiring that note in job locations.
        self.geography = normalize_geography(geography)
        self.price_period = price_period

    @staticmethod
    def _entity_key(evidence: MarketEvidence) -> tuple[str, str]:
        payload = evidence.sanitized_data
        fields = {
            EvidenceType.JOB_MARKET: ("jobId", "job_id", "id"),
            EvidenceType.PAID_COMPETITION: (
                "ad_archive_id",
                "adArchiveID",
                "adArchiveId",
                "ad_id",
                "id",
            ),
            EvidenceType.SOCIAL_VOICE: ("commentId", "cid", "id", "shortCode"),
        }.get(evidence.evidence_type, ())
        for name in fields:
            if value := payload.get(name):
                if not re.search(r"REDACTED|REMOVIDO|^\[", str(value), re.I):
                    return (evidence.evidence_type.value, f"{evidence.source_name}:{value}")
        parsed = urlsplit(evidence.source_url)
        if re.search(r"REDACTED|REMOVIDO|[\[\]]", evidence.source_url, re.I):
            return (evidence.evidence_type.value, evidence.content_hash)
        if evidence.evidence_type == EvidenceType.JOB_MARKET and (
            parsed.hostname or ""
        ).lower() in {"linkedin.com", "www.linkedin.com", "br.linkedin.com"}:
            match = re.search(r"/jobs/view/(?:[^/?]*-)?(\d{6,20})/?$", parsed.path)
            if match:
                return (evidence.evidence_type.value, f"linkedin-job:{match.group(1)}")
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"gclid", "fbclid", "ref", "trackingid"}
        ]
        canonical = urlunsplit(
            (
                "https",
                (parsed.hostname or "").lower().removeprefix("www."),
                parsed.path.rstrip("/"),
                urlencode(sorted(query)),
                "",
            )
        )
        if evidence.evidence_type in {EvidenceType.OFFER, EvidenceType.JOB_MARKET}:
            return (evidence.evidence_type.value, canonical)
        # Comentários sem identificador não se tornam duplicados apenas por compartilhar o vídeo.
        return (evidence.evidence_type.value, evidence.content_hash)

    def accepts(self, evidence: MarketEvidence) -> bool:
        """Respeita qualificação persistida e recorte geográfico observado, sem inferir por IP."""
        payload = evidence.sanitized_data
        qualification = payload.get("_qualification")
        if isinstance(qualification, dict) and qualification.get("accepted") is not True:
            return False
        if isinstance(qualification, dict):
            if qualification.get("own_institution") and evidence.evidence_type in {
                EvidenceType.PAID_COMPETITION,
                EvidenceType.OFFER,
            }:
                return False
            use_for = qualification.get("use_for")
            expected = {
                EvidenceType.JOB_MARKET: "employability",
                EvidenceType.PAID_COMPETITION: "paid_competition",
                EvidenceType.OFFER: "competitive_offers",
                EvidenceType.SOCIAL_VOICE: "audience_needs",
                EvidenceType.TRENDS: "search_interest",
                EvidenceType.SEARCH_VOLUME: "search_interest",
            }.get(evidence.evidence_type)
            if isinstance(use_for, list) and expected and expected not in use_for:
                return False
        if evidence.evidence_type == EvidenceType.JOB_MARKET and self.geography:
            if payload.get("jobs") == []:
                return True  # registro explícito de consulta válida sem resultados
            location = payload.get("location", payload.get("jobLocation", ""))
            if isinstance(location, dict):
                location = " ".join(str(v) for v in location.values())
            scope = str(payload.get("country", "")) + " " + str(location)
            if self.geography.casefold() in {"brasil", "brazil", "br"}:
                if not re.search(r"\b(?:brasil|brazil|br)\b", scope, re.I):
                    # Todas as 27 UFs brasileiras completas; não aceitar localização desconhecida.
                    states = r"AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO"
                    if not re.search(
                        rf",\s*(?:{states})(?:\s*$|\s*[,/-]\s*(?:Brasil|Brazil|BR)\b)",
                        str(location),
                        re.I,
                    ):
                        # Verifica se nome por extenso de estado brasileiro está presente
                        from prometeus.application.research_scope import BRAZILIAN_STATES
                        has_state_name = any(
                            re.search(rf"\b{re.escape(name)}\b", str(location), re.I)
                            for name in BRAZILIAN_STATES.values()
                        )
                        if not has_state_name:
                            return False
                    # PA isolado também é Pennsylvania: exige cidade brasileira reconhecível ou país.
                    if re.search(r",\s*PA\s*$", str(location), re.I) and not re.search(
                        r"Bel[eé]m|Santar[eé]m|Marab[aá]|Par[aá]", str(location), re.I
                    ):
                        return False
            elif not matches_narrow_geography(self.geography, scope):
                return False
        return True

    @staticmethod
    def _trends_metrics(payload: dict[str, Any]) -> dict[str, float]:
        series = payload.get("interestOverTime_timelineData")
        if series is None and isinstance(payload.get("interestOverTime"), dict):
            series = payload["interestOverTime"].get("timelineData")
        if not isinstance(series, list):
            return {}
        points: list[tuple[str, float]] = []
        for point in series:
            if not isinstance(point, dict):
                continue
            raw_partial = point.get("isPartial")
            is_partial = (
                raw_partial is True
                or raw_partial == [True]
                or (isinstance(raw_partial, list) and any(raw_partial))
            )
            if is_partial:
                continue
            has_data = point.get("hasData", True)
            if has_data is False or has_data == [False]:
                continue
            value = point.get("value")
            if isinstance(value, list):
                value = value[0] if len(value) == 1 else None
            number = _positive_number(value)
            if number is not None and number <= 100:
                points.append((str(point.get("time", "")), number))
        if not points:
            return {}
        points.sort(
            key=lambda point: (0, float(point[0]), "") if point[0].isdigit() else (1, 0.0, point[0])
        )
        values = [value for _, value in points]
        metrics = {"average_interest": round(statistics.fmean(values), 4)}
        # Janelas de igual tamanho, sem transformar base zero em crescimento fictício.
        half = len(values) // 2
        if half >= 2:
            before = statistics.fmean(values[:half])
            after = statistics.fmean(values[-half:])
            if before > 0:
                metrics["growth_trend_pct"] = round((after / before - 1) * 100, 4)
        return metrics

    @staticmethod
    def _observed_count(evidence: MarketEvidence) -> int:
        payload = evidence.sanitized_data
        nested_field = {
            EvidenceType.OFFER: "organicResults",
            EvidenceType.PAID_COMPETITION: "ads",
            EvidenceType.JOB_MARKET: "jobs",
            EvidenceType.SOCIAL_VOICE: "comments",
        }.get(evidence.evidence_type)
        if nested_field is not None and nested_field in payload:
            nested = payload.get(nested_field)
            return len(nested) if isinstance(nested, list) else 0
        return 1

    @staticmethod
    def _add_count_feature(
        features: dict[str, VerifiedFeature],
        *,
        name: str,
        evidences: list[MarketEvidence],
    ) -> None:
        if not evidences:
            return
        counts = [
            (evidence, EvidenceFeatureExtractor._observed_count(evidence)) for evidence in evidences
        ]
        value = sum(count for _, count in counts)
        ids = [evidence.id for evidence, _ in counts]
        features[name] = VerifiedFeature(
            name=name,
            value=value,
            evidence_ids=ids,
            method="count_valid_items",
        )

    @staticmethod
    def _numeric_values(
        evidences: list[MarketEvidence], field_name: str
    ) -> list[tuple[str, float]]:
        values: list[tuple[str, float]] = []
        for evidence in evidences:
            raw_value = evidence.sanitized_data.get(field_name)
            value = _positive_number(raw_value)
            if (
                field_name == "growth_trend_pct"
                and isinstance(raw_value, (int, float))
                and not isinstance(raw_value, bool)
                and math.isfinite(raw_value)
            ):
                value = float(raw_value)
            if value is not None:
                values.append((evidence.id, value))
        return values

    @staticmethod
    def _aggregate_numeric(
        features: dict[str, VerifiedFeature],
        *,
        name: str,
        values: list[tuple[str, float]],
        aggregation: str,
    ) -> None:
        if not values:
            return
        numbers = [value for _, value in values]
        if aggregation == "sum":
            aggregated = sum(numbers)
        elif aggregation == "median":
            aggregated = statistics.median(numbers)
        else:
            aggregated = statistics.fmean(numbers)
        if all(number.is_integer() for number in numbers) and aggregation == "sum":
            value: int | float = int(aggregated)
        else:
            value = round(aggregated, 4)
        features[name] = VerifiedFeature(
            name=name,
            value=value,
            evidence_ids=[evidence_id for evidence_id, _ in values],
            method=aggregation,
        )

    def extract(self, evidences: list[MarketEvidence]) -> EvidenceFeatureSet:
        by_type: dict[EvidenceType, list[MarketEvidence]] = {
            evidence_type: [] for evidence_type in EvidenceType
        }
        groups: dict[tuple[str, str], list[MarketEvidence]] = {}
        for evidence in evidences:
            if self.accepts(evidence):
                groups.setdefault(self._entity_key(evidence), []).append(evidence)
        aliases: dict[str, list[str]] = {}
        for group in groups.values():
            # Preferir captura com preço observável e conteúdo mais completo; conservar toda proveniência.
            representative = max(
                group,
                key=lambda ev: (
                    _price_brl(ev.sanitized_data) is not None,
                    len(str(ev.sanitized_data)),
                    ev.collected_at.isoformat(),
                ),
            )
            aliases[representative.id] = [ev.id for ev in group]
            by_type[representative.evidence_type].append(representative)

        features: dict[str, VerifiedFeature] = {}
        self._add_count_feature(
            features,
            name="ad_count",
            evidences=by_type[EvidenceType.PAID_COMPETITION],
        )
        self._add_count_feature(
            features,
            name="competitor_offer_count",
            evidences=by_type[EvidenceType.OFFER],
        )
        self._add_count_feature(
            features,
            name="open_jobs_count",
            evidences=by_type[EvidenceType.JOB_MARKET],
        )
        self._add_count_feature(
            features,
            name="social_mentions_count",
            evidences=by_type[EvidenceType.SOCIAL_VOICE],
        )

        prices = [
            (evidence.id, price)
            for evidence in by_type[EvidenceType.OFFER]
            if self.price_period is None
            or observed_price_period(evidence.sanitized_data) == self.price_period
            if (price := _price_brl(evidence.sanitized_data)) is not None
        ]
        self._aggregate_numeric(
            features,
            name="market_median_price_brl",
            values=prices,
            aggregation="median",
        )

        search_evidence = by_type[EvidenceType.SEARCH_VOLUME]
        paid_evidence = by_type[EvidenceType.PAID_COMPETITION]
        job_evidence = by_type[EvidenceType.JOB_MARKET]
        trends_evidence = by_type[EvidenceType.TRENDS]
        series_metrics = {
            evidence.id: self._trends_metrics(evidence.sanitized_data)
            for evidence in trends_evidence
        }
        for name, source, aggregation in (
            ("monthly_search_volume", search_evidence, "sum"),
            ("competition_index", search_evidence + paid_evidence, "mean"),
            ("cpc_brl", search_evidence + paid_evidence, "median"),
            ("salary_median_brl", job_evidence, "median"),
            ("average_interest", trends_evidence, "mean"),
            ("growth_trend_pct", trends_evidence, "mean"),
        ):
            observed = self._numeric_values(source, name)
            if name in {"average_interest", "growth_trend_pct"}:
                observed_ids = {evidence_id for evidence_id, _ in observed}
                observed.extend(
                    (evidence_id, metrics[name])
                    for evidence_id, metrics in series_metrics.items()
                    if name in metrics and evidence_id not in observed_ids
                )
            self._aggregate_numeric(
                features,
                name=name,
                values=observed,
                aggregation=aggregation,
            )

        return EvidenceFeatureSet(
            features={
                name: VerifiedFeature(
                    name=feature.name,
                    value=feature.value,
                    method=feature.method,
                    evidence_ids=list(
                        dict.fromkeys(
                            alias
                            for eid in feature.evidence_ids
                            for alias in aliases.get(eid, [eid])
                        )
                    ),
                )
                for name, feature in features.items()
            }
        )
