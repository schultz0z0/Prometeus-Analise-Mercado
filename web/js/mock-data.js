/**
 * Estado inicial da interface.
 * Resultados de análise nunca são simulados no navegador. A única massa de
 * teste autorizada é a base histórica institucional, carregada pelo backend.
 */
export const INITIAL_TENANTS = [
  { id: "ens", name: "Escola de Negócios e Seguros", code: "ENS", segment: "Seguros" }
];

export const INITIAL_SETTINGS = {
  ens: {
    gen_llm_provider: "",
    gen_llm_model: "",
    gen_llm_reasoning_effort: "",
    chatgpt_access_token: "",
    jev_model: "",
    apify_max_charge: null
  }
};

export const INITIAL_COURSES = [];
export const INITIAL_HISTORICAL_COURSES = [];
export const DETAILED_DOSSIER = null;
