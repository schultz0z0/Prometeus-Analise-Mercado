import json
import subprocess
from pathlib import Path

query = """SELECT json_build_object(
 'courses', (SELECT count(*) FROM historical_courses),
 'funnels', (SELECT count(*) FROM historical_funnel_records),
 'courses_hash', (SELECT md5(string_agg(to_jsonb(t)::text, '' ORDER BY id)) FROM historical_courses t),
 'funnels_hash', (SELECT md5(string_agg(to_jsonb(t)::text, '' ORDER BY id)) FROM historical_funnel_records t),
 'dossiers', (SELECT count(*) FROM dossiers),
 'dossiers_hash', (SELECT md5(string_agg(to_jsonb(t)::text, '' ORDER BY id)) FROM dossiers t),
 'running_analyses', (SELECT count(*) FROM analyses WHERE status='RUNNING'),
 'running_jobs', (SELECT count(*) FROM analysis_jobs WHERE status='RUNNING'),
 'migration', (SELECT version_num FROM alembic_version));"""
result = subprocess.run(['rtk', 'proxy', 'docker', 'exec', 'prometeus-postgres', 'psql', '-U', 'prometeus', '-d', 'prometeus', '-At', '-c', query], capture_output=True, text=True, check=True)
data = json.loads(result.stdout)
target = Path(__file__).parent / 'baseline.json'
target.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data, indent=2))
