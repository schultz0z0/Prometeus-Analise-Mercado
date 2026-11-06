"""Servidor de fixtures isolado; não acessa os fornecedores ou banco do ambiente ENS."""
import asyncio
import os
import tempfile
import json
from pathlib import Path

import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker

directory=tempfile.TemporaryDirectory(prefix='prometeus-ui-smoke-')
os.environ.update(SERVICE_API_KEYS=json.dumps([{'key':'smoke-test-key-12345678901234567890','subject':'smoke','tenant_id':'ens','role':'admin'}]), CHATGPT_CREDENTIALS_PATH=str(Path(directory.name)/'missing.json'), GEN_LLM_PROVIDER='openai', OPENAI_API_KEY='', TYPESAFE_API_KEY='', APIFY_TOKEN='',WEBHOOK_SECRET='', WEBHOOK_TARGET_URL='')

from prometeus.entrypoints.rest.app import app
from prometeus.infrastructure.db.session import get_db_session
from prometeus.infrastructure.db.models import Base,ScoringResultModel,DossierModel
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.domain.analyses import Analysis,AnalysisRecommendation

engine=create_async_engine('sqlite+aiosqlite:///'+str(Path(directory.name)/'ui.sqlite3'))
factory=async_sessionmaker(engine,expire_on_commit=False)
async def seed():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    async with factory() as session:
        analysis=Analysis.create(tenant_id='ens',course_name='<img src=x onerror="window.__audit_xss=1">',proposal_data={'area':'Teste de segurança','level':'Extensão','modality':'Online','price_period':'total','ticket':100},correlation_id='smoke')
        analysis.start('smoke');analysis.complete(AnalysisRecommendation.INSUFFICIENT_EVIDENCE,'smoke')
        await AnalysisRepository(session).save(analysis)
        session.add(ScoringResultModel(id='smoke-score',analysis_id=analysis.id,profile_id='portfolio-v2',viability_score=0,coverage_score=0,confidence_score=0,partial_score=0,recommendation='INSUFFICIENT_EVIDENCE'))
        session.add(DossierModel(id='smoke-dossier',analysis_id=analysis.id,prompt_version='smoke',model_name='fixture',facts_hash='fixture',status='VERIFIED',executive_summary='Evidências insuficientes para decisão.',sections=[],claims=[],presentation={'contract_version':2,'economics':{'status':'not_calculable','message':'Premissas financeiras ausentes.','missing_inputs':['tax_rate_pct'],'scenarios':[]}}))
        await session.commit()
async def session_override():
    async with factory() as session:
        yield session
asyncio.run(seed())
app.dependency_overrides[get_db_session]=session_override
uvicorn.run(app,host='127.0.0.1',port=18778,log_level='warning')
