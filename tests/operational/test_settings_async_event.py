import subprocess


def test_history_sync_does_not_reuse_event_current_target_after_await():
    script = """
      import assert from 'node:assert/strict';
      import {pathToFileURL} from 'node:url';
      const {bindSettingsEvents}=await import(pathToFileURL(process.cwd()+'/web/js/views/settings-view.js'));
      globalThis.window={__prometeusOAuthListenerBound:true};
      let click;
      const button={disabled:false,addEventListener:(_,fn)=>{click=fn}};
      const result={textContent:''};
      const provider={value:'openai',addEventListener:()=>{}};
      const fields=Object.fromEntries(['setting-oauth-model','setting-api-model','setting-reasoning-effort','setting-oauth-model-group','setting-api-model-group'].map(id=>['#'+id,{value:'',style:{},addEventListener:()=>{}}]));
      const container={querySelector:s=>s==='#btn-sync-crm-data'?button:s==='#settings-result'?result:s==='#setting-llm-provider'?provider:fields[s]||null};
      const store={getState:()=>({currentTenantId:'ens',settings:{ens:{}}}),seedInstitutionalData:async()=>true};
      bindSettingsEvents(store,container);
      const event={currentTarget:button};
      const pending=click(event);
      event.currentTarget=null;
      await pending;
      assert.equal(button.disabled,false);
      assert.match(result.textContent,/carregada/);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_live_view_shows_partial_collection_and_escaped_verification_diagnostics():
    script = """
      import assert from 'node:assert/strict';
      import {pathToFileURL} from 'node:url';
      const {renderLiveView}=await import(pathToFileURL(process.cwd()+'/web/js/views/live-view.js'));
      const store={getState:()=>({liveJob:{id:'analysis',status:'BLOCKED',name:'Curso',
        steps:[{status:'FAILED',output_summary:{verification:{issues:[{message:'Número sem suporte',text_excerpt:'<script>alert(1)</script>'}]}}}],
        toolRuns:[{capability:'google_trends',status:'PARTIAL',query:'seguros',cost_usd:0.13}]
      }})};
      const html=renderLiveView(store);
      assert.match(html,/Número sem suporte/);
      assert.match(html,/consulta interrompida com retorno parcial/);
      assert.match(html,/&lt;script&gt;/);
      assert.doesNotMatch(html,/<script>/);
      const job=store.getState().liveJob;
      job.status='RUNNING';
      job.steps[0].output_summary.dossier_revision={status:'RUNNING',attempt:2};
      store.getState=()=>({liveJob:job});
      assert.match(renderLiveView(store),/Revisando a redação do dossiê/);
      assert.doesNotMatch(renderLiveView(store),/Processamento interrompido/);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
