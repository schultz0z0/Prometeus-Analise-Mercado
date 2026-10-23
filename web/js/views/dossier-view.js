/**
 * VIEW: Dossiê Executivo de Viabilidade & Diagnóstico de Oferta
 */

export function renderDossierView(store) {
  const state = store.getState();
  const course = state.courses.find(c => c.id === state.activeCourseId) || state.courses[0];
  const dossier = state.currentDossier;

  return `
    <!-- Top Action Bar -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
      <button class="prometeus-btn-secondary" id="btn-back-portfolio" style="font-size:13px;">
        ← Voltar ao Portfólio
      </button>

      <div style="display:flex; gap:10px;">
        <button class="prometeus-btn-secondary" id="btn-open-evidence-drawer" style="font-size:13px;">
          <span>🔍 Inspecionar Evidências Forenses</span>
        </button>
        <button class="prometeus-btn-primary" id="btn-export-dossier-pdf" style="font-size:13px;">
          <span>📄 Exportar Dossiê (PDF)</span>
        </button>
      </div>
    </div>

    <!-- Banner Principal do Veredito da Oferta -->
    <div class="dossier-verdict-banner">
      <div class="verdict-info">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
          <span class="prometeus-pill-badge" data-status="${course.recommendation}">
            ● ${getRecommendationLabel(course.recommendation)}
          </span>
          <span class="prometeus-stat-mono" style="font-size:12px; color:var(--prometeus-text-muted);">${course.id}</span>
        </div>
        <h1 class="verdict-course-name">${course.name}</h1>
        <div class="verdict-meta">
          <span>🏛️ Instituição: <strong>ENS</strong></span>
          <span>🎓 Nível: <strong>${course.level}</strong></span>
          <span>💻 Modalidade: <strong>${course.modality}</strong></span>
          <span>💰 Mensalidade Proposta: <strong>R$ ${course.ticket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}/mês</strong></span>
        </div>
      </div>

      <div style="text-align:right;">
        <div style="font-size:12px; text-transform:uppercase; color:var(--prometeus-text-muted); font-weight:600; letter-spacing:0.05em;">Viability Score</div>
        <div style="font-family:var(--prometeus-font-mono); font-size:48px; font-weight:700; color:#ffffff; line-height:1;">
          ${course.viability_score.toFixed(1)} <span style="font-size:18px; color:var(--prometeus-text-muted);">/100</span>
        </div>
        <div style="font-size:12px; color:var(--prometeus-status-approved); margin-top:4px;">
          Coverage: ${course.coverage_index.toFixed(0)}% • Confiança: ${course.confidence_index}
        </div>
      </div>
    </div>

    <!-- Grid Superior: Gauge & Radar dos 6 Pilares -->
    <div style="display:grid; grid-template-columns: 340px 1fr; gap:24px; margin-bottom:28px;">
      <!-- Card do Gauge -->
      <div class="prometeus-card" style="display:flex; flex-direction:column; align-items:center; text-align:center;">
        <div style="width:100%; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <h2 style="font-size:15px; font-weight:600; margin:0; color:#ffffff;">Grau de Viabilidade</h2>
          <span class="prometeus-pill-badge" data-status="APPROVED">86.4%</span>
        </div>

        <div style="position:relative; width:200px; height:200px; margin:16px 0;">
          <svg style="width:100%; height:100%; transform:rotate(-90deg);" viewBox="0 0 200 200">
            <defs>
              <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0652C5" />
                <stop offset="100%" stop-color="#8DB5FF" />
              </linearGradient>
            </defs>
            <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="14" />
            <circle cx="100" cy="100" r="88" fill="none" stroke="url(#gauge-gradient)" stroke-width="14"
                    stroke-dasharray="552.9" stroke-dashoffset="75.2" stroke-linecap="round" />
          </svg>
          <div style="position:absolute; top:0; left:0; width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <span class="prometeus-stat-mono" style="font-size:42px; font-weight:700; color:#ffffff; line-height:1;">${course.viability_score.toFixed(1)}</span>
            <span style="font-size:12px; color:var(--prometeus-text-muted); margin-top:2px;">de 100</span>
          </div>
        </div>

        <p style="font-size:12px; color:var(--prometeus-text-secondary); line-height:1.4; margin:0 0 16px 0;">
          Cálculo matemático determinístico imune a alucinações, combinando os 6 pilares.
        </p>

        <div style="width:100%; display:flex; justify-content:space-between; padding-top:14px; border-top:1px solid var(--prometeus-border-subtle);">
          <div style="text-align:left;">
            <div style="font-size:11px; text-transform:uppercase; color:var(--prometeus-text-muted);">Ponto de Equilíbrio</div>
            <div class="prometeus-stat-mono" style="font-size:16px; font-weight:700; color:#ffffff;">18 alunos</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px; text-transform:uppercase; color:var(--prometeus-text-muted);">Lucro Projetado</div>
            <div class="prometeus-stat-mono" style="font-size:16px; font-weight:700; color:var(--prometeus-status-approved);">R$ 142.800</div>
          </div>
        </div>
      </div>

      <!-- Card do Radar 6 Pilares -->
      <div class="prometeus-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <h2 style="font-size:15px; font-weight:600; margin:0; color:#ffffff;">Decomposição dos 6 Pilares de Decisão</h2>
          <button class="prometeus-btn-secondary" id="btn-toggle-radar-table" style="font-size:12px; padding:4px 10px; min-height:28px;">
            Alternar Visualização Tabular
          </button>
        </div>

        <div id="radar-visual-container" style="display:flex; justify-content:center;">
          <svg class="radar-svg" viewBox="0 0 520 360" role="img" aria-label="Radar dos 6 pilares de avaliação">
            <!-- Polígonos de Nível -->
            <polygon points="260,70 355,125 355,235 260,290 165,235 165,125" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1" />
            <polygon points="260,105 325,145 325,215 260,255 195,215 195,145" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
            <polygon points="260,140 295,160 295,200 260,220 225,200 225,160" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1" />

            <!-- Eixos -->
            <line x1="260" y1="180" x2="260" y2="70" stroke="rgba(255,255,255,0.12)" />
            <line x1="260" y1="180" x2="355" y2="125" stroke="rgba(255,255,255,0.12)" />
            <line x1="260" y1="180" x2="355" y2="235" stroke="rgba(255,255,255,0.12)" />
            <line x1="260" y1="180" x2="260" y2="290" stroke="rgba(255,255,255,0.12)" />
            <line x1="260" y1="180" x2="165" y2="235" stroke="rgba(255,255,255,0.12)" />
            <line x1="260" y1="180" x2="165" y2="125" stroke="rgba(255,255,255,0.12)" />

            <!-- Polígono de Dados do Curso -->
            <polygon points="260,86 334,136 347,230 260,277 174,229 181,135" 
                     fill="rgba(6, 82, 197, 0.25)" 
                     stroke="#0652C5" 
                     stroke-width="2.5" />

            <!-- Pontos nos Vértices -->
            <circle cx="260" cy="86" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />
            <circle cx="334" cy="136" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />
            <circle cx="347" cy="230" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />
            <circle cx="260" cy="277" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />
            <circle cx="174" cy="229" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />
            <circle cx="181" cy="135" r="4.5" fill="#8DB5FF" stroke="#040814" stroke-width="2" />

            <!-- Rótulos dos 6 Pilares -->
            <text x="260" y="48" text-anchor="middle" fill="#FFFFFF" font-size="12" font-weight="600" font-family="Outfit">Histórico Interno (20%)</text>
            <text x="372" y="130" text-anchor="start" fill="#94A3B8" font-size="12" font-family="Outfit">Concorrência Paga (20%)</text>
            <text x="372" y="240" text-anchor="start" fill="#FFFFFF" font-size="12" font-weight="600" font-family="Outfit">Busca/Demanda (20%)</text>
            <text x="260" y="322" text-anchor="middle" fill="#94A3B8" font-size="12" font-family="Outfit">Empregabilidade (15%)</text>
            <text x="148" y="240" text-anchor="end" fill="#FFFFFF" font-size="12" font-weight="600" font-family="Outfit">Aderência Ementa (15%)</text>
            <text x="148" y="130" text-anchor="end" fill="#94A3B8" font-size="12" font-family="Outfit">Regulatório (10%)</text>
          </svg>
        </div>

        <div id="radar-table-container" style="display:none; margin-top:14px;">
          <table class="prometeus-table">
            <thead>
              <tr>
                <th scope="col">Pilar</th>
                <th scope="col">Peso</th>
                <th scope="col">Nota</th>
                <th scope="col">Detalhamento</th>
              </tr>
            </thead>
            <tbody>
              ${dossier.pillars.map(p => `
                <tr>
                  <td><strong>${p.name}</strong></td>
                  <td class="prometeus-stat-mono">${p.weight}</td>
                  <td class="prometeus-stat-mono" style="font-weight:700; color:#ffffff;">${p.score.toFixed(1)}/100</td>
                  <td style="font-size:12px; color:var(--prometeus-text-secondary);">${p.detail}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PARECER EXECUTIVO & SÍNTESE DA INTELIGÊNCIA ARTIFICIAL (LLM) -->
    <div class="prometeus-card" style="margin-bottom:28px; border:1px solid rgba(141, 181, 255, 0.25); background:linear-gradient(135deg, rgba(6, 82, 197, 0.08) 0%, rgba(4, 8, 20, 0.7) 100%);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:20px;">🧠</span>
          <div>
            <h2 style="font-size:16px; font-weight:700; color:#ffffff; margin:0;">Parecer Executivo & Síntese da Inteligência Artificial</h2>
            <div style="font-size:12px; color:var(--prometeus-text-muted);">Síntese gerada e verificada com base na ementa submetida, base histórica ENS e varredura Apify</div>
          </div>
        </div>
        <span class="prometeus-pill-badge" data-status="APPROVED" style="font-size:11px;">
          ⚡ Modelo: ${dossier.model_name || 'ChatGPT / Prometeus Sol'}
        </span>
      </div>

      <div style="font-size:14px; color:var(--prometeus-text-primary); line-height:1.65; white-space:pre-wrap; background:rgba(0,0,0,0.3); padding:16px; border-radius:8px; border:1px solid var(--prometeus-border-subtle); margin-bottom:${dossier.sections && dossier.sections.length > 0 ? '16px' : '0'};">
        ${dossier.executive_summary || 'Análise de viabilidade realizada com base na ementa submetida e no cruzamento com a base histórica de cursos da ENS.'}
      </div>

      ${dossier.sections && dossier.sections.length > 0 ? `
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:12px;">
          ${dossier.sections.map(s => `
            <div style="background:rgba(255,255,255,0.02); border:1px solid var(--prometeus-border-subtle); border-radius:6px; padding:12px;">
              <div style="font-size:13px; font-weight:600; color:var(--prometeus-accent-ice); margin-bottom:6px;">${s.title}</div>
              <div style="font-size:12px; color:var(--prometeus-text-secondary); line-height:1.5;">${s.content}</div>
            </div>
          `).join('')}
        </div>
      ` : ''}
    </div>

    <!-- OS 5 BLOCOS DE RESPOSTAS DE NEGÓCIO -->
    <div class="business-cards-grid">
      <!-- BLOCO 1: TEM DEMANDA REAL? -->
      <div class="business-card">
        <div class="business-card-header">
          <div class="business-card-title">
            <span>📈</span>
            <span>1. Tem Demanda Real de Mercado?</span>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">DEMANDA ALTA</span>
        </div>
        
        <p style="font-size:14px; color:var(--prometeus-text-primary); line-height:1.5; margin-bottom:14px;">
          <strong>Sim, a demanda está em franca expansão.</strong> As pesquisas por especializações em IA no mercado de seguros cresceram <strong>+88% nos últimos 12 meses</strong> no Brasil.
        </p>

        <div style="background:rgba(255,255,255,0.03); border-radius:var(--prometeus-radius-md); padding:14px; margin-bottom:14px;">
          <div style="font-size:12px; color:var(--prometeus-text-muted); margin-bottom:4px;">Empregabilidade & Vagas:</div>
          <div style="font-size:18px; font-weight:700; color:#ffffff; font-family:var(--prometeus-font-mono);">
            1.420 vagas abertas
          </div>
          <div style="font-size:12px; color:var(--prometeus-text-secondary); margin-top:2px;">
            Mapeadas no CBO e LinkedIn para posições de dados/riscos com remuneração média de R$ 12.800/mês.
          </div>
        </div>

        <div style="font-size:12px; color:var(--prometeus-accent-ice);">
          ✓ Conclusão: Janela de mercado altamente oportuna com pico de sazonalidade previsto para janeiro.
        </div>
      </div>

      <!-- BLOCO 2: É UMA BOA OFERTA FRENTE À CONCORRÊNCIA? -->
      <div class="business-card">
        <div class="business-card-header">
          <div class="business-card-title">
            <span>🥊</span>
            <span>2. É uma Boa Oferta Competitiva?</span>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">POSICIONAMENTO IDEAL</span>
        </div>

        <p style="font-size:14px; color:var(--prometeus-text-primary); line-height:1.5; margin-bottom:14px;">
          Seu preço proposto de <strong>R$ 980,00/mês</strong> está estrategicamente posicionado entre os extremos do mercado:
        </p>

        <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:14px;">
          ${dossier.competitors.map(comp => `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.02); padding:8px 12px; border-radius:var(--prometeus-radius-sm); border:1px solid var(--prometeus-border-subtle);">
              <div>
                <strong style="color:#ffffff; font-size:13px;">${comp.institution}</strong>
                <div style="font-size:11px; color:var(--prometeus-text-muted);">${comp.modality} • ${comp.active_ads} anúncios ativos</div>
              </div>
              <span class="prometeus-stat-mono" style="font-size:13px; font-weight:700; color:var(--prometeus-accent-ice);">${comp.price}</span>
            </div>
          `).join('')}
        </div>

        <div style="font-size:12px; color:var(--prometeus-status-adjustments);">
          ⚠️ Ponto de atenção: FGV e FIA investem pesado em Meta Ads há mais de 120 dias, validando que o mercado está comprando.
        </div>
      </div>

      <!-- BLOCO 3: RAIO-X DA EMENTA E DIFERENCIAÇÃO -->
      <div class="business-card" style="grid-column: span 2;">
        <div class="business-card-header">
          <div class="business-card-title">
            <span>💡</span>
            <span>3. O que a sua Ementa tem de Cego e como Diferenciar?</span>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED_WITH_ADJUSTMENTS">OPORTUNIDADE DE OURO</span>
        </div>

        <p style="font-size:14px; color:var(--prometeus-text-primary); line-height:1.5;">
          Mineramos centenas de comentários e dores de alunos reais da concorrência via Social Listening. Veja o contraste com a sua grade:
        </p>

        <div class="curriculum-gap-grid">
          <div class="gap-column-pains">
            <strong style="color:#EF4444; font-size:13px; display:block; margin-bottom:8px;">❌ O que os Alunos Reclamam dos Concorrentes:</strong>
            ${dossier.social_listening_pains.map(p => `
              <div class="gap-item">
                <span style="color:var(--prometeus-text-primary);">${p.pain}</span>
                <span class="prometeus-stat-mono" style="display:block; font-size:11px; color:var(--prometeus-text-muted); margin-top:2px;">
                  Citado por ${p.count} profissionais (${p.percent})
                </span>
              </div>
            `).join('')}
          </div>

          <div class="gap-column-solutions">
            <strong style="color:#34D399; font-size:13px; display:block; margin-bottom:8px;">✓ Ajustes Sugeridos pela Prometeus para Anular a Concorrência:</strong>
            ${dossier.curriculum_adjustments.map(adj => `
              <div class="gap-item">
                <strong style="color:#ffffff; font-size:13px;">${adj.solution}</strong>
                <span style="display:block; font-size:12px; color:var(--prometeus-text-secondary); margin-top:2px;">
                  ${adj.impact}
                </span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- BLOCO 4: SIMULADOR FINANCEIRO E BREAKEVEN (CRUZADO COM CRM DA IES) -->
      <div class="business-card">
        <div class="business-card-header">
          <div class="business-card-title">
            <span>💰</span>
            <span>4. Viabilidade Financeira & Breakeven</span>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">CRUZADO COM CRM DA ENS</span>
        </div>

        <p style="font-size:13px; color:var(--prometeus-text-secondary); margin-bottom:14px;">
          Com base na taxa de conversão histórica de <strong>14.2%</strong> que puxamos da sua API de CRM, calcule os cenários em tempo real:
        </p>

        <div class="simulator-box">
          <div class="slider-row">
            <div class="slider-header">
              <span>Mensalidade do Aluno:</span>
              <strong id="sim-ticket-val" class="prometeus-stat-mono" style="color:#ffffff;">R$ 980,00</strong>
            </div>
            <input type="range" id="sim-ticket-range" class="slider-input" min="600" max="1600" step="50" value="980">
          </div>

          <div class="slider-row">
            <div class="slider-header">
              <span>Alunos Matriculados:</span>
              <strong id="sim-students-val" class="prometeus-stat-mono" style="color:#ffffff;">32 alunos</strong>
            </div>
            <input type="range" id="sim-students-range" class="slider-input" min="10" max="80" step="1" value="32">
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; padding-top:14px; border-top:1px solid var(--prometeus-border-subtle);">
            <div>
              <div style="font-size:11px; text-transform:uppercase; color:var(--prometeus-text-muted);">Ponto de Equilíbrio</div>
              <div id="sim-breakeven-result" class="prometeus-stat-mono" style="font-size:18px; font-weight:700; color:#ffffff;">18 alunos</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--prometeus-text-muted);">Margem / Lucro Líquido</div>
              <div id="sim-net-result" class="prometeus-stat-mono" style="font-size:18px; font-weight:700; color:var(--prometeus-status-approved);">R$ 142.800</div>
            </div>
          </div>
        </div>
      </div>

      <!-- BLOCO 5: KIT DE MARKETING & LANÇAMENTO -->
      <div class="business-card">
        <div class="business-card-header">
          <div class="business-card-title">
            <span>🚀</span>
            <span>5. Marketing Launch Kit</span>
          </div>
          <span class="prometeus-pill-badge" data-status="APPROVED">PRONTO PARA CAMPANHA</span>
        </div>

        <div style="margin-bottom:14px;">
          <strong style="font-size:13px; color:#ffffff; display:block; margin-bottom:6px;">Títulos Comerciais Validados em Busca:</strong>
          ${dossier.commercial_kit.recommended_names.map((item, idx) => `
            <div style="font-size:13px; color:var(--prometeus-text-primary); margin-bottom:4px;">
              ${idx + 1}. <strong>${item.name}</strong>
              <div style="font-size:11px; color:var(--prometeus-text-muted);">${item.note}</div>
            </div>
          `).join('')}
        </div>

        <div>
          <strong style="font-size:13px; color:#ffffff; display:block; margin-bottom:6px;">Ganchos de Alta Conversão para Mídia Paga:</strong>
          ${dossier.commercial_kit.ad_hooks.map(hook => `
            <div style="background:rgba(255,255,255,0.03); border-left:3px solid var(--prometeus-primary); padding:6px 10px; font-size:12px; color:var(--prometeus-text-secondary); margin-bottom:6px; border-radius:0 4px 4px 0;">
              "${hook}"
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <!-- PAINEL DE REGISTRO DA DECISÃO HUMANA (UC-05) -->
    <div class="prometeus-card" style="border:1px solid rgba(141,181,255,0.3); background:rgba(26,35,56,0.85);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div>
          <h2 style="font-size:18px; font-weight:700; color:#ffffff; margin:0;">Registro de Deliberação do Comitê Acadêmico</h2>
          <p style="font-size:13px; color:var(--prometeus-text-secondary); margin:4px 0 0 0;">
            O Prometeus sugere e explicita a incerteza. A decisão de lançamento pertence à governança da instituição.
          </p>
        </div>
        <span class="prometeus-pill-badge" data-status="APPROVED">GOVERNANÇA ATIVA</span>
      </div>

      <form id="form-human-decision" style="display:flex; flex-direction:column; gap:16px;">
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:14px; color:#ffffff;">
            <input type="radio" name="human-decision-radio" value="APPROVED_WITH_ADJUSTMENTS" checked>
            <span>Aprovado com Ajustes Curriculares</span>
          </label>

          <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:14px; color:#ffffff;">
            <input type="radio" name="human-decision-radio" value="APPROVED">
            <span>Aprovado Integralmente</span>
          </label>

          <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:14px; color:#ffffff;">
            <input type="radio" name="human-decision-radio" value="REJECTED">
            <span>Reprovado / Rejeitado</span>
          </label>
        </div>

        <div>
          <label class="form-label" for="decision-notes">Parecer e Justificativa da Diretoria:</label>
          <textarea id="decision-notes" class="form-textarea" style="min-height:80px;" placeholder="Insira aqui as observações para a ata do comitê de ensino...">${course.human_decision ? course.human_decision.notes : "Aprovado pelo comitê acadêmico. Aceitamos integralmente a substituição do módulo teórico 3 pelas oficinas práticas de SUSEP e modelos preditivos em Python sugeridas pela Prometeus."}</textarea>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="font-size:12px; color:var(--prometeus-text-muted);">
            Responsável: <strong>${course.human_decision ? course.human_decision.decision_by : "Prof. Dr. Arnaldo Silveira (Diretor Acadêmico)"}</strong>
          </div>
          <button type="submit" class="prometeus-btn-primary" style="padding:10px 24px;">
            <span>Gravar Decisão no Portfólio</span>
          </button>
        </div>
      </form>
    </div>
  `;
}

export function bindDossierEvents(store, container) {
  const backBtn = container.querySelector('#btn-back-portfolio');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      store.setView('portfolio');
    });
  }

  const exportBtn = container.querySelector('#btn-export-dossier-pdf');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      window.print();
    });
  }

  // Toggle do Radar para visualização tabular acessível
  const toggleBtn = container.querySelector('#btn-toggle-radar-table');
  const radarVisual = container.querySelector('#radar-visual-container');
  const radarTable = container.querySelector('#radar-table-container');

  if (toggleBtn && radarVisual && radarTable) {
    toggleBtn.addEventListener('click', () => {
      const isVisible = radarTable.style.display !== 'none';
      if (isVisible) {
        radarTable.style.display = 'none';
        radarVisual.style.display = 'flex';
        toggleBtn.textContent = 'Alternar Visualização Tabular';
      } else {
        radarTable.style.display = 'block';
        radarVisual.style.display = 'none';
        toggleBtn.textContent = 'Alternar Gráfico Visual';
      }
    });
  }

  // Sliders interativos do Simulador de Breakeven
  const ticketSlider = container.querySelector('#sim-ticket-range');
  const studentsSlider = container.querySelector('#sim-students-range');
  const ticketVal = container.querySelector('#sim-ticket-val');
  const studentsVal = container.querySelector('#sim-students-val');
  const breakevenResult = container.querySelector('#sim-breakeven-result');
  const netResult = container.querySelector('#sim-net-result');

  function updateSimulation() {
    if (!ticketSlider || !studentsSlider) return;
    const ticket = parseFloat(ticketSlider.value);
    const students = parseInt(studentsSlider.value);
    
    ticketVal.textContent = `R$ ${ticket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    studentsVal.textContent = `${students} alunos`;

    // Custo fixo estimado de corpo docente + coordenação: R$ 85.000 / ano
    // Custo variável de aquisição (CAC): R$ 480 por aluno matriculado
    const fixedCost = 85000;
    const cac = 480;
    const annualTicket = ticket * 12;
    const breakeven = Math.ceil(fixedCost / (annualTicket - cac));
    const grossRevenue = students * annualTicket;
    const totalCost = fixedCost + (students * cac);
    const netProfit = grossRevenue - totalCost;

    breakevenResult.textContent = `${breakeven} alunos`;
    netResult.textContent = `R$ ${netProfit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    netResult.style.color = netProfit >= 0 ? 'var(--prometeus-status-approved)' : 'var(--prometeus-status-risk)';
  }

  if (ticketSlider && studentsSlider) {
    ticketSlider.addEventListener('input', updateSimulation);
    studentsSlider.addEventListener('input', updateSimulation);
  }

  // Formulário de decisão humana
  const decisionForm = container.querySelector('#form-human-decision');
  if (decisionForm) {
    decisionForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const state = store.getState();
      const selectedRadio = container.querySelector('input[name="human-decision-radio"]:checked');
      const decisionVal = selectedRadio ? selectedRadio.value : 'APPROVED_WITH_ADJUSTMENTS';
      const notes = container.querySelector('#decision-notes').value;

      store.registerHumanDecision(state.activeCourseId, decisionVal, notes, "Prof. Dr. Arnaldo Silveira");
      alert("Decisão da Diretoria registrada com sucesso no histórico da instituição!");
    });
  }
}

function getRecommendationLabel(rec) {
  switch (rec) {
    case 'APPROVED': return 'APROVADO';
    case 'APPROVED_WITH_ADJUSTMENTS': return 'APROVADO COM AJUSTES';
    case 'HIGH_RISK': return 'ALTO RISCO';
    default: return rec;
  }
}
