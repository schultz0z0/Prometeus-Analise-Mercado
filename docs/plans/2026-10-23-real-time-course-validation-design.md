# Desenho do fluxo real de validação de novos cursos

**Data:** 2026-10-23  
**Status:** aprovado  
**Produto:** Prometeus — Inteligência para Produtos Educacionais

## Objetivo

Substituir o fluxo demonstrativo de `validar novo curso` por uma auditoria real, executada em tempo real e baseada em evidências rastreáveis. A única fonte sintética permitida durante os testes é a base histórica passada da ENS, usada como benchmark institucional.

Nenhum dado de mercado, número, concorrente, anúncio, vaga, sinal social, score ou trecho do dossiê pode ser preenchido por fixture, fallback estático ou valor calibrado.

## Modos de inteligência

O fluxo suporta dois modos sem alterar suas garantias:

1. **LLM tradicional:** modo ativo para os testes atuais. A LLM realiza geração e julgamentos semânticos por contratos estruturados. Código convencional continua responsável por autorização de ferramentas, validação, fórmulas, score e mudanças de estado.
2. **Híbrido JEV + LLM:** habilitado quando `TYPESAFE_API_KEY` estiver configurada. O JEV assume os julgamentos atômicos Choice, Score e Noul; a LLM continua responsável por planejamento verbal e síntese.

JEV desativado não autoriza o uso de `FakeDecisionModel`, fixtures ou respostas fixas em runtime. O fallback permitido é somente do adaptador JEV para o adaptador de decisão baseado na LLM real.

## Arquitetura

O workflow será um orquestrador híbrido controlado por código. A LLM compreende o curso e propõe um plano de investigação; uma política determinística valida esse plano e executa apenas ferramentas registradas, com limites de custo e escopo. A LLM nunca chama fornecedores diretamente nem calcula o score.

O pipeline canônico possui as seguintes etapas:

1. carregar o snapshot do tenant e validar integrações;
2. normalizar proposta, ementa, anexos e contexto do usuário;
3. avaliar prontidão e solicitar dados faltantes quando necessário;
4. produzir um `CourseUnderstanding` estruturado;
5. gerar e classificar keywords, entidades, concorrentes, cargos e competências;
6. produzir um `ResearchPlan` com fontes, consultas, obrigatoriedade, orçamento e critérios de suficiência;
7. consultar a base histórica sintética da ENS e selecionar comparáveis;
8. executar as ferramentas externas reais planejadas;
9. sanitizar, deduplicar e persistir evidências com proveniência;
10. executar julgamentos semânticos via LLM tradicional ou JEV;
11. extrair features verificadas e calcular scores em código;
12. aplicar quality gates e definir a recomendação em código;
13. sintetizar o dossiê pela LLM usando somente fatos aprovados;
14. verificar claims, números e referências;
15. persistir o resultado e publicar progresso/webhook.

## Fontes e ferramentas

O catálogo inicial obrigatório inclui:

- pesquisa web no Google via Actor Apify;
- páginas e ofertas de concorrentes via crawler/Google Search Apify;
- Meta Ads Library via Actor Apify avaliado e configurado;
- LinkedIn para presença, posicionamento e sinais públicos permitidos;
- LinkedIn Jobs e/ou Google Jobs via Actor Apify;
- Instagram, TikTok, YouTube, Reddit e outras redes sociais quando o plano justificar;
- Google Trends, Google Analytics ou fontes adicionais via Apify quando aplicáveis e autorizadas;
- base histórica sintética ENS para comparabilidade passada.

Actors não ficam embutidos no código. IDs, versões, schema esperado, custo máximo e limites são configuração de deployment. Antes da execução, cada Actor passa por validação de configuração e schema.

O plano pode acrescentar ferramentas registradas quando o contexto do curso exigir. Ferramentas desconhecidas, não configuradas ou fora do orçamento são recusadas pelo orquestrador.

## Evidência e proveniência

Cada execução externa registra, no mínimo:

- ferramenta, fornecedor, Actor e versão;
- run ID e dataset ID;
- consulta normalizada e parâmetros relevantes;
- URL ou identificador público;
- horário de início e conclusão;
- quantidade bruta, válida e deduplicada;
- custo real ou estimado;
- hash do conteúdo;
- período, região e idioma;
- limitações, qualidade e status da coleta.

Uma fonte vazia é um resultado observável, não evidência negativa. Números só entram no score e no dossiê após normalização e validação do contrato.

## Política de falhas

Não existe fallback com dados fictícios.

- Falha de uma fonte marcada como obrigatória leva a análise para `BLOCKED` e preserva o checkpoint para retomada.
- Falha de fonte complementar produz plano parcial e impede recomendação positiva quando a cobertura mínima não for atingida.
- Evidência insuficiente resulta em `INSUFFICIENT_EVIDENCE` ou `REQUIRES_HUMAN_REVIEW`, conforme quality gate.
- Falha da LLM impede síntese e deixa a análise bloqueada; não gera texto determinístico fingindo ter sido produzido pelo modelo.
- Credencial ausente, Actor inválido, falta de egress ou schema drift aparecem explicitamente no progresso e na auditoria.

## Scoring e dossiê

O `ScoringService` existente será usado com features derivadas das evidências persistidas. Valores fixos no worker serão removidos. Cálculos financeiros e de viabilidade permanecem em código e usam parâmetros explícitos; a LLM pode sugerir hipóteses, mas não executa fórmulas.

O `DossierSynthesisService` recebe somente `DossierFacts` aprovados. Toda claim quantitativa deve referenciar `evidence_ids`, e o `DossierVerifier` rejeita números não encontrados nas evidências citadas. O dossiê mostra também fontes ausentes, limitações, contraprovas e cobertura.

## Experiência e observabilidade

A interface exibirá as quinze etapas reais, incluindo plano de pesquisa, fonte em execução, consultas, run IDs, itens encontrados, custo e falhas. O painel não poderá inicializar uma análise nova com o dossiê demonstrativo nem reutilizar `DETAILED_DOSSIER` como resultado real.

Logs e eventos terão `analysis_id`, `step`, `tool`, `source`, `run_id`, duração, custo e resultado, sem segredos. O health check do worker verificará fila e capacidade de egress necessária.

## Testes e aceite

A implementação seguirá TDD e incluirá:

- testes unitários das políticas, contratos e extração de features;
- testes contratuais de cada Actor com respostas gravadas de schema real, sem usar os dados como runtime;
- testes de integração do modo LLM tradicional e do modo híbrido;
- testes de falha para credencial, egress, timeout, Actor inválido, dataset vazio e schema drift;
- teste E2E em Docker que cria uma proposta, observa ferramentas externas reais e valida o dossiê produzido;
- teste de regressão que falha se qualquer número estático conhecido (`86.4`, `1420`, `+88%` etc.) voltar ao worker;
- verificação de que apenas a base histórica ENS é marcada como sintética.

O aceite exige uma execução nova em Docker na qual todas as claims de mercado possam ser rastreadas até runs e datasets reais, e na qual uma fonte obrigatória indisponível bloqueie a análise em vez de produzir o parecer.
