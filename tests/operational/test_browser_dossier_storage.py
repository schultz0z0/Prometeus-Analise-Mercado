import json
import subprocess
from pathlib import Path


def test_server_dossiers_do_not_consume_browser_storage_or_restore_stale_records():
    source = Path("web/js/store.js").resolve().as_uri()
    script = f"""
const key = 'prometeus_courses_real_v2';
const saved = new Map([[key, JSON.stringify([{{id:'stale-other-session',dossier:{{}}}}])]]);
const warnings = [];
console.warn = (...args) => warnings.push(args[0]);
globalThis.localStorage = {{
  getItem: key => saved.get(key) ?? null,
  removeItem: key => saved.delete(key),
  setItem: (key,value) => {{
    if (value.length > 4096) throw new Error('QuotaExceededError');
    saved.set(key,value);
  }}
}};
const {{store}} = await import({json.dumps(source)});
const staleRestored = store.getState().courses.some(c => c.id === 'stale-other-session');
store.state.courses = [{{id:'real-analysis', dossier:{{evidence:'x'.repeat(6000000)}}}}];
let notified = false;
store.subscribe(() => {{ notified = true; }});
store.notify();
console.log(JSON.stringify({{
  staleRestored, legacyRemoved: !saved.has(key), warnings,
  notified, inMemoryLength:store.getState().courses[0].dossier.evidence.length,
  savedTenant:saved.get('prometeus_tenant')
}}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, encoding="utf-8", check=True,
    )
    outcome = json.loads(result.stdout)
    assert not outcome["staleRestored"]
    assert outcome["legacyRemoved"]
    assert outcome["warnings"] == []
    assert outcome["notified"] and outcome["inMemoryLength"] == 6000000
    assert outcome["savedTenant"] == "ens"
