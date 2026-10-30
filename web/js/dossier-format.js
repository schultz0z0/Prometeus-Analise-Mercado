/** Rótulos de negócio e formatação, sem criar métricas. */
export const PILLAR_LABELS = {
  internal_history: 'Histórico institucional', paid_competition: 'Concorrência em mídia paga',
  search_and_media: 'Interesse de busca e tendência', employability: 'Empregabilidade e vagas',
  syllabus_fit: 'Aderência curricular', pricing: 'Precificação'
};
export function escapeHtml(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}
export function displayNumber(value, digits = 1) {
  if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return 'Não disponível';
  return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export function percentage(value) {
  return value === null || value === undefined ? 'Não disponível' : `${displayNumber(Number(value) * 100, 0)}%`;
}
export function safeUrl(value) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; }
  catch { return ''; }
}
export function channelLabel(value) {
  const name = String(value || '').replace(/^apify_/, '');
  return ({ google_search: 'Google e sites', web_crawler: 'Sites de ofertas', meta_ads_library: 'Meta Ads',
    linkedin: 'LinkedIn empresas', linkedin_jobs: 'LinkedIn vagas', instagram: 'Instagram',
    tiktok: 'TikTok', youtube_comments: 'YouTube', google_trends: 'Google Trends', reddit: 'Reddit' })[name] || 'Outra fonte';
}
export function recommendationLabel(value) {
  return ({ APPROVED: 'Lançamento recomendado', APPROVED_WITH_ADJUSTMENTS: 'Viável com ajustes',
    HIGH_RISK: 'Alto risco mercadológico', INSUFFICIENT_EVIDENCE: 'Evidências insuficientes',
    REQUIRES_HUMAN_REVIEW: 'Requer deliberação humana' })[value] || 'Recomendação indisponível';
}
