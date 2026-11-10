from prometeus.application.declared_curriculum import curriculum_text, declared_curriculum


def test_text_and_structured_modules_reach_curriculum_judgment_together():
    proposal = {
        "curriculum_text": "Objetivo geral de governança.",
        "curriculum": "Prática de auditoria.",
        "modules": [{"title": "Risco algorítmico", "topics": ["LGPD", "Validação"]}],
        "learning_outcomes": ["Auditar modelos"],
        "price": 1000,
    }
    result = declared_curriculum(proposal)
    assert result == {key: value for key, value in proposal.items() if key != "price"}
    result["modules"][0]["topics"].append("changed")
    assert len(proposal["modules"][0]["topics"]) == 2


def test_historical_comparison_includes_structured_curriculum_without_field_names():
    text = curriculum_text({"modules": [{"title": "Gestão de riscos", "topics": ["sinistros"]}]})
    assert "Gestão de riscos" in text and "sinistros" in text
    assert "title" not in text and "topics" not in text
    assert declared_curriculum({"price": 1000}) == {}
