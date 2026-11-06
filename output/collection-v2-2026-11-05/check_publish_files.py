"""Verify publication candidates without displaying any secret values."""
from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]
secrets = []
for line in (root/'.env').read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=',1)
        value = value.strip().strip('"').strip("'")
        if any(word in key.upper() for word in ('TOKEN','SECRET','API_KEY','PASSWORD')) and len(value) >= 16:
            secrets.append(value.encode())
secrets.append((root/'var/auth/admin.key').read_bytes().strip())
files = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
findings = []
for name in set(filter(None, files)):
    p = root/name
    if not p.is_file():
        continue
    data = p.read_bytes()
    if any(value and value in data for value in secrets):
        findings.append({'path':name,'reason':'configured_secret_value'})
    if re.search(rb'(?:sk-proj-[A-Za-z0-9_-]{30,}|apify_api_[A-Za-z0-9]{20,})',data):
        findings.append({'path':name,'reason':'credential_pattern'})
report = {'files_checked':len(set(files))-1,'findings':findings}
print(json.dumps(report))
assert not findings, 'Publication candidates contain credentials; do not stage them.'
