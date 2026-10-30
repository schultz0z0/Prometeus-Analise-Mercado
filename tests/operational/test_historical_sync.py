import json
import subprocess
from pathlib import Path


def test_portfolio_sync_upserts_without_resetting_historical_ids():
    store_url = Path("web/js/store.js").resolve().as_uri()
    view_url = Path("web/js/views/portfolio-view.js").resolve().as_uri()
    script = f"""
      import assert from 'node:assert/strict';
      globalThis.localStorage={{getItem:()=>null,setItem:()=>{{}}}};
      globalThis.alert=()=>{{}};
      const requests=[];
      globalThis.fetch=async(url,options)=>{{requests.push({{url,options}});return {{ok:true,json:async()=>({{courses:[]}})}}}};
      const {{store}}=await import({json.dumps(store_url)});
      const {{bindPortfolioEvents}}=await import({json.dumps(view_url)});
      let click;
      const button={{textContent:'Sincronizar',addEventListener:(event,fn)=>{{click=fn}}}};
      const container={{querySelector:selector=>selector==='#btn-reseed-data'?button:null,querySelectorAll:()=>[]}};
      bindPortfolioEvents(store,container);
      await click();
      const sync=requests.find(r=>r.options?.method==='POST');
      assert.equal(new URL(sync.url,'http://test').searchParams.get('reset'),'false');
      assert.equal(button.disabled,false);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
