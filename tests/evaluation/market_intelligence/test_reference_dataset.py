"""Validação do conjunto de referência e esquema de rótulos humanos (Fase 0, Tarefa 0.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prometeus.domain.evaluation import AdjudicationStatus, ControlType, ReferenceExample

REF_DIR = Path(__file__).parent


@pytest.fixture
def manifest() -> dict[str, object]:
    path = REF_DIR / "manifest.json"
    assert path.exists(), f"Arquivo de manifesto não encontrado em {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def schema_raw() -> dict[str, object]:
    path = REF_DIR / "schema.json"
    assert path.exists(), f"Esquema JSON não encontrado em {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_json_contains_required_specification(schema_raw: dict[str, object]) -> None:
    required = schema_raw.get("required")
    assert isinstance(required, list)
    expected_fields = {
        "example_id",
        "capture_id",
        "entity_id",
        "source_name",
        "source_url",
        "scope",
        "expected_critical_fields",
        "extracted_snippets",
        "purpose",
        "utility",
        "category_exact",
        "family",
        "ambiguity_flag",
        "allowed_claims",
        "disallowed_claims",
        "control_type",
        "annotations",
        "adjudication",
    }
    assert expected_fields.issubset(set(required))


def test_manifest_items_validate_against_domain_model(manifest: dict[str, object]) -> None:
    items = manifest.get("items")
    assert isinstance(items, list) and len(items) > 0, "O manifesto deve conter itens rotulados."
    for raw in items:
        # Validação tipada estrita via Pydantic
        example = ReferenceExample.model_validate(raw)
        assert example.example_id.startswith("ref-")
        assert len(example.annotations) >= 2


def test_all_examples_have_double_independent_reviewers(manifest: dict[str, object]) -> None:
    items = manifest.get("items")
    assert isinstance(items, list)
    expected_reviewers = {"reviewer_ens_market", "reviewer_data_methodology"}
    for item in items:
        annotations = item.get("annotations", [])
        assert isinstance(annotations, list) and len(annotations) >= 2
        reviewers = {ann.get("reviewer_id") for ann in annotations if isinstance(ann, dict)}
        assert expected_reviewers.issubset(reviewers), (
            f"Exemplo {item.get('example_id')} deve conter anotações de {expected_reviewers}"
        )


def test_adjudication_rules_and_unresolved_handling(manifest: dict[str, object]) -> None:
    items = manifest.get("items")
    assert isinstance(items, list)
    for item in items:
        annotations = item.get("annotations", [])
        adjudication = item.get("adjudication", {})
        status = adjudication.get("status")
        utilities = [ann.get("utility") for ann in annotations if isinstance(ann, dict)]
        if len(set(utilities)) == 1:
            # Revisores concordaram
            assert status == AdjudicationStatus.AGREED.value, (
                f"Exemplo {item.get('example_id')} teve concordância mas status é {status}"
            )
            assert adjudication.get("final_utility") == utilities[0]
        else:
            # Houve desacordo material entre especialistas
            assert status in {
                AdjudicationStatus.ADJUDICATED.value,
                AdjudicationStatus.UNKNOWN_UNRESOLVED.value,
            }, (
                f"Exemplo {item.get('example_id')} teve desacordo mas status não é ADJUDICATED/UNKNOWN_UNRESOLVED: {status}"
            )
            assert adjudication.get("rationale"), "Adjudicação exige parecer técnico fundamentado."


def test_control_types_cover_mandatory_categories(manifest: dict[str, object]) -> None:
    items = manifest.get("items")
    assert isinstance(items, list)
    control_types = {item.get("control_type") for item in items}
    mandatory = {c.value for c in ControlType}
    assert mandatory.issubset(control_types), (
        f"O conjunto de referência deve cobrir todos os controles: {mandatory - control_types} ausentes"
    )


def test_entities_are_distinct_from_captures_and_denominators_reconciled(
    manifest: dict[str, object],
) -> None:
    items = manifest.get("items")
    assert isinstance(items, list)
    denominators = manifest.get("denominators", {})
    assert isinstance(denominators, dict)

    assert denominators.get("total_examples") == len(items)
    unique_entities = {item.get("entity_id") for item in items}
    assert denominators.get("unique_entities") == len(unique_entities)

    # Verifica separação estrita de chaves de capture vs entity
    for item in items:
        assert item.get("capture_id") != item.get("entity_id"), (
            f"Capture ID e Entity ID não devem ser idênticos: {item.get('example_id')}"
        )
