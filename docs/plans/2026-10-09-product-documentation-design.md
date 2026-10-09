# Design da fundação documental do produto

**Data:** 2026-10-09  
**Status:** Aprovado pelo responsável do produto

## Contexto

O produto será um serviço B2B institucional, headless e white-label para avaliar novos cursos. O primeiro cliente é a ENS. A experiência do usuário ocorre em um chatbot existente, que consumirá o serviço via MCP e/ou REST.

## Decisões aprovadas

1. Código-base único com deployment Docker isolado por instituição.
2. Monólito modular com API, MCP, worker, PostgreSQL e Redis.
3. JEV obrigatório para julgamentos semânticos delimitados.
4. Código convencional para fórmulas, permissões e mudanças de estado.
5. LLM generativa restrita à síntese e recomendações baseadas em evidências.
6. Score, confiança e cobertura apresentados separadamente.
7. Workflow assíncrono com `analysis_id`, consulta de status e webhook.
8. Apify como infraestrutura preferencial de scraping, sujeito a avaliação de Actor, custo, termos e qualidade.
9. Adaptadores institucionais traduzem CRMs diferentes para um modelo canônico.
10. Toda conclusão relevante deve manter proveniência e versão.

## Opções consideradas

- **Deployment dedicado por instituição:** escolhido por isolamento, LGPD e simplicidade operacional.
- **SaaS multi-tenant compartilhado:** adiado por elevar complexidade e risco para uma equipe de dois desenvolvedores.
- **Core central com gateways dedicados:** possível evolução enterprise, mas prematuro.

## Fluxo aprovado

Entrada pelo chatbot, validação, gate JEV, expansão e classificação de palavras-chave, planejamento de pesquisa, coleta interna e externa, higienização, decisões JEV, cálculo determinístico, gate de qualidade, síntese generativa, validação da saída, persistência, webhook e feedback humano.

## Limites

Esta etapa prepara documentação e esqueleto de diretórios. Não declara integrações prontas nem implementa lógica de produção.

## Restrição operacional

O diretório ainda não era um repositório Git quando este design foi criado; por isso não foi possível cumprir a etapa de commit automático prevista no processo de brainstorming.
