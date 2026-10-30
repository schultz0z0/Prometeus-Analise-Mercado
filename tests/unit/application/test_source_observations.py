"""Regressões e contratos de observações canônicas por fonte (Tarefa 1.1).

Verifica variantes de schema/build, descriptionText, listas aninhadas, datas
numéricas, salário textual, preço parcelado, hasData e isPartial escalar/lista,
e garante que reordenar chaves não apaga campos críticos.
"""

from __future__ import annotations

from prometeus.domain.evidence_observations import (
    JobObservation,
    ObservationStatus,
    OfferObservation,
    PageAcquisition,
    TrendSeries,
)
from prometeus.infrastructure.apify.normalizers import (
    normalize_crawler_page,
    normalize_job,
    normalize_trends,
)


def test_trends_normalizer_handles_scalar_and_list_is_partial_and_preserves_timestamps() -> None:
    raw_payload = {
        "term": "litigância predatória",
        "interestOverTime_timelineData": [
            {
                "time": "1635033600",
                "formattedTime": "24 de out. de 2021",
                "formattedAxisTime": "24 de out. de 2021",
                "value": [15],
                "hasData": [True],
                "isPartial": [True],  # variante de lista observada
            },
            {
                "time": "1635638400",
                "formattedTime": "31 de out. de 2021",
                "value": [0],
                "hasData": True,  # variante escalar
                "isPartial": False,  # variante escalar
            },
            {
                "time": "1636243200",
                "formattedTime": "7 de nov. de 2021",
                "value": [30],
                "hasData": True,
                "isPartial": True,
            },
        ],
    }

    obs = normalize_trends(raw_payload, source_url="https://trends.google.com")
    assert isinstance(obs, TrendSeries)
    assert obs.total_points == 3
    assert obs.positive_points == 2
    assert obs.partial_points == 2
    # Timestamps devem ser preservados exatamente como observados, sem máscara telefônica
    assert obs.points[0].time == "1635033600"
    assert obs.points[0].is_partial is True
    assert obs.points[1].time == "1635638400"
    assert obs.points[1].is_partial is False
    assert obs.points[2].time == "1636243200"
    assert obs.points[2].is_partial is True
    assert obs.average_interest == 15.0


def test_job_normalizer_extracts_descriptions_and_nested_skills() -> None:
    raw_job = {
        "jobId": "4481932467",
        "title": "Gerente de Sinistros e Riscos",
        "companyName": "Seguradora Nacional S.A.",
        "location": "São Paulo, Brazil",
        "descriptionText": "Responsável por liderar a regulação de sinistros e subscrição de riscos patrimoniais.",
        "descriptionHtml": "<div><p>Responsável por liderar a regulação de sinistros e subscrição de riscos patrimoniais.</p></div>",
        "skills": ["Subscrição", "Regulação de Sinistros", "Resseguro"],
        "salary": "A combinar na faixa de R$ 15.000 a R$ 20.000 CLT",
        "postedDate": "2026-09-15",
    }

    obs = normalize_job(raw_job, source_url="https://linkedin.com/jobs/view/4481932467")
    assert isinstance(obs, JobObservation)
    assert obs.title.value == "Gerente de Sinistros e Riscos"
    assert obs.title.status == ObservationStatus.OBSERVED
    assert obs.description_text.value == raw_job["descriptionText"]
    assert obs.description_text.status == ObservationStatus.OBSERVED
    assert "Subscrição" in obs.requirements_skills
    assert "Regulação de Sinistros" in obs.requirements_skills
    assert obs.salary_text.value == "A combinar na faixa de R$ 15.000 a R$ 20.000 CLT"
    # Moeda ou país ausente não deve ser inferido arbitrariamente
    assert obs.country.status in {ObservationStatus.OBSERVED, ObservationStatus.MISSING}


def test_job_normalizer_falls_back_to_html_if_text_missing() -> None:
    raw_job = {
        "id": "123",
        "title": "Analista de Riscos",
        "descriptionHtml": "<p>Análise de apólices e cálculo atuarial.</p>",
    }
    obs = normalize_job(raw_job, source_url="https://linkedin.com/jobs/view/123")
    assert "Análise de apólices e cálculo atuarial." in (obs.description_text.value or "")


def test_price_and_offer_normalizer_parses_installments_without_inventing_total() -> None:
    raw_crawler = {
        "url": "https://faculdade.com.br/pos-seguros",
        "pageTitle": "Pós-Graduação em Gestão de Seguros",
        "httpStatusCode": 200,
        "text": "O curso conta com 360 horas de carga horária. Mensalidade de R$ 950 em 18 vezes no boleto.",
        "pricing": {
            "installments": 18,
            "installment_value": 950.0,
            "currency": "BRL",
        },
    }

    obs = normalize_crawler_page(raw_crawler, source_url="https://faculdade.com.br/pos-seguros")
    assert isinstance(obs, OfferObservation)
    assert obs.workload_hours.value == 360
    assert obs.pricing is not None
    assert obs.pricing.installments.value == 18
    assert obs.pricing.installment_value.value == 950.0
    assert obs.pricing.currency.value == "BRL"
    # Preço total calculado determinístico sem inventar moeda se ela não existisse
    assert obs.pricing.total_price.value == 18 * 950.0


def test_page_acquisition_records_outcomes_for_404_and_blocked() -> None:
    raw_404 = {
        "url": "https://instituto.com/nao-existe",
        "httpStatusCode": 404,
        "error": "Not Found",
    }
    acq = normalize_crawler_page(raw_404, source_url="https://instituto.com/nao-existe")
    assert isinstance(acq, PageAcquisition)
    assert acq.outcome == "not_found"
    assert acq.status_code == 404


def test_key_reordering_preserves_observation_identity_and_critical_fields() -> None:
    payload_a = {
        "title": "Especialista",
        "descriptionText": "Descricao de teste",
        "location": "Brasil",
    }
    payload_b = {
        "location": "Brasil",
        "descriptionText": "Descricao de teste",
        "title": "Especialista",
    }
    obs_a = normalize_job(payload_a, source_url="https://test.com/1")
    obs_b = normalize_job(payload_b, source_url="https://test.com/1")
    assert obs_a.title.value == obs_b.title.value
    assert obs_a.description_text.value == obs_b.description_text.value
    assert obs_a.canonical_hash() == obs_b.canonical_hash()

