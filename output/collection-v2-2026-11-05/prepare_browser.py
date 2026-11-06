"""Create a private browser session without exposing the access key or cookie."""
import json
import subprocess
import time
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[2]
state = root / 'var/auth/collection-browser.json'
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=30) as client:
    response = client.post('/v1/session/login', json={
        'access_key': (root / 'var/auth/admin.key').read_text(encoding='utf-8').strip(),
    }, headers={'Origin': 'http://127.0.0.1:8000'})
    response.raise_for_status()
    cookies = [{'name': c.name, 'value': c.value, 'domain': '127.0.0.1', 'path': '/',
                'expires': int(time.time()) + 28800, 'httpOnly': True, 'secure': False,
                'sameSite': 'Strict'} for c in client.cookies.jar]
    assert cookies
    state.write_text(json.dumps({'cookies': cookies, 'origins': []}), encoding='utf-8')
result = subprocess.run(['npx.cmd', '--yes', '--package', '@playwright/cli', 'playwright-cli',
                         '-s=prometeus-collectionverify', 'state-load', str(state)], capture_output=True)
assert result.returncode == 0, 'Private browser state could not be loaded'
print('Private browser session prepared; credentials omitted.')
