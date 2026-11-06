import json
from pathlib import Path

import httpx

BASE = 'http://127.0.0.1:8000'
ART = Path(__file__).resolve().parent
ROOT = ART.parents[1]
key = (ROOT/'var/auth/admin.key').read_text(encoding='utf-8').strip()
report = {}
with httpx.Client(base_url=BASE, timeout=40) as client:
    for path in ['/health/live','/health/ready']:
        r = client.get(path)
        report[path] = {'status':r.status_code,'result':r.json().get('status')}
        assert r.status_code == 200
    assert client.get('/v1/analyses').status_code == 401
    r=client.post('/v1/session/login',json={'access_key':key},headers={'Origin':BASE})
    if r.status_code != 200:
        print('Login rejected, status:',r.status_code)
        raise SystemExit(1)
    report['session_cookie_httponly']='httponly' in r.headers.get('set-cookie','').lower()
    assert report['session_cookie_httponly']
    report['identity']=client.get('/v1/session').json()
    r=client.get('/v1/institutional/courses',params={'tenant_id':'ens'})
    assert r.status_code==200
    body=r.json()
    report['historical_courses']=len(body if isinstance(body,list) else body.get('courses',[]))
    assert report['historical_courses']==33
    assert client.get('/v1/institutional/courses?tenant_id=ens&tenant_id=another').status_code==403
    assert client.post('/v1/session/logout',headers={'Origin':'https://foreign.invalid'}).status_code==403
    settings=client.get('/v1/settings').json()
    report['runtime']={k:settings.get(k) for k in ['ai_mode','jev_enabled','gen_llm_provider','gen_llm_model','chatgpt_oauth_connected','apify_max_charge']}
    report['anonymous_protected']=True
    report['cross_tenant_rejected']=True
    report['cross_origin_rejected']=True
    assert client.post('/v1/session/logout',headers={'Origin':BASE}).status_code==200
    assert client.get('/v1/session').status_code==401
    report['logout_revokes_browser_session']=True
(ART/'http-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
