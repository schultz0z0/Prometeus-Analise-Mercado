import json
from pathlib import Path
import httpx
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.apify.registry import ApifyActorRegistry

s=AppSettings()
registry=ApifyActorRegistry.from_settings(s)
report={}
with httpx.Client(timeout=30,headers={'Authorization':f'Bearer {s.APIFY_TOKEN}'}) as client:
    for name in ['google_search','google_trends','youtube_comments']:
        spec=registry.require(name)
        response=client.get(f'{s.APIFY_BASE_URL.rstrip("/")}/actors/{spec.actor_path}/runs',params={'limit':2,'desc':'true'})
        response.raise_for_status()
        report[name]=[{k:x.get(k) for k in ['id','status','startedAt','finishedAt','usageTotalUsd','statusMessage']} for x in response.json()['data']['items']]
Path(__file__).with_name('remote-observation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
