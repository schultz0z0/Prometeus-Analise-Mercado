import pytest

from prometeus.application.offer_comparability import classify_competitor_offer
from prometeus.domain.research import CourseUnderstanding


def classify(**updates):
    values = {
        "evidence_type": "OFFER", "title": "MBA em Governança de IA",
        "source_url": "https://escola.br/cursos/governanca-ia", "data": {},
        "understanding": CourseUnderstanding(analysis_id="a", course_title="MBA em Governança de IA", level="MBA"),
        "relevant": True, "own": False, "sector": False,
    }
    values.update(updates)
    return classify_competitor_offer(**values)


def test_matching_observed_course_category_is_direct_without_price_or_hours():
    result = classify()
    assert result["is_offer"] and result["relation"] == "direct"
    assert result["observed_category"] == result["proposed_category"] == "mba"


def test_different_observed_course_category_is_adjacent():
    result = classify(title="Extensão em Governança de IA")
    assert result["is_offer"] and result["relation"] == "adjacent"


def test_observed_offer_with_missing_category_preserves_unconfirmed_relation():
    result = classify(title="Governança de IA", data={"workload_hours": 360})
    assert result["is_offer"] and result["relation"] == "unclassified"
    assert result["observed_category"] is None
    assert "observed_category" in result["missing_fields"]


def test_proposal_category_missing_cannot_turn_observed_mba_into_direct_competitor():
    result = classify(understanding=CourseUnderstanding(analysis_id="a", course_title="Governança de IA"))
    assert result["relation"] == "unclassified"


@pytest.mark.parametrize("updates", [
    {"relevant": False}, {"own": True}, {"sector": True}, {"evidence_type": "SOCIAL_VOICE"},
    {"source_url": "https://escola.br/noticias/mba-governanca-ia"},
    {"title": "Escola X", "source_url": "https://escola.br/"},
])
def test_context_news_and_institutional_homepages_never_become_confirmed_offers(updates):
    assert classify(**updates)["is_offer"] is False


def test_course_category_uses_observed_metadata_and_never_institution_category():
    result = classify(title="Governança de IA", data={"course_type": "curso livre", "institution_category": "executive_business"})
    assert result["observed_category"] == "curso_livre"
    assert result["relation"] == "adjacent"
