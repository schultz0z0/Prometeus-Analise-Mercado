import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

art = Path(__file__).parent
stem = 'canary2' if '--second' in sys.argv else 'canary'
key = (art.parents[1] / 'var/auth/admin.key').read_text(encoding='utf-8').strip()
headers = {'Authorization': f'Bearer {key}'}
with httpx.Client(base_url='http://127.0.0.1:8000', headers=headers, timeout=40) as client:
    if '--submit' in sys.argv:
        previous = json.loads((art / 'canary.json').read_text(encoding='utf-8'))['analysis_id'] if '--second' in sys.argv else 'dffd0359-4a40-4cc4-be00-fc5bb74bf687'
        payload = {'proposal_data': {'validation_run': 'collection-v2-real-2026-11-05', 'notes': 'Homologação real da coleta sem teto monetário local, cobertura dirigida de concorrentes e recuperação diagnosticada. Preservar premissas de teste e histórico sintético ENS identificado; não registrar decisão comercial.'}}
        request_headers = {'Idempotency-Key': 'homologacao-collection-v2-20261105' + ('-r2' if '--second' in sys.argv else '')}
        response = client.post(f'/v1/analyses/{previous}/reanalyze', json=payload, headers=request_headers)
        response.raise_for_status()
        repeated = client.post(f'/v1/analyses/{previous}/reanalyze', json=payload, headers=request_headers)
        repeated.raise_for_status()
        data = response.json()
        assert data['analysis_id'] == repeated.json()['analysis_id']
        data.update(idempotency_verified=True, policy='collection-v2', submitted_at=datetime.now(UTC).isoformat())
        (art / f'{stem}.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(json.dumps(data), flush=True)
    identifier = json.loads((art / f'{stem}.json').read_text(encoding='utf-8'))['analysis_id']
    prior = None
    while True:
        try:
            response = client.get(f'/v1/analyses/{identifier}')
        except httpx.TransportError:
            if '--once' in sys.argv:
                raise
            time.sleep(5)
            continue
        response.raise_for_status()
        body = response.json()
        (art / f'{stem}-progress.json').write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
        steps = body['steps']
        active = next((s for s in reversed(steps) if s['status'] not in {'PLANNED', 'PENDING'}), None)
        counts = dict(Counter(r['status'] for r in body['tool_runs']))
        signature = (body['status'], json.dumps(counts, sort_keys=True), str(active))
        if signature != prior:
            summary = {'at': datetime.now(UTC).isoformat(), 'status': body['status'], 'step': {k: active[k] for k in ['step_number', 'name', 'status']} if active else None, 'runs': counts, 'observed_cost_usd': round(sum(r['cost_usd'] for r in body['tool_runs']), 6), 'attempts': sum(r.get('attempts_count', 0) for r in body['tool_runs'])}
            with (art / f'{stem}-timeline.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(summary) + '\n')
            print(json.dumps(summary), flush=True)
            prior = signature
        if body['status'] in {'COMPLETED', 'FAILED', 'BLOCKED', 'CANCELLED', 'WAITING_FOR_INPUT'}:
            if body['status'] == 'COMPLETED':
                response = client.get(f'/v1/analyses/{identifier}/dossier')
                response.raise_for_status()
                dossier = response.json()
                (art / f'{stem}-dossier.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'dossier_status': dossier.get('status'), 'benchmark': dossier.get('presentation', {}).get('competitive_benchmark', {})}, ensure_ascii=True)[:1800], flush=True)
            else:
                print(json.dumps({'blocking': body.get('blocking'), 'failed_steps': [{k:s.get(k) for k in ['step_number', 'name', 'error_message']} for s in steps if s['status'] == 'FAILED']}, ensure_ascii=True), flush=True)
            break
        if '--once' in sys.argv:
            break
        time.sleep(15)
