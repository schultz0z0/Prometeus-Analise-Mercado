import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / '.env'
backup = root / 'var/backups/collection-v2-2026-11-05/environment-before.env'
assert not backup.exists(), 'Do not overwrite the predeployment configuration backup'
original = path.read_bytes()
backup.write_bytes(original)
text = original.decode('utf-8-sig')
keys = {'APIFY_MAX_TOTAL_CHARGE_USD_PER_ANALYSIS', 'APIFY_DISCOVERY_MCP_ENABLED'}
retained = [line for line in text.splitlines() if line.split('=', 1)[0].strip() not in keys]
updated = '\n'.join([*retained, 'APIFY_DISCOVERY_MCP_ENABLED=true', ''])
path.write_text(updated, encoding='utf-8')
assert [line for line in path.read_text(encoding='utf-8').splitlines() if line.split('=', 1)[0].strip() not in keys] == retained
report = {'monetary_application_cap': None, 'discovery_mcp_enabled': True, 'unrelated_configuration_preserved': True, 'backup_sha256': hashlib.sha256(original).hexdigest()}
(Path(__file__).parent / 'configuration-transition.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
