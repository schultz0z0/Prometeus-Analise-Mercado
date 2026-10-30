import shutil
import subprocess
from pathlib import Path

import pytest


def test_reopening_analysis_uses_read_only_backend_state_and_respects_tenant():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for frontend contract checks")
    script = """
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      globalThis.localStorage={getItem:()=>null,setItem:()=>{}};
      const mocks='data:text/javascript;base64,'+Buffer.from(readFileSync('web/js/mock-data.js','utf8')).toString('base64');
      const source=readFileSync('web/js/store.js','utf8').replace("'./mock-data.js?v=20261027'",JSON.stringify(mocks));
      const {store}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
      const id='73501c53-cc58-47f9-8927-d9e299b4f4b5';
      let calls=[],polled;
      store.analysisCatalog=[{id,level:'Extensão',modality:'EAD',ticket:100,duration_months:1}];
      globalThis.fetch=async(url,options)=>{
        calls.push([url,options]);
        return {ok:true,json:async()=>({analysis_id:id,tenant_id:'ens',course_name:'Curso real',status:'RUNNING',steps:[{step_number:9,status:'RUNNING'}],tool_runs:[]})};
      };
      store.pollAnalysisStatus=(analysisId,input)=>{polled=analysisId;assert.equal(input.level,'Extensão');assert.equal(input.ticket,100)};
      assert.equal(await store.openAnalysis(id),true);
      assert.equal(store.state.currentView,'live');
      assert.equal(store.state.liveJob.steps[0].step_number,9);
      assert.equal(polled,id);
      assert.equal(calls.length,1);
      assert.equal(calls[0][1]?.method,undefined);
      const previous=store.state.liveJob;
      globalThis.fetch=async()=>({ok:true,json:async()=>({tenant_id:'other',analysis_id:id,status:'RUNNING'})});
      assert.equal(await store.openAnalysis(id),false);
      assert.equal(store.state.liveJob,previous);
      assert.equal(await store.openAnalysis('invalid'),false);
    """
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            cwd=Path(__file__).resolve().parents[2], capture_output=True,
                            text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr


def test_polling_survives_five_minutes_and_connection_loss_until_real_completion():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for frontend contract checks")
    script = """
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      globalThis.localStorage={getItem:()=>null,setItem:()=>{}};
      const mocks='data:text/javascript;base64,'+Buffer.from(readFileSync('web/js/mock-data.js','utf8')).toString('base64');
      const source=readFileSync('web/js/store.js','utf8').replace("'./mock-data.js?v=20261027'",JSON.stringify(mocks));
      const {store}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
      let deadline;
      globalThis.setTimeout=fn=>{deadline=fn;return 456};
      globalThis.clearTimeout=()=>{};
      let tick, cleared=false, completed=false;
      globalThis.setInterval=fn=>{tick=fn;return 123};
      globalThis.clearInterval=()=>{cleared=true};
      store.state.liveJob={id:'analysis',status:'RUNNING',logs:[]};
      store.completeRealAnalysis=async()=>{completed=true};
      globalThis.fetch=async()=>({ok:true,json:async()=>({status:'RUNNING',steps:[],tool_runs:[{capability:'instagram',status:'EMPTY',valid_items_count:0}]})});
      store.pollAnalysisStatus('analysis',{});
      for(let i=0;i<155;i++) await tick();
      assert.equal(cleared,false);
      assert.equal(store.state.liveJob.status,'RUNNING');
      globalThis.fetch=async()=>{throw new Error('offline')};
      await tick();
      assert.equal(cleared,false);
      assert.equal(store.state.liveJob.status,'RUNNING');
      assert.match(store.state.liveJob.connectionWarning,/offline/);
      globalThis.fetch=async(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted'))));
      const hung=tick(); deadline(); await hung;
      assert.match(store.state.liveJob.connectionWarning,/aborted/);
      const view=await import('data:text/javascript;base64,'+Buffer.from(readFileSync('web/js/views/live-view.js','utf8')).toString('base64'));
      const html=view.renderLiveView(store);
      assert.match(html,/Instagram/);
      assert.match(html,/dados parciais/);
      assert.doesNotMatch(html,/Processamento interrompido/);
      globalThis.fetch=async()=>({ok:true,json:async()=>({status:'COMPLETED'})});
      store.completeRealAnalysis=async()=>{throw new Error('dossier offline')};
      await tick();
      assert.equal(cleared,false);
      store.completeRealAnalysis=async()=>{completed=true};
      await tick();
      assert.equal(cleared,true);
      assert.equal(completed,true);
      assert.equal(store.state.liveJob.connectionWarning,null);
    """
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
