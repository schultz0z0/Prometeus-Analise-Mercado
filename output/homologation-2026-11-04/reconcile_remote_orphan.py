import json
from pathlib import Path
import httpx
from prometeus.domain.configuration import AppSettings
from prometeus.domain.research import PlannedToolCall
from prometeus.infrastructure.apify.registry import ApifyActorRegistry

ART=Path(__file__).resolve().parent
body=json.loads((ART/'canary-progress.json').read_text(encoding='utf-8'))
plan=next(x for x in body['steps'] if x['step_number']==6)['output_summary']
call=PlannedToolCall.model_validate(next(x for x in plan['tool_calls'] if x['capability']=='google_trends'))
settings=AppSettings()
registry=ApifyActorRegistry.from_settings(settings)
expected=registry.build_input(call)
run_id='0g2XRUqe7wr2um7PU'
base=settings.APIFY_BASE_URL.rstrip('/')
with httpx.Client(headers={'Authorization':f'Bearer {settings.APIFY_TOKEN}'},timeout=30) as client:
    response=client.get(f'{base}/actor-runs/{run_id}')
    response.raise_for_status()
    run=response.json()['data']
    assert run['id']==run_id and run['startedAt'].startswith('2026-11-04T17:37:40')
    assert run['options']['build']==registry.require('google_trends').build
    inputs=client.get(f'{base}/key-value-stores/{run["defaultKeyValueStoreId"]}/records/INPUT')
    inputs.raise_for_status()
    assert all(inputs.json().get(k)==v for k,v in expected.items())
    before=run['status']
    if before in {'READY','RUNNING'}:
        response=client.post(f'{base}/actor-runs/{run_id}/abort',params={'gracefully':'false'})
        response.raise_for_status()
        run=response.json()['data']
    report={'run_id':run_id,'planned_call_id':call.id,'input_identity_confirmed':True,'before':before,'after':run['status'],'observed_cost_usd':run.get('usageTotalUsd'),'dataset_id':run.get('defaultDatasetId'),'reason':'Provider returned HTTP 502 during start/wait; local workflow had no confirmed remote identity. Stop orphaned paid run and reconcile without buying another run.'}
    (ART/'remote-orphan-reconciliation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
