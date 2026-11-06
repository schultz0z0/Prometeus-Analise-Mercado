import json
from pathlib import Path

from prometeus.application.decision_service import DecisionService
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient
from scripts.evaluate_jev import evaluate_single_pack, run_evaluation
from scripts.run_backtest import run_backtest_evaluation


async def test_expected_labels_never_reach_inference(tmp_path):
    captured = []

    class SpyModel(FakeDecisionClient):
        async def execute_choice(self, pack, context, evidence_ids=None):
            captured.append(context)
            return await super().execute_choice(pack, context, evidence_ids)

    dataset = tmp_path / "pack.json"
    dataset.write_text(
        json.dumps(
            {
                "pack_id": "keywords-relevance-v1",
                "samples": [
                    {
                        "input_context": {"course_title": "Course", "search_term": "term"},
                        "expected_output": "IRRELEVANT",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    await evaluate_single_pack(dataset, DecisionService(SpyModel()))
    assert captured == [{"course_title": "Course", "search_term": "term"}]


async def test_offline_evaluation_cannot_approve_gate_c(tmp_path):
    report = tmp_path / "ai.json"
    await run_evaluation(Path("tests/evaluation/jev"), report)
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["evaluation_mode"] == "simulation"
    assert result["gate_status"] == "PENDING_MANUAL_VALIDATION"


def test_fixture_backtest_cannot_approve_gate_d(tmp_path):
    report = tmp_path / "score.json"
    run_backtest_evaluation(
        "default-v1", Path("tests/evaluation/scoring/backtest_dataset.json"), report
    )
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["evaluation_mode"] == "fixture_simulation"
    assert result["gate_status"] == "PENDING_MANUAL_VALIDATION"
