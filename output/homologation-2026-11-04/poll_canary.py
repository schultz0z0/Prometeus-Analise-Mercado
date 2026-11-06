import json
import sys
from pathlib import Path
import httpx

ART=Path(__file__).resolve().parent
ROOT=ART.parents[1]
key=(ROOT/'var/auth/admin.key').read_text(encoding='utf-8').strip()
stem='canary'+(sys.argv[1] if len(sys.argv)>1 else '')
analysis_id=json.loads((ART/f'{stem}.json').read_text())['analysis_id']
r=httpx.get(f'http://127.0.0.1:8000/v1/analyses/{analysis_id}',headers={'Authorization':f'Bearer {key}'},timeout=30)
r.raise_for_status()
body=r.json()
(ART/f'{stem}-progress.json').write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf-8')
from collections import Counter
print(json.dumps({'status':body['status'],'recommendation':body['recommendation'],'blocking':body['blocking'],'latest_step':{k:body['steps'][-1][k] for k in ['step_number','name','status']} if body['steps'] else None,'run_counts':dict(Counter(x['status'] for x in body['tool_runs'])),'latest_run':{k:body['tool_runs'][-1][k] for k in ['capability','status','valid_items_count','error_code']} if body['tool_runs'] else None,'errors':[{k:x[k] for k in ['capability','status','error_code']} for x in body['tool_runs'] if x.get('error_code')],'reported_cost_usd':sum(x['cost_usd'] for x in body['tool_runs'])},ensure_ascii=True,indent=2))
