from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from prometeus.infrastructure.db.models import MarketEvidenceModel, ResearchPlanModel, ToolRunModel


def compiled_table(model: type[object]) -> str:
    return str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))


def test_research_plan_persists_understanding_plan_and_skill_snapshots() -> None:
    sql = compiled_table(ResearchPlanModel)

    assert "understanding_snapshot" in sql
    assert "plan_snapshot" in sql
    assert "snapshot_hash" in sql
    assert "skill_snapshots" in sql


def test_tool_run_persists_provider_provenance_and_outcome() -> None:
    sql = compiled_table(ToolRunModel)

    for column in (
        "planned_call_id",
        "capability",
        "provider",
        "actor_id",
        "provider_run_id",
        "dataset_id",
        "raw_items_count",
        "valid_items_count",
        "cost_usd",
        "error_code",
    ):
        assert column in sql


def test_market_evidence_can_reference_the_tool_run_that_produced_it() -> None:
    sql = compiled_table(MarketEvidenceModel)
    assert "tool_run_id" in sql

