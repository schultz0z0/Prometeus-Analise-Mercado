import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def test_cms_and_collection_migrations_have_one_deployable_head():
    config = Config(str(Path("alembic.ini").resolve()))
    scripts = ScriptDirectory.from_config(config)
    assert len(scripts.get_heads()) == 1
    head = scripts.get_revision(scripts.get_heads()[0])
    assert set(head.down_revision) == {"0013_dossier_area_reviews", "0014_collection_attempts"}
    spec = importlib.util.spec_from_file_location(
        "cms_reviews_migration", Path("migrations/versions/0013_dossier_area_reviews.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE analyses (id VARCHAR(64) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO analyses VALUES ('existing')"))
        connection.execute(text("CREATE TABLE tool_run_attempts (id VARCHAR(64) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO tool_run_attempts VALUES ('retained')"))
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert "dossier_area_reviews" in inspect(connection).get_table_names()
        assert (
            connection.execute(text("SELECT id FROM tool_run_attempts")).scalar_one() == "retained"
        )
        assert connection.execute(text("SELECT id FROM analyses")).scalar_one() == "existing"
    engine.dispose()
