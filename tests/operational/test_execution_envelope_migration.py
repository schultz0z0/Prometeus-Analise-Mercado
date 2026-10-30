import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_execution_envelope_migration_follows_real_head_and_is_reversible():
    path = Path("migrations/versions/0011_execution_envelopes.py")
    spec = importlib.util.spec_from_file_location("envelope_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "0010_historical_ipd_metadata"
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE analyses (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO analyses VALUES ('prior')"))
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()
        columns = {c["name"] for c in sa.inspect(conn).get_columns("execution_envelopes")}
        assert {
            "analysis_id",
            "tenant_id",
            "stage",
            "attempt",
            "input_hash",
            "cache_key",
            "component_versions",
            "model",
            "mode",
            "outcome",
            "usage",
            "cost_usd",
            "cost_status",
        } <= columns
        cost = next(
            c for c in sa.inspect(conn).get_columns("execution_envelopes") if c["name"] == "cost_usd"
        )
        assert cost["nullable"] is True
        module.downgrade()
        assert "execution_envelopes" not in sa.inspect(conn).get_table_names()
        assert conn.execute(sa.text("SELECT id FROM analyses")).scalar_one() == "prior"
    engine.dispose()

