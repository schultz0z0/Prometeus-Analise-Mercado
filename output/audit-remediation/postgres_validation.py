"""Integration check against a disposable labelled PostgreSQL container only."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.domain.analyses import AnalysisStatus, ConcurrentAnalysisUpdateError
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.backup import BackupRestoreManager
from prometeus.infrastructure.db.models import AnalysisModel, Base, ScoringResultModel

def target():
    metadata=json.loads(subprocess.check_output(['docker','inspect','prometeus-remediation-pg'],text=True))[0]
    assert metadata['Config']['Labels']['prometeus.audit']=='remediation-20261104'
    port=metadata['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
    assert metadata['NetworkSettings']['Ports']['5432/tcp'][0]['HostIp']=='127.0.0.1'
    return f'postgresql+asyncpg://postgres:audit-test-only@127.0.0.1:{port}/prometeus_test'

async def main(url):
    engine=create_async_engine(url)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    settings=AppSettings(_env_file=None,APP_ENV='test',DATABASE_URL=url,SERVICE_API_KEYS='')
    async def create():
        async with factory() as session:
            result=await CreateAnalysisUseCase(session,settings).execute(CreateAnalysisCommand('ens','PG fixture',{},'same-concurrent-key','test'))
            await session.commit()
            return result.analysis_id
    ids=await asyncio.gather(create(),create())
    assert len(set(ids))==1
    async with factory() as worker,factory() as caller:
        analysis=await AnalysisRepository(worker).get_by_id(ids[0])
        other=await AnalysisRepository(caller).get_by_id(ids[0])
        other.cancel('test')
        await AnalysisRepository(caller).save(other)
        await caller.commit()
        try:
            await AnalysisRepository(worker).save(analysis)
        except ConcurrentAnalysisUpdateError:
            await worker.rollback()
        else:
            raise AssertionError('Stale update accepted')
        assert (await AnalysisRepository(worker).get_by_id(ids[0])).status==AnalysisStatus.CANCELLED
    async with factory() as session:
        session.add(ScoringResultModel(id='pg-score',analysis_id=ids[0],profile_id='portfolio-v2',viability_score=40,coverage_score=.5,confidence_score=.6,partial_score=40,recommendation='INSUFFICIENT_EVIDENCE'))
        await session.commit()
    with TemporaryDirectory(prefix='prometeus-pg-test-') as directory:
        path=Path(directory)/'backup.json'
        async with factory() as session:
            manifest=await BackupRestoreManager(session).create_backup(path)
        assert set(manifest.table_counts)==set(Base.metadata.tables)
        async with factory() as session:
            await BackupRestoreManager(session).restore_backup(path)
            assert await session.scalar(select(func.count()).select_from(ScoringResultModel))==1
            assert await session.scalar(select(func.count()).select_from(AnalysisModel))==1
    async with engine.connect() as connection:
        head=await connection.scalar(text('select version_num from alembic_version'))
        assert head=='0013_workflow_reliability'
    await engine.dispose()
    report={'database':'isolated-postgresql-16','migration_head':head,'concurrent_idempotency':'passed','stale_cancel_protection':'passed','full_backup_restore_fk':'passed','table_count':len(Base.metadata.tables)}
    Path('output/audit-remediation/postgres-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    url=target()
    env={**os.environ,'DATABASE_URL':url}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True)
    asyncio.run(main(url))
