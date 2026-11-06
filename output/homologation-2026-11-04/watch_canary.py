import json
import time
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
import httpx

ART=Path(__file__).resolve().parent
ROOT=ART.parents[1]
key=(ROOT/'var/auth/admin.key').read_text(encoding='utf-8').strip()
stem='canary'+(sys.argv[1] if len(sys.argv)>1 else '')
analysis_id=json.loads((ART/f'{stem}.json').read_text())['analysis_id']
with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':f'Bearer {key}'},timeout=30) as client:
    for _ in range(100):
        r=client.get(f'/v1/analyses/{analysis_id}')
        r.raise_for_status()
        body=r.json()
        (ART/f'{stem}-progress.json').write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf-8')
        row={'time':datetime.now(UTC).isoformat(),'status':body['status'],'latest_step':body['steps'][-1]['name'] if body['steps'] else None,'run_statuses':dict(Counter(x['status'] for x in body['tool_runs'])),'reported_cost_usd':round(sum(x['cost_usd'] for x in body['tool_runs']),6)}
        print(json.dumps(row),flush=True)
        with (ART/f'{stem}-timeline.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(row)+'\n')
        if body['status'] not in {'QUEUED','RUNNING'}:
            dossier=client.get(f'/v1/analyses/{analysis_id}/dossier')
            if dossier.status_code==200:
                (ART/f'{stem}-dossier.json').write_text(json.dumps(dossier.json(),ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'terminal_status':body['status'],'blocking':body.get('blocking'),'recommendation':body.get('recommendation'),'dossier_http_status':dossier.status_code}),flush=True)
            break
        time.sleep(30)
    else:
        raise SystemExit('Watch interval ended; analysis requires continued inspection')
