/**
 * PROMETEUS INTELLIGENCE PLATFORM — REACTIVE STORE
 * Gerencia o estado da aplicação, persistência em localStorage e emissão de eventos.
 */

import { INITIAL_TENANTS, INITIAL_SETTINGS, INITIAL_COURSES, DETAILED_DOSSIER } from './mock-data.js';

class PrometeusStore {
  constructor() {
    this.listeners = [];
    this.loadState();
  }

  loadState() {
    try {
      const savedTenant = localStorage.getItem('prometeus_tenant') || 'ens';
      const savedSettings = JSON.parse(localStorage.getItem('prometeus_settings')) || INITIAL_SETTINGS;
      const savedCourses = JSON.parse(localStorage.getItem('prometeus_courses')) || INITIAL_COURSES;
      
      this.state = {
        tenants: INITIAL_TENANTS,
        currentTenantId: savedTenant,
        settings: savedSettings,
        courses: savedCourses,
        activeCourseId: "JOB-2026-ENS-884",
        currentDossier: DETAILED_DOSSIER,
        currentView: "portfolio", // 'validate' | 'portfolio' | 'live' | 'dossier' | 'settings'
        liveJob: null
      };
    } catch (e) {
      this.state = {
        tenants: INITIAL_TENANTS,
        currentTenantId: 'ens',
        settings: INITIAL_SETTINGS,
        courses: INITIAL_COURSES,
        activeCourseId: "JOB-2026-ENS-884",
        currentDossier: DETAILED_DOSSIER,
        currentView: "portfolio",
        liveJob: null
      };
    }
  }

  saveState() {
    try {
      localStorage.setItem('prometeus_tenant', this.state.currentTenantId);
      localStorage.setItem('prometeus_settings', JSON.stringify(this.state.settings));
      localStorage.setItem('prometeus_courses', JSON.stringify(this.state.courses));
    } catch (e) {
      console.warn("Falha ao salvar no localStorage", e);
    }
  }

  getState() {
    return this.state;
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    this.saveState();
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  setTenant(tenantId) {
    if (this.state.currentTenantId !== tenantId) {
      this.state.currentTenantId = tenantId;
      this.notify();
    }
  }

  setView(viewName, params = {}) {
    this.state.currentView = viewName;
    if (params.courseId) {
      this.state.activeCourseId = params.courseId;
    }
    this.notify();
  }

  updateSettings(tenantId, newSettings, shouldNotify = true) {
    this.state.settings[tenantId] = {
      ...this.state.settings[tenantId],
      ...newSettings
    };
    if (shouldNotify) {
      this.notify();
    } else {
      this.saveState();
    }
  }

  async syncBackendSettings() {
    if (this._syncingBackendSettings || this._hasSyncedBackendSettings) return;
    this._syncingBackendSettings = true;
    try {
      const resp = await fetch('/v1/settings');
      if (resp.ok) {
        const backendSettings = await resp.json();
        const tenantId = this.state.currentTenantId;
        this.updateSettings(tenantId, {
          gen_llm_provider: backendSettings.gen_llm_provider || "chatgpt_oauth",
          gen_llm_model: backendSettings.gen_llm_model || "gpt-6.1-sol",
          gen_llm_reasoning_effort: backendSettings.gen_llm_reasoning_effort || "high",
          chatgpt_access_token: backendSettings.chatgpt_access_token_masked || "",
          jev_model: backendSettings.jev_model || "jev-v1.2.0",
          apify_max_charge: backendSettings.apify_max_charge || 5.0,
        }, false);
        this._hasSyncedBackendSettings = true;
      }
    } catch (e) {
      console.warn("Backend settings sync failed:", e);
    } finally {
      this._syncingBackendSettings = false;
    }
  }

  startAnalysis(courseInput) {
    const newId = `JOB-2026-${this.state.currentTenantId.toUpperCase()}-${Math.floor(100 + Math.random() * 900)}`;
    
    const newJob = {
      id: newId,
      name: courseInput.name,
      area: courseInput.area || "Tecnologia & Negócios",
      level: courseInput.level || "MBA Executivo",
      modality: courseInput.modality || "EAD Síncrono",
      ticket: parseFloat(courseInput.ticket) || 980.0,
      duration_months: parseInt(courseInput.duration) || 12,
      status: "RUNNING",
      created_at: new Date().toISOString(),
      step: 1,
      logs: []
    };

    this.state.liveJob = newJob;
    this.state.currentView = "live";
    this.notify();

    // Simulação dos 4 Motores trabalhando em paralelo
    this.simulateLivePipeline(newJob);
  }

  simulateLivePipeline(job) {
    const steps = [
      { step: 1, delay: 800, engine: "JEV Gatekeeper", text: "Proposta avaliada com prontidão semântica 100%. Iniciando varredura." },
      { step: 2, delay: 1800, engine: "CRM Institucional", text: "Consultando API de Cursos da ENS... 3 turmas históricas encontradas (conversão média 14.2%)." },
      { step: 3, delay: 2800, engine: "Google Trends", text: "Volume de busca em alta (+88% YoY). Pico de sazonalidade previsto para janeiro." },
      { step: 4, delay: 3800, engine: "Meta Ads & Apify", text: "22 anúncios concorrentes ativos capturados da FGV, PUC e FIA. Mapeando criativos." },
      { step: 5, delay: 4800, engine: "CBO & Catho", text: "1.420 vagas ativas mapeadas exigindo formação em dados e regulação no setor de seguros." },
      { step: 6, delay: 5800, engine: "JEV Ementa", text: "Auditoria curricular concluída: 1 lacuna prática detectada (recomendada inclusão de laboratório Python/SUSEP)." },
      { step: 7, delay: 6800, engine: "Scoring Engine", text: "Viability Score calculado: 86.4 (Recomendação: APPROVED_WITH_ADJUSTMENTS). Ponto de equilíbrio: 18 alunos." }
    ];

    steps.forEach(({ step, delay, engine, text }) => {
      setTimeout(() => {
        if (!this.state.liveJob || this.state.liveJob.id !== job.id) return;
        
        this.state.liveJob.step = step;
        this.state.liveJob.logs.push(`[${new Date().toLocaleTimeString()}] ${engine}: ${text}`);
        
        if (step === 7) {
          this.finishJob(this.state.liveJob);
        } else {
          this.notify();
        }
      }, delay);
    });
  }

  finishJob(job) {
    const completedCourse = {
      id: job.id,
      name: job.name,
      area: job.area,
      level: job.level,
      modality: job.modality,
      ticket: job.ticket,
      duration_months: job.duration_months,
      status: "COMPLETED",
      recommendation: "APPROVED_WITH_ADJUSTMENTS",
      viability_score: 86.4,
      coverage_index: 92.0,
      confidence_index: 0.88,
      demand_level: "MUITO ALTA (+88% YoY)",
      competition_pressure: "MODERADA / ALTA",
      breakeven_students: 18,
      projected_students: 32,
      net_revenue_projected: 142800.00,
      created_at: job.created_at,
      human_decision: null
    };

    this.state.courses.unshift(completedCourse);
    this.state.activeCourseId = job.id;
    this.state.liveJob = null;
    this.state.currentView = "dossier";
    this.notify();
  }

  registerHumanDecision(courseId, decision, notes, deciderName) {
    const course = this.state.courses.find(c => c.id === courseId);
    if (course) {
      course.human_decision = {
        status: decision,
        decision_by: deciderName || "Diretoria Acadêmica",
        decided_at: new Date().toISOString(),
        notes: notes || "Decisão registrada em comitê."
      };
      this.notify();
    }
  }
}

export const store = new PrometeusStore();
