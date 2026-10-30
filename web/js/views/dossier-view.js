/** Dossiê executivo: todo indicador vem do resultado persistido. */
import { PILLAR_LABELS, escapeHtml, displayNumber, percentage, safeUrl, channelLabel, recommendationLabel } from '../dossier-format.js';

function paragraphs(text) {
  return String(text || '').split(/\n+/).filter(part => part.trim())
    .map(part => `<p>${escapeHtml(part)}</p>`).join('');
}
function inspectionButton(ids, label = 'Ver evidências') {
  const unique = [...new Set(ids || [])];
  return unique.length ? `<button type="button" class="dossier-source-button" data-evidence-ids="${escapeHtml(JSON.stringify(unique))}">${escapeHtml(label)}</button>` : '';
}
function evidenceIds(claimIds, claims) {
  return [...new Set((claimIds || []).flatMap(id => claims.find(claim => claim.claim_id === id)?.evidence_ids || []))];
}
function claimList(ids, claims, empty) {
  const selected = (ids || []).map(id => claims.find(claim => claim.claim_id === id)).filter(Boolean);
  return selected.length ? `<ul class="dossier-findings">${selected.map(claim => `<li>${escapeHtml(claim.statement)} ${inspectionButton(claim.evidence_ids)}</li>`).join('')}</ul>` : `<p class="dossier-muted">${escapeHtml(empty)}</p>`;
}
function pillarCard(name, pillar) {
  const label = PILLAR_LABELS[name] || 'Dimensão complementar';
  const present = pillar.is_present === true;
  const ids = pillar.evidence_ids || pillar.features?.evidence_ids || [];
  const score = Number(pillar.raw_score);
  const missingReason = /feature/i.test(pillar.missing_reason || '') ? 'Não foram obtidos dados verificados suficientes para esta dimensão.' : pillar.missing_reason;
  const tone = !present ? 'missing' : score >= 70 ? 'strong' : score >= 40 ? 'moderate' : 'weak';
  return `<article class="dossier-pillar" data-tone="${tone}">
    <h3>${escapeHtml(label)}</h3>
    ${present ? `<div class="dossier-pillar-score">${displayNumber(pillar.raw_score)} <span>/ 100</span></div>
      <meter min="0" max="100" value="${Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0}" aria-label="${escapeHtml(label)}"></meter>
      <p class="dossier-muted">Confiança analítica: ${percentage(pillar.confidence)}</p>`
      : `<p class="dossier-no-sample">Sem amostra suficiente</p><p class="dossier-muted">${escapeHtml(missingReason || 'Não foram obtidos dados comparáveis para esta dimensão.')}</p>`}
    ${inspectionButton(ids, 'Inspecionar base deste pilar')}
  </article>`;
}

