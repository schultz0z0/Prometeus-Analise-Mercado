import json

import pytest

from prometeus.application.evidence_projection import build_qualification_context
from prometeus.infrastructure.apify.normalizers import normalize_ad


def snapshot_ad():
    return {
        "ad_archive_id": "123",
        "page_name": "Escola Exemplo",
        "snapshot": {
            "body": {"text": "Formação em governança de IA e privacidade. Inscreva-se."},
            "title": "Curso de privacidade",
            "link_url": "https://escola.br/curso",
        },
    }


def test_nested_meta_creative_reaches_judgment_with_exact_provenance():
    raw = snapshot_ad()
    ad = normalize_ad(raw)
    assert ad.ad_id == "123"
    assert ad.ad_text.value == raw["snapshot"]["body"]["text"]
    assert ad.ad_text.pointer == "/snapshot/body/text"
    assert ad.headline.pointer == "/snapshot/title"
    assert ad.cta_url.pointer == "/snapshot/link_url"
    context = build_qualification_context(raw, "PAID_COMPETITION")
    assert context["ad_copy"] == ad.ad_text.value
    assert context["headline"] == "Curso de privacidade"
    assert context["target_url"] == "https://escola.br/curso"
    assert context["field_provenance"]["ad_copy"]["pointer"] == "/snapshot/body/text"


def test_flat_creatives_remain_compatible_and_take_precedence():
    raw = {
        **snapshot_ad(),
        "text": "Texto observado no formato plano",
        "headline": "Título plano",
        "cta_url": "https://escola.br/plano",
    }
    ad = normalize_ad(raw)
    assert ad.ad_text.value == raw["text"] and ad.ad_text.pointer == "/text"
    assert ad.headline.value == raw["headline"]
    assert ad.cta_url.value == raw["cta_url"]


@pytest.mark.parametrize("snapshot", [None, [], {"body": []}, {"body": {"text": {}}}])
def test_malformed_optional_creative_fields_do_not_become_invented_text(snapshot):
    ad = normalize_ad({"ad_archive_id": "123", "snapshot": snapshot})
    assert ad.ad_text.value is None
    assert ad.headline.value is None


def test_carousel_creatives_retain_individual_text_and_source_pointers():
    raw = {
        "ad_archive_id": "123",
        "snapshot": {
            "cards": [
                {
                    "title": "Curso IA",
                    "body": "Governança de modelos",
                    "link_url": "https://escola.br/ia",
                },
                {"title": "Curso LGPD", "body": {"text": "Proteção de dados"}},
            ]
        },
    }
    context = build_qualification_context(raw, "PAID_COMPETITION")
    assert context["creative_cards"][0]["ad_copy"] == "Governança de modelos"
    assert context["creative_cards"][1]["ad_copy"] == "Proteção de dados"
    assert (
        context["creative_cards"][1]["field_provenance"]["ad_copy"]["pointer"]
        == "/snapshot/cards/1/body/text"
    )


def test_large_creatives_respect_projection_budget_with_omission_diagnostics():
    raw = snapshot_ad()
    raw["snapshot"]["body"]["text"] = "Informação de curso. " * 2000
    raw["snapshot"]["cards"] = [{"body": "Conteúdo de curso. " * 20}] * 100
    context = build_qualification_context(raw, "PAID_COMPETITION", budget=2000)
    assert len(json.dumps(context, ensure_ascii=False)) <= 2000
    assert context["omissions"]
    assert raw["snapshot"]["body"]["text"].endswith("Informação de curso. ")


def test_single_long_carousel_card_keeps_a_useful_excerpt_within_budget():
    raw = {
        "ad_archive_id": "123",
        "snapshot": {
            "cards": [
                {"title": "Curso de IA", "body": "Governança de modelos e privacidade. " * 700},
            ]
        },
    }
    context = build_qualification_context(raw, "PAID_COMPETITION", budget=2000)
    assert len(json.dumps(context, ensure_ascii=False)) <= 2000
    assert len(context["creative_cards"]) == 1
    assert context["creative_cards"][0]["ad_copy"].startswith("Governança de modelos")
    assert any(item["field"] == "/snapshot/cards/0/body" for item in context["omissions"])
