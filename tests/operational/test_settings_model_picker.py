import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_node(script: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required for frontend contract checks")
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_oauth_picker_renders_only_current_account_catalog_and_keeps_api_model_separate():
    run_node("""
      import assert from 'node:assert/strict';
      import { readFileSync } from 'node:fs';
      const module = await import('data:text/javascript;base64,' + Buffer.from(readFileSync('web/js/views/settings-view.js','utf8')).toString('base64'));
      const settings = {gen_llm_provider:'chatgpt_oauth', chatgpt_oauth_connected:true, chatgpt_oauth_model:'account-current', gen_llm_model:'stale-api-model'};
      const store = { getState:()=>({settings:{ens:settings},currentTenantId:'ens'}), chatgptModelsCatalog:{status:'ready',models:[{slug:'account-current',display_name:'Conta atual'},{slug:'account-next',display_name:'Outro modelo'}]} };
      const html = module.renderSettingsView(store);
      assert.match(html, /<select[^>]*id="setting-oauth-model"/);
      assert.match(html, /value="account-next"/);
      assert.match(html, /Outro modelo/);
      assert.doesNotMatch(html, /value="gpt-4o-mini"/);
      assert.match(html, /id="btn-refresh-chatgpt-models"/);
      assert.match(html, /id="setting-api-model"/);
    """)


def test_failed_catalog_keeps_current_model_visible_without_fabricating_alternatives():
    run_node("""
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      const module = await import('data:text/javascript;base64,' + Buffer.from(readFileSync('web/js/views/settings-view.js','utf8')).toString('base64'));
      const settings = {gen_llm_provider:'chatgpt_oauth',chatgpt_oauth_connected:true,chatgpt_oauth_model:'account-current',gen_llm_model:'stale-api-model'};
      const store={getState:()=>({settings:{ens:settings},currentTenantId:'ens'}),chatgptModelsCatalog:{status:'error',models:[],error:'Catálogo indisponível'}};
      const html=module.renderSettingsView(store);
      assert.match(html, /value="account-current"/);
      assert.match(html, /Catálogo indisponível/);
      assert.doesNotMatch(html, /value="stale-api-model"[^>]*selected/);
    """)


def test_catalog_refresh_and_backend_sync_keep_api_preference_separate():
    run_node("""
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      const saved = new Map();
      globalThis.localStorage = {getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,value)};
      const mocks = 'data:text/javascript;base64,'+Buffer.from(readFileSync('web/js/mock-data.js','utf8')).toString('base64');
      let source=readFileSync('web/js/store.js','utf8').replace("'./mock-data.js?v=20261027'",JSON.stringify(mocks));
      const {store}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
      let response={gen_llm_provider:'openai',gen_llm_model:'api-model'};
      globalThis.fetch=async()=>({ok:true,json:async()=>response});
      await store.syncBackendSettings();
      assert.equal(store.getState().settings.ens.api_llm_model,'api-model');
      store._hasSyncedBackendSettings=false;
      response={gen_llm_provider:'chatgpt_oauth',gen_llm_model:'oauth-model',chatgpt_oauth_model:'oauth-model'};
      await store.syncBackendSettings();
      assert.equal(store.getState().settings.ens.api_llm_model,'api-model');
      response={models:[{slug:'oauth-model',display_name:'Real account model'}],selected_model:'oauth-model'};
      const catalog=await store.loadChatGPTModels(true);
      assert.equal(catalog.status,'ready');
      assert.equal(catalog.models[0].slug,'oauth-model');
      globalThis.fetch=async()=>({ok:false,status:502,json:async()=>({detail:'Falha real do catálogo'})});
      const failure=await store.loadChatGPTModels(true);
      assert.equal(failure.status,'error');
      assert.equal(failure.models.length,0);
      assert.equal(failure.error,'Falha real do catálogo');
    """)


def test_intake_declares_monthly_tuition_for_comparable_price_search():
    run_node("""
      import assert from 'node:assert/strict';
      import {readFileSync} from 'node:fs';
      globalThis.localStorage={getItem:()=>null,setItem:()=>{}};
      const mocks='data:text/javascript;base64,'+Buffer.from(readFileSync('web/js/mock-data.js','utf8')).toString('base64');
      const source=readFileSync('web/js/store.js','utf8').replace("'./mock-data.js?v=20261027'",JSON.stringify(mocks));
      const {store}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
      let sent; globalThis.fetch=async(_url,options)=>{sent=JSON.parse(options.body);return {ok:false,status:422}};
      await store.startAnalysis({name:'Curso',ticket:980});
      assert.equal(sent.proposal_data.price_period,'monthly');
    """)
