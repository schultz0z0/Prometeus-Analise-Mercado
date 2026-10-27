/** Estado reativo da interface, alimentado exclusivamente pela API. */

import {
  INITIAL_TENANTS,
  INITIAL_SETTINGS,
  INITIAL_COURSES,
  INITIAL_HISTORICAL_COURSES
} from './mock-data.js?v=20261027';

const REAL_COURSES_STORAGE_KEY = 'prometeus_courses_real_v2';

function numericOrNull(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function nowLabel() {
  return new Date().toLocaleTimeString('pt-BR');
}

class PrometeusStore {
  constructor() {
    this.listeners = [];
    this.loadState();
  }

  loadState() {
    let savedSettings = INITIAL_SETTINGS;
    let savedCourses = INITIAL_COURSES;
    try {
      savedSettings = JSON.parse(localStorage.getItem('prometeus_settings')) || INITIAL_SETTINGS;
      savedCourses = JSON.parse(localStorage.getItem(REAL_COURSES_STORAGE_KEY)) || INITIAL_COURSES;
    } catch (error) {
      console.warn('Estado local inválido; iniciando interface limpa.', error);
    }
    this.state = {
      tenants: INITIAL_TENANTS,
      currentTenantId: localStorage.getItem('prometeus_tenant') || 'ens',
      settings: savedSettings,
      courses: savedCourses,
      historicalCourses: INITIAL_HISTORICAL_COURSES,
      portfolioTab: 'historical',
      activeCourseId: null,
      currentDossier: null,
      currentView: 'portfolio',
      liveJob: null
    };
  }

  saveState() {
    try {
      localStorage.setItem('prometeus_tenant', this.state.currentTenantId);
      localStorage.setItem('prometeus_settings', JSON.stringify(this.state.settings));
      localStorage.setItem(REAL_COURSES_STORAGE_KEY, JSON.stringify(this.state.courses));
    } catch (error) {
      console.warn('Falha ao salvar preferências locais.', error);
    }
  }

  getState() { return this.state; }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => { this.listeners = this.listeners.filter(item => item !== listener); };
  }

  notify() {
    this.saveState();
    this.listeners.forEach(listener => listener(this.state));
  }

  setTenant(tenantId) {
    if (this.state.tenants.some(tenant => tenant.id === tenantId)) {
      this.state.currentTenantId = tenantId;
      this.notify();
    }
  }

  setView(viewName, params = {}) {
    this.state.currentView = viewName;
    if (params.courseId) {
      this.state.activeCourseId = params.courseId;
      const course = this.state.courses.find(item => item.id === params.courseId);
      this.state.currentDossier = course?.dossier || null;
    }
    this.notify();
  }

  setPortfolioTab(tab) {
    this.state.portfolioTab = tab;
    this.notify();
  }

  async loadHistoricalCourses() {
    try {
      const response = await fetch(`/v1/institutional/courses?tenant_id=${encodeURIComponent(this.state.currentTenantId)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      this.state.historicalCourses = Array.isArray(data.courses) ? data.courses : [];
      this.notify();
    } catch (error) {
      console.warn('Base histórica indisponível.', error);
      this.state.historicalCourses = [];
      this.notify();
    }
  }

  async loadCompletedAnalyses() {
    try {
      const response = await fetch(`/v1/analyses?tenant_id=${encodeURIComponent(this.state.currentTenantId)}`);
      if (!response.ok) return;
      const data = await response.json();
      const verified = (Array.isArray(data.items) ? data.items : []).filter(
        item => item.status === 'COMPLETED' && item.dossier && item.dossier.status === 'VERIFIED'
      );
      if (verified.length > 0) {
        this.state.courses = verified;
        if (!this.state.activeCourseId) {
          this.state.activeCourseId = verified[0].id;
          this.state.currentDossier = verified[0].dossier;
        }
        this.notify();
      }
    } catch (error) {
      console.warn('Não foi possível sincronizar diagnósticos concluídos.', error);
    }
  }

  async seedInstitutionalData(reset = true) {
    try {
      const response = await fetch(`/v1/institutional/seed?tenant_id=${encodeURIComponent(this.state.currentTenantId)}&reset=${reset}`, { method: 'POST' });
      if (!response.ok) return false;
      await this.loadHistoricalCourses();
      return true;
    } catch (error) {
      console.error('Falha ao carregar a base histórica de teste.', error);
      return false;
    }
  }

  updateSettings(tenantId, newSettings, shouldNotify = true) {
    this.state.settings[tenantId] = { ...this.state.settings[tenantId], ...newSettings };
    if (shouldNotify) this.notify(); else this.saveState();
  }

  async syncBackendSettings() {
    if (this._syncingBackendSettings || this._hasSyncedBackendSettings) return;
    this._syncingBackendSettings = true;
    try {
      const response = await fetch('/v1/settings');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const settings = await response.json();
      this.updateSettings(this.state.currentTenantId, {
        gen_llm_provider: settings.gen_llm_provider || '',
        gen_llm_model: settings.gen_llm_model || '',
        gen_llm_reasoning_effort: settings.gen_llm_reasoning_effort || '',
        chatgpt_oauth_connected: Boolean(settings.chatgpt_oauth_connected),
        chatgpt_oauth_email: settings.chatgpt_oauth_email || '',
        chatgpt_oauth_model: settings.chatgpt_oauth_model || '',
        openai_api_key_masked: settings.openai_api_key_masked || '',
        apify_token_masked: settings.apify_token_masked || '',
        is_jev_configured: Boolean(settings.is_jev_configured),
        jev_model: settings.jev_model || '',
        apify_max_charge: settings.apify_max_charge ?? null
      }, false);
      this._hasSyncedBackendSettings = true;
    } catch (error) {
      console.warn('Configuração do backend indisponível.', error);
    } finally {
      this._syncingBackendSettings = false;
    }
  }

  async startAnalysis(courseInput) {
    const job = {
      id: `pending_${Date.now().toString(36)}`,
      name: courseInput.name,
      status: 'SUBMITTING',
      created_at: new Date().toISOString(),
      steps: [],
      toolRuns: [],
      blocking: null,
      error: null,
      logs: [`[${nowLabel()}] Enviando proposta para a API do Prometeus.`]
    };
    this.state.liveJob = job;
    this.state.currentView = 'live';
    this.notify();

    const payload = {
      course_name: courseInput.name,
      tenant_id: this.state.currentTenantId,
      proposal_data: {
        curriculum: courseInput.curriculum || '',
        curriculum_text: courseInput.curriculum || '',
        curriculum_file_name: courseInput.curriculum_file_name || '',
        area: courseInput.area || '',
        level: courseInput.level || '',
        modality: courseInput.modality || '',
        ticket: numericOrNull(courseInput.ticket),
        duration_months: numericOrNull(courseInput.duration),
        audience: courseInput.audience || '',
        competitors: courseInput.competitors || ''
      }
    };

    try {
      const response = await fetch('/v1/analyses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error(`A API recusou a solicitação (HTTP ${response.status}).`);
      const data = await response.json();
      job.id = data.analysis_id;
      job.status = data.status;
      job.logs.push(`[${nowLabel()}] Análise ${job.id} aceita e enviada ao worker.`);
      this.notify();
      this.pollAnalysisStatus(job.id, courseInput);
    } catch (error) {
      job.status = 'FAILED';
      job.error = error.message;
      job.logs.push(`[${nowLabel()}] Falha real: ${error.message}`);
      this.notify();
    }
  }

  pollAnalysisStatus(analysisId, courseInput) {
    let attempts = 0;
    const logged = new Set();
    const poll = setInterval(async () => {
      attempts += 1;
      const job = this.state.liveJob;
      if (!job || job.id !== analysisId) return clearInterval(poll);
      try {
        const response = await fetch(`/v1/analyses/${analysisId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        job.status = data.status;
        job.steps = data.steps || [];
        job.toolRuns = data.tool_runs || [];
        job.blocking = data.blocking || null;
        job.steps.forEach(step => {
          const key = `${step.step_number}:${step.status}`;
          if (!logged.has(key)) {
            logged.add(key);
            job.logs.push(`[${nowLabel()}] Etapa ${step.step_number} — ${step.name}: ${step.status}.`);
          }
        });
        this.notify();
        if (data.status === 'COMPLETED') {
          clearInterval(poll);
          await this.completeRealAnalysis(analysisId, data, courseInput);
        } else if (['BLOCKED', 'FAILED', 'WAITING_FOR_INPUT', 'CANCELLED'].includes(data.status)) {
          clearInterval(poll);
          job.error = data.blocking?.reason || `Processamento encerrado em ${data.status}.`;
          job.logs.push(`[${nowLabel()}] ${job.error}`);
          this.notify();
        } else if (attempts >= 150) {
          clearInterval(poll);
          job.status = 'TIMEOUT';
          job.error = 'O processamento continua sem confirmação de conclusão. Consulte novamente a análise.';
          this.notify();
        }
      } catch (error) {
        if (attempts >= 150) {
          clearInterval(poll);
          job.status = 'CONNECTION_ERROR';
          job.error = `Não foi possível consultar o backend: ${error.message}`;
          this.notify();
        }
      }
    }, 2000);
  }

  async completeRealAnalysis(analysisId, analysisData, courseInput) {
    const response = await fetch(`/v1/analyses/${analysisId}/dossier`);
    if (!response.ok) {
      this.state.liveJob.status = 'FAILED';
      this.state.liveJob.error = `Análise concluída sem dossiê verificável (HTTP ${response.status}).`;
      this.notify();
      return;
    }
    const dossier = await response.json();
    if (dossier.status !== 'VERIFIED' || !dossier.scoring) {
      this.state.liveJob.status = 'FAILED';
      this.state.liveJob.error = 'O backend não retornou um dossiê factual verificado com scoring.';
      this.notify();
      return;
    }
    const scoring = dossier.scoring;
    const course = {
      id: analysisId,
      name: courseInput.name,
      area: courseInput.area || '',
      level: courseInput.level || '',
      modality: courseInput.modality || '',
      ticket: numericOrNull(courseInput.ticket),
      duration_months: numericOrNull(courseInput.duration),
      status: analysisData.status,
      recommendation: scoring.recommendation,
      viability_score: scoring.viability_score,
      coverage_index: scoring.coverage_score,
      confidence_index: scoring.confidence_score,
      created_at: dossier.created_at,
      dossier
    };
    this.state.courses = [course, ...this.state.courses.filter(item => item.id !== analysisId)];
    this.state.activeCourseId = analysisId;
    this.state.currentDossier = dossier;
    this.state.liveJob = null;
    this.state.currentView = 'dossier';
    this.notify();
  }

  async registerHumanDecision(courseId, decision, notes, deciderName) {
    const response = await fetch(`/v1/analyses/${courseId}/decisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: deciderName,
        user_role: 'academic_committee',
        decision,
        rationale: notes,
        adjustments: {}
      })
    });
    if (!response.ok) throw new Error(`Decisão não registrada (HTTP ${response.status}).`);
    return response.json();
  }
}

export const store = new PrometeusStore();