function scoreAudit(audit, scoring) {
  const blocks=scoring.gate_details?.score_blocks || {};
  const internal=audit.internal || {};
  const pricing=audit.pricing || {};
  const evidence=audit.evidence || {};
  const money=value=>Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
  const priceReason = code => ({
    own_institution: 'Oferta da própria instituição; fora da comparação externa',
    not_qualified: 'Conteúdo sem qualificação para comparar preço',
    category_mismatch: 'Categoria de curso diferente da proposta',
    theme_mismatch: 'Tema diferente da proposta',
    category_or_theme_mismatch: 'Categoria ou tema diferente da proposta',
    total_not_observed: 'Investimento total não observado com segurança',
    ambiguous_payment_condition: 'Vários preços sem vínculo inequívoco à oferta e condição',
    dated_offer_requires_current_confirmation: 'Preço histórico precisa de confirmação atual'
  })[code] || 'Condição comercial sem suporte suficiente';
  return `${Object.keys(blocks).length ? `<section class="dossier-section"><h2>Composição da avaliação</h2><p class="dossier-muted">Cada bloco mantém sua origem e cobertura. Aderência e preço cruzam fontes; entram uma única vez no consolidado.</p><div class="dossier-pillars">${Object.entries(blocks).map(([key,block])=>`<article class="dossier-pillar"><h3>${({internal:'Score interno · IPD',external:'Score externo · Mercado',alignment:'Aderência curricular',pricing:'Precificação combinada'})[key] || escapeHtml(key)}</h3><p class="dossier-pillar-score">${block.score == null ? 'Sem base suficiente' : displayNumber(block.score)+' / 100'}</p><p>Cobertura do bloco: ${percentage(block.coverage)}</p><p class="dossier-muted">Confiança: ${percentage(block.confidence)}</p></article>`).join('')}</div></section>` : ''}
  ${internal.comparables ? `<section class="dossier-section"><h2>Comparáveis internos e IPD</h2><p>Até três cursos da mesma família, selecionados por tema e grade quando disponível. Referência: ${escapeHtml(internal.reference_n ?? 0)} cursos na janela ${escapeHtml(internal.reference_period || 'não confirmada')}.</p>${(internal.limitations || []).map(text=>`<p class="dossier-muted">${escapeHtml(text)}</p>`).join('')}<ul>${internal.comparables.map(row=>`<li><strong>${escapeHtml(row.name)}</strong> · IPD ${row.ipd_score==null?'indisponível':displayNumber(row.ipd_score)}<p>${escapeHtml(row.reason)}</p>${inspectionButton(row.evidence_ids || [])}</li>`).join('')}</ul></section>` : ''}
  ${pricing.method ? `<section class="dossier-section"><h2>Referência de preço</h2><p>${pricing.mean_total_brl==null ? 'Sem preços totais comparáveis suficientes.' : `Média por curso: <strong>${money(pricing.mean_total_brl)}</strong> de investimento total.`}</p><p>${escapeHtml(pricing.internal_count || 0)} cursos internos e ${escapeHtml(pricing.external_count || 0)} externos comparáveis. Prazo de pagamento é independente da duração acadêmica.</p>${(pricing.limitations || []).map(text=>`<p class="dossier-muted">${escapeHtml(text)}</p>`).join('')}<ul>${(pricing.comparables || []).map(row=>`<li>${escapeHtml(row.name)} · ${row.origin==='internal'?'Interno':'Concorrente externo'} · ${money(row.total_brl)}${row.installments ? ` · ${escapeHtml(row.installments)} parcela(s)` : ''} ${inspectionButton(row.evidence_ids || [])}</li>`).join('')}</ul>${(pricing.excluded || []).length ? `<details><summary>Preços fora da referência (${pricing.excluded.length})</summary><ul>${pricing.excluded.map(row=>`<li>${escapeHtml(priceReason(row.reason_code))} ${row.origin==='external' ? inspectionButton([row.id], 'Inspecionar página') : ''}</li>`).join('')}</ul><p class="dossier-muted">Ficar fora da referência de preço não exclui automaticamente a página dos outros usos.</p></details>` : ''}</section>` : ''}
  ${evidence.sources ? `<section class="dossier-section"><h2>Aproveitamento e perdas da pesquisa</h2><p>${evidence.collected_records} registros coletados; ${evidence.accepted_records} qualificados para indicadores, ${evidence.context_records} preservados como contexto e ${evidence.excluded_records} excluídos. ${evidence.used_in_score_records} capturas sustentam os pilares calculados.</p><p class="dossier-muted">Uma captura pode repetir a mesma entidade. Contexto preservado continua útil à redação, sem virar contagem de demanda.</p><div class="dossier-audit-grid">${Object.entries(evidence.sources).map(([source,info])=>`<details><summary>${escapeHtml(channelLabel(source))}: ${info.accepted_records} de ${info.collected_records} qualificados</summary><p>${info.context_records} em contexto · ${info.excluded_records} excluídos · ${info.used_in_score_records} usados no cálculo</p><ul>${Object.entries(info.reasons || {}).map(([reason,count])=>`<li>${escapeHtml(reason)}: ${count}</li>`).join('')}</ul></details>`).join('')}</div>${(audit.source_failures || []).length?`<details><summary>Consultas sem dados utilizáveis</summary><ul>${audit.source_failures.map(row=>`<li>${escapeHtml(channelLabel('apify_'+row.source))}: ${escapeHtml(row.query)} — ${escapeHtml(row.reason || 'Consulta concluída sem resultados')}</li>`).join('')}</ul></details>`:''}</section>` : ''}`;
}

