import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_collection_attempts_migration_preserves_legacy_and_is_reversible():
    path = Path("migrations/versions/0014_collection_attempts.py")
    assert path.exists(), "collection attempt migration must exist"
    spec = importlib.util.spec_from_file_location("attempt_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "0013_workflow_reliability"
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE analyses (id VARCHAR(64) PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE tool_runs (id VARCHAR(64) PRIMARY KEY)"))
        conn.execute(
            sa.text(
                "CREATE TABLE research_plans (id TEXT PRIMARY KEY, budget_limit_usd FLOAT NOT NULL)"
            )
        )
        conn.execute(sa.text("CREATE TABLE market_evidences (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO research_plans VALUES ('legacy', 5)"))
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()
        assert "tool_run_attempts" in sa.inspect(conn).get_table_names()
        cols = {c["name"] for c in sa.inspect(conn).get_columns("tool_run_attempts")}
        assert {
            "tool_run_id",
            "tenant_id",
            "task_key",
            "attempt_index",
            "provider_run_id",
            "next_attempt_at",
            "diagnosis",
        } <= cols
        budget = next(
            c
            for c in sa.inspect(conn).get_columns("research_plans")
            if c["name"] == "budget_limit_usd"
        )
        assert budget["nullable"]
        assert (
            conn.execute(
                sa.text("SELECT budget_limit_usd FROM research_plans WHERE id='legacy'")
            ).scalar_one()
            == 5
        )
        assert conn.execute(sa.text("SELECT count(*) FROM tool_run_attempts")).scalar_one() == 0
        module.downgrade()
        assert "tool_run_attempts" not in sa.inspect(conn).get_table_names()
    engine.dispose()
