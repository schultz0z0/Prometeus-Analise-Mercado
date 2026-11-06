import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from postgres_validation import target

url = target()  # Verifica label e bind do único container temporário criado nesta auditoria.
env = {**os.environ, 'DATABASE_URL':url}
for revision in ('0012_sector_radar_snapshots','head'):
    command='downgrade' if revision!='head' else 'upgrade'
    subprocess.run([sys.executable,'-m','alembic',command,revision],env=env,check=True)

async def check():
    engine=create_async_engine(url)
    async with engine.connect() as connection:
        assert await connection.scalar(text('select count(*) from analyses')) == 1
        assert await connection.scalar(text('select count(*) from scoring_results')) == 1
        assert await connection.scalar(text('select version_num from alembic_version')) == '0013_workflow_reliability'
    await engine.dispose()
asyncio.run(check())
Path('output/audit-remediation/migration-roundtrip.json').write_text(json.dumps({'rollback_0013_to_0012':'passed','upgrade_0012_to_0013':'passed','prior_analyses_and_scores_preserved':True},indent=2),encoding='utf-8')
print('PostgreSQL migration rollback/upgrade preserved fixture analysis and score.')
