import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_ipd_migration_upgrade_and_downgrade_preserve_prior_rows():
    path = Path("migrations/versions/0010_historical_ipd_metadata.py")
    spec = importlib.util.spec_from_file_location("ipd_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE historical_courses (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE historical_funnel_records (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO historical_courses VALUES ('prior-course')"))
        conn.execute(sa.text("INSERT INTO historical_funnel_records VALUES ('prior-funnel')"))
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade()
        assert (
            conn.execute(sa.text("SELECT curriculum_text FROM historical_courses")).scalar_one()
            == ""
        )
        assert conn.execute(
            sa.text("SELECT price_period, cohort_status FROM historical_funnel_records")
        ).one() == ("unknown", "UNKNOWN")
        module.downgrade()
        assert (
            conn.execute(sa.text("SELECT id FROM historical_courses")).scalar_one()
            == "prior-course"
        )
        assert [c["name"] for c in sa.inspect(conn).get_columns("historical_funnel_records")] == [
            "id"
        ]
    engine.dispose()
