"""Local deployment evidence; never emit credential contents."""
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT / 'output' / 'homologation-2026-11-04'
PRIVATE = ROOT / 'var' / 'backups' / 'homologation-2026-11-04'
ART.mkdir(parents=True, exist_ok=True)
PRIVATE.mkdir(parents=True, exist_ok=True)


def run(args, *, payload=None, binary=False):
    result = subprocess.run(args, input=payload, capture_output=True, text=not binary, cwd=ROOT)
    if result.returncode:
        raise RuntimeError(f'Operation failed ({result.returncode}): {args[:4]}')
    return result.stdout


def sql(statement):
    return run(['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'prometeus', '-d', 'prometeus', '-At', '-v', 'ON_ERROR_STOP=1', '-c', statement]).strip()


def historical_fingerprint():
    tables = ['historical_courses', 'historical_funnel_records']
    return {table: {'count': int(sql(f'SELECT count(*) FROM {table}')), 'sha256': hashlib.sha256(sql(f'SELECT row_to_json(t)::text FROM {table} t ORDER BY id').encode()).hexdigest()} for table in tables}


def main():
    mode = sys.argv[1]
    if mode == 'preflight':
        snippet = '''
import json
from dataclasses import asdict
from prometeus.domain.configuration import AppSettings
from prometeus.application.runtime_preflight import validate_runtime_preflight
from prometeus.infrastructure.llm.codex_oauth import ChatGPTCredentialStore
s=AppSettings()
c=ChatGPTCredentialStore(s.CHATGPT_CREDENTIALS_PATH).load()
print(json.dumps({'preflight':asdict(validate_runtime_preflight(s)), 'app_env':s.APP_ENV,'provider':s.GEN_LLM_PROVIDER,'oauth_stored':c is not None,'selected_model':c.selected_model if c else s.GEN_LLM_MODEL,'apify_configured':bool(s.APIFY_TOKEN.strip()),'synthetic_history_allowed':s.ALLOW_SYNTHETIC_INSTITUTIONAL_HISTORY,'shadow_mode':s.SHADOW_MODE,'kill_switch':s.KILL_SWITCH_ACTIVE,'max_cost_usd':s.MAX_ANALYSIS_COST_USD if hasattr(s,'MAX_ANALYSIS_COST_USD') else None,'service_keys_configured':bool(s.SERVICE_API_KEYS.strip()),'webhook_configured':bool(s.WEBHOOK_TARGET_URL)}))
'''
        metadata = json.loads(run(['docker','compose','exec','-T','api','python','-'],payload=snippet))
        evidence = {'timestamp':datetime.now(UTC).isoformat(),'metadata':metadata,'migration':sql('SELECT version_num FROM alembic_version'),'historical':historical_fingerprint(),'analysis_statuses':json.loads(sql("SELECT json_object_agg(status,n) FROM (SELECT status,count(*) n FROM analyses GROUP BY status) t")), 'env_sha256': hashlib.sha256((ROOT/'.env').read_bytes()).hexdigest()}
        (ART/'baseline.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print(json.dumps(evidence,indent=2))
    elif mode == 'backup':
        target = PRIVATE/'pre-migration.dump'
        dump = run(['docker','compose','exec','-T','postgres','pg_dump','-U','prometeus','-d','prometeus','-Fc'],binary=True)
        target.write_bytes(dump)
        run(['docker','compose','exec','-T','postgres','pg_restore','--list'],payload=dump,binary=True)
        baseline=json.loads((ART/'baseline.json').read_text(encoding='utf-8'))
        assert historical_fingerprint()==baseline['historical']
        images=json.loads(run(['docker','inspect','prometeus-api','prometeus-worker']))
        for item in images:
            service=item['Config']['Labels']['com.docker.compose.service']
            run(['docker','tag',item['Image'],f'prometeus-rollback-{service}:20261104'])
        report={'bytes':len(dump),'sha256':hashlib.sha256(dump).hexdigest(),'pg_restore_list':'passed','historical_unchanged':True,'rollback_images_tagged':True,'private_backup_path':str(target)}
        (ART/'backup.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    elif mode == 'preservation':
        baseline=json.loads((ART/'baseline.json').read_text(encoding='utf-8'))
        result={'historical_unchanged':historical_fingerprint()==baseline['historical'],'env_unchanged':hashlib.sha256((ROOT/'.env').read_bytes()).hexdigest()==baseline['env_sha256'],'migration':sql('SELECT version_num FROM alembic_version')}
        (ART/'preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
        assert result['historical_unchanged'] and result['env_unchanged']
    elif mode == 'rehearsal':
        def clone_sql(statement):
            return run(['docker','exec','prometeus-homologation-restore','psql','-U','postgres','-d','homologation','-At','-v','ON_ERROR_STOP=1','-c',statement]).strip()
        names=sql("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'alembic_version' ORDER BY tablename").splitlines()
        counts={name:{'original':int(sql(f'SELECT count(*) FROM {name}')),'restored':int(clone_sql(f'SELECT count(*) FROM {name}'))} for name in names}
        baseline=json.loads((ART/'baseline.json').read_text(encoding='utf-8'))
        same=all(hashlib.sha256(clone_sql(f'SELECT row_to_json(t)::text FROM {name} t ORDER BY id').encode()).hexdigest()==value['sha256'] for name,value in baseline['historical'].items())
        report={'migration':clone_sql('SELECT version_num FROM alembic_version'),'tables':counts,'all_original_counts_preserved':all(value['original']==value['restored'] for value in counts.values()),'historical_fingerprints_preserved':same}
        (ART/'restore-rehearsal.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
        assert report['all_original_counts_preserved'] and same


if __name__=='__main__':
    main()
