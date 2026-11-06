import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.ecosystem_presentation import build_ecosystem_presentation_blocks
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.models import AnalysisModel


async def main():
    engine = create_async_engine(AppSettings().DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        identifier = '9cb4f98e-60b5-46d9-998e-5ad81ebe7d86'
        analysis = await session.get(AnalysisModel, identifier)
        facts = await DossierSynthesisService(session, None).build_facts(identifier)
        blocks = build_ecosystem_presentation_blocks(analysis.proposal_data, facts, 24)
        benchmark = blocks['competitive_benchmark']
        result = {
            'analysis_status': analysis.status,
            'benchmark': {k:v for k,v in benchmark.items() if k != 'rows'},
            'rows': [{k:row.get(k) for k in ['name','execution_status','evidence_status','offers']} for row in benchmark['rows']],
        }
        Path('/app/var/collection-facts-inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True))
    await engine.dispose()


asyncio.run(main())
