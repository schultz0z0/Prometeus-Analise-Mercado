import json
from pathlib import Path
import httpx

ART=Path(__file__).resolve().parent
ROOT=ART.parents[1]
key=(ROOT/'var/auth/admin.key').read_text(encoding='utf-8').strip()
with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':f'Bearer {key}'},timeout=30) as client:
    r=client.post('/v1/analyses',headers={'Idempotency-Key':'homologacao-20261104-cancel-01'},json={'tenant_id':'ens','course_name':'Teste controlado de cancelamento imediato','proposal_data':{'validation_run':'cancelamento-homologacao-2026-11-04','notes':'Cancelar imediatamente, sem coleta externa.'}})
    r.raise_for_status()
    analysis_id=r.json()['analysis_id']
    before=client.get(f'/v1/analyses/{analysis_id}').json()
    if before['status'] != 'CANCELLED':
        cancelled=client.post(f'/v1/analyses/{analysis_id}/cancel')
        cancelled.raise_for_status()
    after=client.get(f'/v1/analyses/{analysis_id}').json()
    assert after['status']=='CANCELLED'
    assert not after['tool_runs']
    report={'analysis_id':analysis_id,'status':after['status'],'tool_runs':len(after['tool_runs'])}
    (ART/'cancellation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
