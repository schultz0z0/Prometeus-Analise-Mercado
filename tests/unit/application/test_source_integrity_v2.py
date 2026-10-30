from prometeus.application.evidence_features import EvidenceFeatureExtractor
from prometeus.application.research_scope import normalize_geography
from prometeus.application.sanitization import EvidenceSanitizer
from prometeus.domain.configuration import AppSettings
from prometeus.domain.ports.market_sources import EvidenceType, MarketEvidence
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


def evidence(url, payload, evidence_id="one"):
    return MarketEvidence.create(
        analysis_id="v2",
        evidence_type=EvidenceType.JOB_MARKET,
        source_name="apify_linkedin_jobs",
        source_url=url,
        collector="test",
        title="Gerente de seguros",
        raw_payload=payload,
        sanitized_data=payload,
        evidence_id=evidence_id,
    )


def test_public_listing_identifier_is_preserved_but_description_phone_is_redacted():
    data, _ = EvidenceSanitizer().sanitize_payload(
        {
            "id": "4481932467",
            "title": "Gerente de seguros",
            "location": "São Paulo, Brazil",
            "description": "Contato: 11 99999-1234",
        }
    )
    assert data["id"] == "4481932467"
    assert "99999-1234" not in data["description"]
    unknown, _ = EvidenceSanitizer().sanitize_payload({"id": "11999991234"})
    assert unknown["id"] != "11999991234"


def test_redaction_markers_do_not_merge_distinct_jobs_but_repeated_job_urls_do():
    rows = [
        evidence(
            "https://br.linkedin.com/jobs/view/cargo-4481932467?trackingId=one",
            {"id": "[PHONE_REDACTED]", "location": "São Paulo, Brazil"},
            "one",
        ),
        evidence(
            "https://br.linkedin.com/jobs/view/cargo-4481932467?trackingId=two",
            {"id": "[PHONE_REDACTED]", "location": "São Paulo, Brazil"},
            "repeat",
        ),
        evidence(
            "https://br.linkedin.com/jobs/view/outro-4478805894",
            {"id": "[PHONE_REDACTED]", "location": "São Paulo, Brazil"},
            "two",
        ),
    ]
    feature = EvidenceFeatureExtractor(geography="Brasil").extract(rows).require("open_jobs_count")
    assert feature.value == 2
    assert set(feature.evidence_ids) == {"one", "repeat", "two"}


def test_country_description_does_not_discard_brazil_but_narrow_region_is_preserved():
    row = evidence("https://linkedin.com/jobs/view/4481932467", {"location": "São Paulo, Brazil"})
    assert EvidenceFeatureExtractor(
        geography="Brasil como contexto do programa e do mercado estudado; participação online de qualquer localidade."
    ).accepts(row)
    assert not EvidenceFeatureExtractor(geography="Rio de Janeiro, Brasil").accepts(row)
    assert not EvidenceFeatureExtractor(geography="Brasil").accepts(
        evidence("https://linkedin.com/jobs/view/4481932467", {"location": "Austin, TX"})
    )


def test_google_trends_sends_distinct_terms_not_comma_phrase():
    registry = ApifyActorRegistry.from_settings(
        AppSettings(_env_file=None, APIFY_ACTOR_GOOGLE_TRENDS="apify/google-trends-scraper@0.0.143")
    )
    payload = registry.build_input(
        PlannedToolCall(
            id="trends",
            capability="google_trends",
            query="MBA seguros, gestão de riscos",
            rationale="comparar",
            parameters={"geo": "BR", "time_range": "today 3-m"},
        )
    )
    assert payload["searchTerms"] == ["MBA seguros", "gestão de riscos"]
    assert payload["timeRange"] == "today 3-m"


def test_explicit_use_for_prevents_own_institution_ad_entering_competition():
    row = MarketEvidence.create(
        analysis_id="v2",
        evidence_type=EvidenceType.PAID_COMPETITION,
        source_name="meta",
        source_url="https://ens.edu.br",
        collector="test",
        title="MBA ENS",
        raw_payload={},
        sanitized_data={
            "_qualification": {
                "accepted": True,
                "own_institution": True,
                "use_for": ["institution_context"],
            }
        },
    )
    assert EvidenceFeatureExtractor().extract([row]).get("ad_count") is None


def test_redacted_listing_url_is_not_used_as_entity_key_for_distinct_unknown_jobs():
    rows = [
        evidence(
            "https://jobs.example/[PHONE_REDACTED]",
            {
                "id": "[PHONE_REDACTED]",
                "location": "São Paulo, Brazil",
                "description": "subscrição",
            },
            "first",
        ),
        evidence(
            "https://jobs.example/[PHONE_REDACTED]",
            {"id": "[PHONE_REDACTED]", "location": "São Paulo, Brazil", "description": "sinistros"},
            "second",
        ),
    ]
    assert (
        EvidenceFeatureExtractor(geography="Brasil").extract(rows).require("open_jobs_count").value
        == 2
    )


def test_restrictive_suffix_does_not_expand_city_scope_to_country():
    geography = "Brasil; somente Rio de Janeiro"
    assert normalize_geography(geography) == geography
    sao_paulo = evidence("https://jobs.example/1", {"location": "São Paulo, São Paulo, Brazil"})
    rio = evidence("https://jobs.example/2", {"location": "Rio de Janeiro, Rio de Janeiro, Brazil"})
    assert not EvidenceFeatureExtractor(geography=geography).accepts(sao_paulo)
    assert EvidenceFeatureExtractor(geography=geography).accepts(rio)


def test_narrow_scope_matches_brazil_alias_without_dropping_city():
    geography = "São Paulo, Brasil"
    assert normalize_geography(geography) == geography
    assert EvidenceFeatureExtractor(geography=geography).accepts(
        evidence("https://jobs.example/1", {"location": "São Paulo, São Paulo, Brazil"})
    )
    assert not EvidenceFeatureExtractor(geography=geography).accepts(
        evidence("https://jobs.example/2", {"location": "Rio de Janeiro, Brazil"})
    )
