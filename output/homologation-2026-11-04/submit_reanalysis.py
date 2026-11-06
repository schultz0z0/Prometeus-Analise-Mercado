import json
from pathlib import Path
import httpx

ART=Path(__file__).resolve().parent
key=(ART.parents[1]/'var/auth/admin.key').read_text(encoding='utf-8').strip()
previous=json.loads((ART/'canary.json').read_text())['analysis_id']
with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':f'Bearer {key}','Idempotency-Key':'homologacao-20261104-r2'},timeout=45) as client:
    payload={'proposal_data':{'validation_run':'homologacao-real-2026-11-04-r2','notes':'Reanálise controlada de homologação após reconexão do provedor e correção de compromissos de orçamento. Premissas financeiras são exclusivamente dados de teste, sem aprovação de oferta. Preservar lacunas e natureza sintética do histórico ENS.'}}
    first=client.post(f'/v1/analyses/{previous}/reanalyze',json=payload)
    first.raise_for_status()
    second=client.post(f'/v1/analyses/{previous}/reanalyze',json=payload)
    second.raise_for_status()
    assert first.json()['analysis_id']==second.json()['analysis_id']
    assert first.json()['previous_analysis_id']==previous
    report={**first.json(),'idempotency_verified':True,'budget_policy':'analysis-caps-v1','root_limit_usd':5.0}
    (ART/'canary2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
