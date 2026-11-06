import asyncio
import json
from pathlib import Path
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.client import ApifyClient
from prometeus.infrastructure.apify.registry import ApifyActorRegistry


async def main():
    s=AppSettings()
    client=ApifyClient(api_token=s.APIFY_TOKEN,registry=ApifyActorRegistry.from_settings(s),base_url=s.APIFY_BASE_URL)
    try:
        result=await client.execute(PlannedToolCall(id='homologation-billing-control',capability='google_search',query='curso governança inteligência artificial seguros',rationale='Canário técnico de cobrança reconciliada, sem alimentar decisão comercial.',max_items=1,parameters={'country':'BR','language':'pt-BR'}),max_total_charge_usd=0.5)
        report={'run_id':result.run.run_id,'status':result.run.status,'build':result.run.build_number,'cost_usd':result.run.cost_usd,'max_charge_usd':0.5,'dataset_id':result.run.dataset_id,'raw_items_count':len(result.items),'billing_checked':True}
        Path(__file__).with_name('live-billing-control.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    finally:
        await client.aclose()


asyncio.run(main())
