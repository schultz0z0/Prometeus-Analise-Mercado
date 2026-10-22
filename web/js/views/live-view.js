/**
 * VIEW: Esteira de Inteligência em Tempo Real (Live Job Stream)
 */

export function renderLiveView(store) {
  const state = store.getState();
  const job = state.liveJob || {
    id: "JOB-2026-ENS-884",
    name: "MBA em Inteligência Artificial Aplicada a Seguros e Gestão de Riscos",
    step: 5,
    logs: ["Iniciando varredura paralela dos 4 motores de inteligência..."]
  };

  const currentStep = job.step || 1;

  const stepsList = [
    "1. Contexto", "2. Intake", "3. Readiness", "4. Keywords", "5. Plano",
    "6. Histórico CRM", "7. Meta Ads", "8. Higienização", "9. JEV Decisões", "10. Scoring",
    "11. Quality Gate", "12. Síntese", "13. Verificação", "14. Dossiê", "15. Concluído"
  ];

  return `
    <div class="view-header">
      <div class="view-title-row">
        <div>
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <span class="prometeus-pill-badge" data-status="RUNNING">● PROCESSAMENTO ATIVO</span>
            <span class="prometeus-stat-mono" style="font-size:12px; color:var(--prometeus-text-muted);">${job.id}</span>
          </div>
          <h1 class="view-title">${job.name}</h1>
          <p class="view-subtitle">A esteira de inteligência está varrendo o histórico do seu CRM e fontes públicas em paralelo.</p>
        </div>
      </div>
    </div>

    <!-- Stepper de 15 Etapas Canônicas -->
    <div class="prometeus-card" style="margin-bottom:24px; padding:18px 24px;">
      <div style="font-size:13px; font-weight:600; color:#ffffff; margin-bottom:12px;">Progresso do Pipeline de Validação:</div>
      <div class="stepper-container" style="padding:0;">
        ${stepsList.map((stepName, idx) => {
          const stepNum = idx + 1;
          const isDone = stepNum < currentStep;
          const isCurrent = stepNum === currentStep;
          let className = "step-item";
          let prefix = `${stepNum}. `;
          if (isDone) {
            className += " completed";
            prefix = "✓ ";
          } else if (isCurrent) {
            className += " active";
            prefix = "⟳ ";
          }
          return `<div class="${className}">${prefix}${stepName.replace(/^\d+\.\s*/, '')}</div>`;
        }).join('')}
      </div>
    </div>

    <!-- Os 4 Motores em Paralelo -->
    <div style="font-size:16px; font-weight:600; color:#ffffff; margin-bottom:14px;">Motores de Coleta e Análise em Execução:</div>
    <div class="live-stream-grid">
      <!-- Motor 1: CRM Institucional -->
      <div class="engine-card ${currentStep >= 2 ? 'completed' : 'running'}">
        <div class="engine-header">
          <div class="engine-title">
            <span>🏢</span>
            <span>Histórico Interno (ENS CRM)</span>
          </div>
          <span class="prometeus-pill-badge" data-status="${currentStep >= 2 ? 'APPROVED' : 'RUNNING'}">
            ${currentStep >= 2 ? '✓ Sincronizado' : '⟳ Varrendo'}
          </span>
        </div>
        <p style="font-size:12px; color:var(--prometeus-text-secondary); margin:0;">
          Cruzando proposta com a base de 18 turmas históricas e taxa de conversão de leads da instituição.
        </p>
        <div class="engine-log-box">
          ${currentStep >= 2 ? '✓ 3 turmas parecidas encontradas.<br>• Conversão média: 14.2%<br>• Ticket médio praticado: R$ 850' : 'Aguardando sincronização de endpoints...'}
        </div>
      </div>

      <!-- Motor 2: Demanda & Busca -->
      <div class="engine-card ${currentStep >= 3 ? 'completed' : 'running'}">
        <div class="engine-header">
          <div class="engine-title">
            <span>📈</span>
            <span>Busca Orgânica (Google Trends)</span>
          </div>
          <span class="prometeus-pill-badge" data-status="${currentStep >= 3 ? 'APPROVED' : 'RUNNING'}">
            ${currentStep >= 3 ? '✓ Mapeado' : '⟳ Consultando'}
          </span>
        </div>
        <p style="font-size:12px; color:var(--prometeus-text-secondary); margin:0;">
          Calculando volume de interesse nacional, tendência anual e sazonalidade de matrículas.
        </p>
        <div class="engine-log-box">
          ${currentStep >= 3 ? '✓ Volume nacional: +88% YoY.<br>• Sazonalidade: Pico forte em Janeiro/Fevereiro.<br>• CPC médio estimado: R$ 3,40' : 'Consultando Google Trends API...'}
        </div>
      </div>

      <!-- Motor 3: Meta Ads & Concorrência -->
      <div class="engine-card ${currentStep >= 4 ? 'completed' : 'running'}">
        <div class="engine-header">
          <div class="engine-title">
            <span>🥊</span>
            <span>Concorrência & Ads (Meta + Apify)</span>
          </div>
          <span class="prometeus-pill-badge" data-status="${currentStep >= 4 ? 'APPROVED' : 'RUNNING'}">
            ${currentStep >= 4 ? '✓ Capturado' : '⟳ Varrendo'}
          </span>
        </div>
        <p style="font-size:12px; color:var(--prometeus-text-secondary); margin:0;">
          Espionando anúncios ativos na Meta Ads Library e minerando queixas de alunos no YouTube/redes.
        </p>
        <div class="engine-log-box">
          ${currentStep >= 4 ? '✓ 22 anúncios ativos capturados.<br>• Concorrentes: FGV, PUC, FIA.<br>• Queixa #1: Cursos rivais muito teóricos.' : 'Raspando biblioteca de anúncios...'}
        </div>
      </div>

      <!-- Motor 4: Empregabilidade & Vagas -->
      <div class="engine-card ${currentStep >= 5 ? 'completed' : 'running'}">
        <div class="engine-header">
          <div class="engine-title">
            <span>💼</span>
            <span>Mercado de Trabalho (CBO / LinkedIn)</span>
          </div>
          <span class="prometeus-pill-badge" data-status="${currentStep >= 5 ? 'APPROVED' : 'RUNNING'}">
            ${currentStep >= 5 ? '✓ Concluído' : '⟳ Mapeando'}
          </span>
        </div>
        <p style="font-size:12px; color:var(--prometeus-text-secondary); margin:0;">
          Mapeando postos de trabalho no Ministério do Trabalho e competências exigidas em vagas abertas.
        </p>
        <div class="engine-log-box">
          ${currentStep >= 5 ? '✓ 1.420 vagas ativas encontradas.<br>• CBO 2124-05 em alta no setor segurador.<br>• Exigência: Python, Fraudes, SUSEP.' : 'Cruzando dados do CAGED...'}
        </div>
      </div>
    </div>

    <!-- Console de Eventos Globais -->
    <div class="prometeus-card" style="margin-top:24px;">
      <div style="font-size:13px; font-weight:600; color:#ffffff; margin-bottom:10px;">Console de Logs do Agente em Execução:</div>
      <div class="engine-log-box" style="height:120px; font-size:12px;" id="live-log-container">
        ${job.logs.map(log => `<div>${log}</div>`).join('')}
      </div>
    </div>
  `;
}

export function bindLiveEvents(store, container) {
  // O store já emite notificações à medida que os timeouts da simulação avançam.
  const logContainer = container.querySelector('#live-log-container');
  if (logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }
}
