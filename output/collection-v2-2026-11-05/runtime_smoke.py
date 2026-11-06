import json
from pathlib import Path
import httpx

art = Path(__file__).parent
key = (art.parents[1] / 'var/auth/admin.key').read_text(encoding='utf-8').strip()
with httpx.Client(base_url='http://127.0.0.1:8000', headers={'Authorization': f'Bearer {key}'}, timeout=40) as client:
    ready = client.get('/health/ready')
    ready.raise_for_status()
    settings = client.get('/v1/settings')
    settings.raise_for_status()
    settings = settings.json()
    assert settings['apify_max_charge'] is None
    assert settings['apify_spending_mode'] == 'monitor_only'
    assert settings['apify_discovery_mcp_enabled'] is True
    result = client.post('/v1/settings/apify/discovery', json={'tool': 'fetch-actor-details', 'arguments': {'actor': 'apify/google-search-scraper'}})
    result.raise_for_status()
    body = result.json()
    assert body['status'] == 'ok', body.get('error_code')
    report = {'ready': ready.status_code, 'apify_spending_mode': settings['apify_spending_mode'], 'apify_max_charge': settings['apify_max_charge'], 'discovery_mcp': body['status'], 'discovery_untrusted': body.get('untrusted'), 'ai_mode': settings.get('ai_mode'), 'jev_enabled': settings.get('jev_enabled'), 'llm_provider': settings.get('gen_llm_provider'), 'llm_model': settings.get('gen_llm_model'), 'oauth_connected': settings.get('chatgpt_oauth_connected')}
    (art / 'runtime-smoke.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
