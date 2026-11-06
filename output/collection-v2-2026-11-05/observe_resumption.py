"""Read-only counters for the real resumption; never exposes credentials."""
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

query = """SELECT json_build_object(
 'status', a.status,
 'qualified_v4', (SELECT count(*) FROM market_evidences WHERE analysis_id=a.id AND sanitized_data->'_qualification'->>'qualification_version'='4'),
 'accepted_evidences_v4', (SELECT count(*) FROM market_evidences WHERE analysis_id=a.id AND sanitized_data->'_qualification'->>'qualification_version'='4' AND sanitized_data->'_qualification'->>'accepted'='true'),
 'evidence_total', (SELECT count(*) FROM market_evidences WHERE analysis_id=a.id),
 'plans', (SELECT count(*) FROM research_plans WHERE analysis_id=a.id),
 'tool_runs', (SELECT count(*) FROM tool_runs WHERE analysis_id=a.id),
 'latest_step', (SELECT max(step_number) FROM analysis_steps WHERE analysis_id=a.id))
FROM analyses a WHERE a.id='9cb4f98e-60b5-46d9-998e-5ad81ebe7d86';"""
prior = None
while True:
    result = subprocess.run(['rtk', 'proxy', 'docker', 'exec', 'prometeus-postgres', 'psql', '-U', 'prometeus', '-d', 'prometeus', '-At', '-c', query], capture_output=True, text=True, encoding='utf-8', check=True)
    body = json.loads(result.stdout)
    if body != prior:
        item = {'at': datetime.now(UTC).isoformat(), **body}
        with (Path(__file__).parent / 'resumption-counters.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(item) + '\n')
        print(json.dumps(item), flush=True)
        prior = body
    if body['status'] in {'BLOCKED', 'FAILED', 'COMPLETED', 'CANCELLED', 'WAITING_FOR_INPUT'}:
        break
    time.sleep(40)
