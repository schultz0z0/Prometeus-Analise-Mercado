"""Testes unitários para validação de integridade e conformidade de todos os Decision Packs YAML."""

from pathlib import Path

import pytest
import yaml

from prometeus.domain.ports.decision_model import DecisionPack, DecisionType

PACKS_DIR = Path("config/decision-packs")

EXPECTED_PACK_IDS = {
    "readiness-v1",
    "taxonomy-v1",
    "keywords-relevance-v1",
    "comparable-fit-v1",
    "sentiment-v1",
    "syllabus-fit-v1",
    "evidence-support-v1",
    "contradiction-check-v1",
}


def test_all_expected_packs_exist() -> None:
    yaml_files = list(PACKS_DIR.glob("*.yaml"))
    pack_stems = {f.stem for f in yaml_files}
    assert EXPECTED_PACK_IDS.issubset(pack_stems), (
        f"Faltam packs em {PACKS_DIR}: {EXPECTED_PACK_IDS - pack_stems}"
    )


@pytest.mark.parametrize("pack_id", list(EXPECTED_PACK_IDS))
def test_pack_schema_and_integrity(pack_id: str) -> None:
    file_path = PACKS_DIR / f"{pack_id}.yaml"
    assert file_path.exists(), f"Arquivo {file_path} não encontrado"

    with file_path.open("r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    pack = DecisionPack.model_validate(raw_data)

    assert pack.pack_id == pack_id
    assert pack.schema_version == 1
    assert pack.owner == "Agência Prometeus"
    assert len(pack.question) > 10
    assert 0.0 < pack.review_threshold < 1.0

    if pack.decision_type == DecisionType.CHOICE:
        assert len(pack.options) >= 2, f"Pack Choice {pack_id} precisa de ao menos 2 opções"
        assert len(pack.rubric) == len(pack.options), f"Rubric incompleta no pack {pack_id}"
    elif pack.decision_type == DecisionType.SCORE:
        assert pack.min_score < pack.max_score
        assert len(pack.rubric) >= 2
