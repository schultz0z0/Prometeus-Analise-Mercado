# Market Evidence and Executive Dossier Implementation Plan

> Execução aprovada pelo responsável do produto em 2026-10-28, nesta conversa. Aplicar TDD e revisão independente; preservar alterações documentais existentes e `relatorio.md`.

**Goal:** corrigir a cadeia factual de pesquisa e entregar um dossiê executivo rastreável, sem atribuir cálculos ou mudanças de estado à IA.

**Architecture:** preservar portas de decisão e modos `traditional`/`hybrid`; normalizar e qualificar evidências antes do scoring. A LLM planeja e redige sobre contratos validados; blocos visuais referenciam claims verificadas. Coleta adicional segue política limitada de rodadas e orçamento.

**Tech Stack:** Python 3.11, Pydantic, SQLAlchemy, Apify, pytest, frontend JavaScript/CSS existente.

## 1. Coleta e higienização

Arquivos: `application/sanitization.py`, `application/collect_market_evidence.py`, `infrastructure/apify/registry.py`, `infrastructure/apify/client.py`, testes de mercado.

1. Reproduzir qualidade 0,10 em objeto limpo aninhado, URLs de canal aceitas, dependências ignoradas e SERPs agrupadas; observar falhas.
2. Corrigir recursão e limpeza de HTML sem penalizar HTML comum; manter detecção de injeção após decodificação.
3. Validar grafo de chamadas, usar somente origens declaradas, não revisitar URLs canônicas e persistir resultados orgânicos individuais com proveniência.
4. Excluir metadados/erros dos sinais sociais; validar URLs fornecidas integralmente. Preservar itens rejeitados como auditoria, sem pontuar.
5. Validar schemas oficiais antes de alterar builders. Normalizar local Brasil/Brazil e recorte; manter pin dos Actors e custo real.
6. Executar `rtk proxy .venv/Scripts/python.exe -m pytest tests/integration/market_sources tests/contract/market_sources -q` e revisar diff.

## 2. Planejamento, suficiência e features

Arquivos: `application/plan_course_research.py`, `application/evidence_features.py`, `application/scoring_service.py`, `application/run_course_analysis.py`, `domain/research.py`, `skills/planning-market-research/SKILL.md`.

1. Testar catálogo somente com fontes habilitadas, dependências inválidas, ausência versus zero observado, geografia, metadados sociais, preços comparáveis e série temporal Trends.
2. Injetar contrato descritivo por capability com finalidade, entradas, limites e evidência esperada; planejar buscas distintas por intenção.
3. Normalizar métricas observadas e filtrar pertinência/escopo antes de contar; manter IDs e motivos de exclusão.
4. Impedir presença de pilar sem proveniência; distinguir ausência de coleta de zero observado. Não alterar fórmulas ou pesos silenciosamente.
5. Adicionar avaliação de lacunas e uma rodada adicional limitada, com orçamento cumulativo, queries novas, plano persistido e falhas explícitas. Testar retomada sem repetir cobrança.
6. Executar testes de features, scoring, planejamento e fluxo ponta a ponta.

## 3. Contrato e verificação do dossiê

Arquivos: `domain/dossiers.py`, `application/dossier_verifier.py`, `application/synthesize_dossier.py`, `infrastructure/llm/client.py`, `config/prompts/dossier-v1.yaml`, `entrypoints/rest/app.py`.

1. Testar número inventado em claim qualitativa, resumo, seção e bloco novo; testar referências inválidas e validação institucional fabricada.
2. Introduzir destaques tipados com IDs de claims (pontos fortes, riscos, critérios pendentes e ações propostas); compatibilidade com saída v1.
3. Verificar números e URLs independentemente do tipo e em todos os textos; vincular conteúdo aos fatos citados e controlar certeza/hipóteses.
4. Preservar campos normalizados, escopo, trechos e limitações nos fatos; contextualizar cobertura ponderada, confiança e score experimental.
5. Propagar contrato por cliente LLM, persistência e endpoints sem exigir migração destrutiva; testar round-trip e dossiês antigos.
6. Executar `rtk proxy .venv/Scripts/python.exe -m pytest tests/unit/dossiers tests/integration/dossiers tests/evaluation/dossier -q`.

## 4. Dashboard executivo

Arquivos: `web/js/views/dossier-view.js`, `web/js/components/evidence-drawer.js`, `web/styles/app.css` e testes frontend.

1. Testar renderização de `claim.statement`, referências seção → claims → evidências, zero versus ausente, traduções e dados faltantes.
2. Implementar síntese e recomendação em português, três indicadores, seis pilares, forças/riscos, ações propostas e fontes agrupadas. Preservar marca e tokens.
3. Manter metadados técnicos em inspeção; filtrar evidências por pilar/claim; evitar promessas de retorno e afirmações de aprovação não suportadas.
4. Validar desktop, mobile, impressão, estado antigo sem destaques e controles de evidência no navegador.

## 5. Integração e revisão

1. Rodar suíte completa, lint e validação documental; corrigir regressões, sem relaxar testes para aceitar fatos inventados.
2. Revisão independente primeiro dos critérios e depois da qualidade. Corrigir achados e rever.
3. Atualizar relatórios das fases 04 e 06, documentação de contratos e changelog com resultados reais e limites de homologação.
4. Preservar a análise histórica; testes operacionais não geram nova coleta paga sem necessidade. Não prometer aumento da nota de viabilidade.