function renderThreeFoldReview(review) {
  if (!review) return '';
  const di = review.data_integrity || {};
  const sa = review.senior_analytical || {};
  const fd = review.factual_drafting || {};
  const statusLabel = s => s === 'PASS' ? 'Homologado' : s === 'WARN' ? 'Alerta / Limitação' : 'Revisão necessária';
  const statusTone = s => s === 'PASS' ? 'strong' : s === 'WARN' ? 'moderate' : 'weak';
  return `<section class="dossier-section">
    <h2>Homologação em três frentes de revisão</h2>
    <p class="dossier-muted">${escapeHtml(review.summary || 'Auditoria técnica, analítica e factual.')}</p>
    <div class="dossier-pillars">
      <article class="dossier-pillar" data-tone="${statusTone(di.status)}">
        <h3>1. Integridade dos dados</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(di.status))}</p>
        <p class="dossier-muted">${di.brief_facts_count || 0} fatos auditados a partir de ${di.source_count || 0} fontes brutas.</p>
        ${di.missing_descriptions_count ? `<p class="dossier-muted">${di.missing_descriptions_count} descrições parciais preservadas como limitações.</p>` : ''}
      </article>
      <article class="dossier-pillar" data-tone="${statusTone(sa.status)}">
        <h3>2. Qualidade analítica sênior</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(sa.status))}</p>
        <p class="dossier-muted">${sa.independence_verified ? 'Independência institucional confirmada' : 'Conflito de concorrência detectado'}.</p>
        <p class="dossier-muted">${sa.proxies_properly_qualified ? 'Proxies de vagas e demanda qualificados' : 'Requer ajuste na qualificação de proxies'}.</p>
      </article>
      <article class="dossier-pillar" data-tone="${statusTone(fd.status)}">
        <h3>3. Factualidade da redação</h3>
        <p class="dossier-pillar-score">${escapeHtml(statusLabel(fd.status))}</p>
        <p class="dossier-muted">${fd.no_hallucinations ? 'Sem alucinações numéricas' : 'Alucinação detectada'}.</p>
        <p class="dossier-muted">${fd.unsupported_claims_count === 0 ? 'Todas as afirmações possuem evidências' : `${fd.unsupported_claims_count} afirmação(ões) sem suporte`}.</p>
      </article>
    </div>
    ${(review.actionable_feedback || []).length ? `<details><summary>Recomendações das revisões (${review.actionable_feedback.length})</summary><ul>${review.actionable_feedback.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></details>` : ''}
  </section>`;
}

export function renderDossierView(store) {
  const state = store.getState();
  const course = state.courses.find(item => item.id === state.activeCourseId);
  const dossier = state.currentDossier || course?.dossier;
  if (!course || !dossier) return `<div class="prometeus-card"><h2>Dossiê indisponível</h2><p>A análise ainda não possui um dossiê validado. Acompanhe o processamento no portfólio.</p><button class="prometeus-btn-secondary" id="btn-back-portfolio">Voltar ao portfólio</button></div>`;
  const scoring = dossier.scoring || {};
  const claims = Array.isArray(dossier.claims) ? dossier.claims : [];
  const sections = Array.isArray(dossier.sections) ? dossier.sections : [];
  const evidences = Array.isArray(dossier.evidences) ? dossier.evidences : [];
  const highlights = dossier.highlights || {};
  const pillars = scoring.pillar_scores || {};
  const present = Object.values(pillars).filter(pillar => pillar.is_present === true).length;
  const groups = new Map();
  evidences.forEach(evidence => { const key = channelLabel(evidence.source_name); groups.set(key, [...(groups.get(key) || []), evidence]); });
  const limitations = Array.isArray(dossier.limitations) ? dossier.limitations : [];
  const insufficient = scoring.recommendation === 'INSUFFICIENT_EVIDENCE';
  const v2=scoring.profile_id === 'portfolio-v2' || scoring.gate_details?.profile_id === 'portfolio-v2';
  return `<div class="dossier-page">
    <div class="dossier-toolbar">
      <button class="prometeus-btn-secondary" id="btn-back-portfolio">Voltar ao portfólio</button>
      <div><button class="prometeus-btn-secondary" id="btn-open-evidence-drawer">Inspecionar evidências</button>
      <button class="prometeus-btn-primary" id="btn-export-dossier-pdf">Imprimir / salvar PDF</button></div>
    </div>
    <header class="dossier-verdict-banner dossier-heading">
      <div class="verdict-info">
        <span class="prometeus-pill-badge" data-status="${escapeHtml(scoring.recommendation)}">${escapeHtml(recommendationLabel(scoring.recommendation))}</span>
        <h1 class="verdict-course-name">${escapeHtml(course.name)}</h1>
        <p class="dossier-context">${[course.level, course.modality].filter(Boolean).map(escapeHtml).join(' · ')}</p>
        ${insufficient ? '<p>A base disponível ainda não sustenta uma recomendação de lançamento. As lacunas abaixo indicam o que precisa ser validado.</p>' : '<p>Parecer de apoio à decisão institucional, sujeito às limitações da pesquisa.</p>'}
      </div>
      <dl class="dossier-indicators">
        <div><dt>${v2 && insufficient ? 'Índice observado · provisório' : 'Índice de viabilidade'}</dt><dd>${v2 && Number(scoring.coverage_score)===0 ? 'Sem base' : displayNumber(scoring.viability_score)} <small>/ 100</small></dd>${v2?'<span>A nota usa somente dimensões cobertas; lacunas limitam a recomendação.</span>':''}</div>
        <div><dt>Cobertura de evidências</dt><dd>${percentage(scoring.coverage_score)}</dd><span>${present} de ${Object.keys(pillars).length} dimensões com dados · cobertura ponderada</span></div>
        <div><dt>Confiança analítica</dt><dd>${percentage(scoring.confidence_score)}</dd><span>Qualidade do suporte analítico; não é chance de sucesso</span></div>
      </dl>
    </header>
    ${scoring.is_experimental !== false ? '<p class="dossier-notice">Índice experimental: pesos e limiares sujeitos a calibração. Este resultado não é uma projeção de retorno financeiro.</p>' : ''}
    <section class="dossier-summary"><h2>Síntese executiva</h2>${paragraphs(dossier.executive_summary)}
      ${inspectionButton(evidenceIds(dossier.executive_summary_claim_ids || [], claims), 'Ver base da síntese')}</section>
    <div class="curriculum-gap-grid dossier-diagnosis">
      <section class="gap-column-solutions"><h2>Pontos fortes e oportunidades</h2>${claimList(highlights.pros, claims, 'Ainda não há pontos fortes destacados com suporte nesta versão do dossiê.')}</section>
      <section class="gap-column-pains"><h2>Riscos e lacunas</h2>${claimList(highlights.cons, claims, 'Consulte os pilares e as limitações para identificar o que ainda precisa ser validado.')}</section>
    </div>
    <section class="dossier-section"><h2>As dimensões da viabilidade</h2><p class="dossier-muted">Ausência de dados não significa desempenho negativo. Cada dimensão mantém seu peso no índice.</p>
      <div class="dossier-pillars">${Object.entries(PILLAR_LABELS).map(([name]) => pillarCard(name, pillars[name] || {})).join('')}</div></section>
    ${scoreAudit(dossier.analysis_audit || {},scoring)}
    ${renderThreeFoldReview(dossier.three_fold_review || (dossier.presentation || {}).three_fold_review)}
    <section class="dossier-section"><h2>Comparação de ofertas</h2>
      ${(highlights.competitors || []).length ? `<div class="prometeus-table-container"><table class="prometeus-table"><thead><tr><th scope="col">Instituição e oferta</th><th scope="col">Condições observadas</th></tr></thead><tbody>${highlights.competitors.map(row => `<tr><th scope="row">${escapeHtml(row.label)}</th><td>${claimList(row.claim_ids, claims, 'Sem informação vinculada.')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="dossier-muted">Ainda não há um quadro de ofertas comparáveis nesta versão. Consulte as páginas coletadas sem presumir equivalência de preços ou modalidades.</p>'}
    </section>
    <section class="dossier-section"><h2>Ementa e necessidades do mercado</h2>
      ${(highlights.curriculum_alignment || []).length ? `<div class="prometeus-table-container"><table class="prometeus-table"><thead><tr><th scope="col">Módulo da ementa</th><th scope="col">Necessidade observada</th><th scope="col">Cobertura e lacunas</th></tr></thead><tbody>${highlights.curriculum_alignment.map(row => `<tr><th scope="row">${escapeHtml(row.module)}</th><td>${claimList(row.need_claim_ids, claims, 'Necessidade sem vínculo.')}</td><td>${claimList(row.coverage_claim_ids, claims, 'Cobertura sem vínculo.')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="dossier-muted">A relação por módulo requer necessidades de mercado e trechos da ementa com suporte. A leitura acadêmica abaixo registra o diagnóstico disponível.</p>'}
    </section>
    <section class="dossier-section"><h2>Leituras por área</h2><div class="business-cards-grid dossier-audiences">
      ${sections.map(section => `<article class="business-card"><h3>${escapeHtml(section.title)}</h3>${paragraphs(section.content)}
        <details><summary>Afirmações desta leitura</summary>${claimList(section.claim_ids, claims, 'Esta seção não possui afirmações vinculadas.')}</details>
        ${inspectionButton(evidenceIds(section.claim_ids, claims), 'Inspecionar fontes desta análise')}</article>`).join('')}
    </div></section>
    <section class="dossier-section"><h2>Validações antes do lançamento</h2><p class="dossier-muted">Condições propostas para avaliação da equipe. A conclusão depende de validação institucional.</p>
      ${(highlights.validation_criteria || []).length ? `<ul class="dossier-validation-list">${highlights.validation_criteria.map(item => `<li><span class="dossier-label">Pendente</span><div><h3>${escapeHtml(item.criterion)}</h3><p>${escapeHtml(item.target)}</p>${inspectionButton(evidenceIds(item.claim_ids, claims))}</div></li>`).join('')}</ul>` : '<p>Nenhum checklist foi estruturado nesta versão. Use as lacunas identificadas como pauta para a próxima validação.</p>'}
    </section>
    <section class="dossier-section"><h2>Próximos passos propostos</h2><div class="dossier-actions">
      ${(highlights.action_recommendations || []).map(item => `<article><div class="dossier-action-meta"><span>${escapeHtml(item.area)}</span><span>Prioridade ${{ high: 'alta', medium: 'média', low: 'baixa' }[item.priority] || 'não informada'}</span></div><p>${escapeHtml(item.action)}</p>${inspectionButton(evidenceIds(item.claim_ids, claims))}</article>`).join('') || '<p>As recomendações desta versão estão nas leituras por área.</p>'}
    </div></section>
    ${limitations.length ? `<section class="dossier-section"><h2>Limites desta pesquisa</h2><ul>${limitations.map(text => `<li>${escapeHtml(text)}</li>`).join('')}</ul></section>` : ''}
    <section class="dossier-section"><h2>Fontes consultadas</h2><p class="dossier-muted">${evidences.length} evidências persistidas. Itens do mesmo site ou canal não representam fontes independentes.</p>
      <div class="dossier-sources">${[...groups].map(([channel, items]) => `<section><h3>${escapeHtml(channel)} <span>(${items.length})</span></h3><ul>${items.map(evidence => {
        const url = safeUrl(evidence.source_url);
        const qualification = evidence.sanitized_data?._qualification;
        return `<li>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(evidence.title || channel)}</a>` : escapeHtml(evidence.title || channel)}
          ${qualification ? `<span class="dossier-label">${qualification.accepted ? 'Qualificada' : qualification.context_only ? 'Contexto preservado' : 'Excluída do cálculo'}</span><p class="dossier-muted">${escapeHtml(qualification.reason || '')}</p>${qualification.use_for?.length ? `<small>Uso: ${qualification.use_for.map(purpose=>escapeHtml(({employability:'vagas',curriculum:'necessidades curriculares',pricing:'referência de preço',competitive_offers:'ofertas comparáveis',paid_competition:'concorrência em mídia',audience_needs:'necessidades do público',institution_context:'contexto da própria instituição',search_interest:'interesse de busca'})[purpose] || purpose)).join(', ')}</small>` : ''}` : ''}
          ${inspectionButton([evidence.id], 'Inspecionar')}</li>`;
      }).join('')}</ul></section>`).join('') || '<p>Não há fontes externas anexadas. Consulte o estado das coletas.</p>'}</div>
    </section>
    <details class="dossier-claims"><summary>Afirmações e suporte analítico</summary>${claims.map(claim => `<article><p>${escapeHtml(claim.statement)}</p><span class="dossier-label">${({ observed: 'Observado', suggestive: 'Indício', hypothesis: 'Hipótese' })[claim.support_level] || 'Suporte declarado'}</span> ${inspectionButton(claim.evidence_ids)}</article>`).join('')}</details>
  </div>`;
}

export function bindDossierEvents(store, container) {
  container.querySelector('#btn-back-portfolio')?.addEventListener('click', () => store.setView('portfolio'));
  container.querySelector('#btn-export-dossier-pdf')?.addEventListener('click', () => window.print());
  container.querySelectorAll('[data-evidence-ids]').forEach(button => button.addEventListener('click', () => {
    document.dispatchEvent(new CustomEvent('prometeus:inspect-evidence', { detail: { ids: JSON.parse(button.dataset.evidenceIds), trigger: button } }));
  }));
}
