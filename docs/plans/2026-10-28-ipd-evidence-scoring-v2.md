# Plano de implementação — IPD, evidências e scoring v2

**Objetivo:** corrigir perda indevida de evidências e implementar histórico por até três comparáveis, preços internos/externos e apresentação de scores com cobertura separada.

**Arquitetura:** preservar análises concluídas; novas análises usam perfil versionado `portfolio-v2`. Código valida geografia, IDs, comparabilidade, cálculos e estados. LLM/JEV qualificam sinais com finalidade por dimensão e conservam confiança/revisão. Documentos coletados são dados não confiáveis.

**Stack:** Python/FastAPI/SQLAlchemy/Alembic, PostgreSQL, JavaScript, pytest/Node, Docker Compose.

## 1. Evidências e contratos por fonte

- Regressões antes das correções para descrição Brasil, IDs públicos versus PII, deduplicação por marcador, séries Trends com termos separados e empregador próprio.
- Normalizar região/idioma em contrato reutilizável; preservar IDs técnicos tipados, redigir PII textual; chave de entidade ignora marcadores.
- Classificação com uso por finalidade: cargos/competências não precisam comprovar intenção de comprar um MBA; contexto de setor pode alimentar narrativa, sem inflar procura. Motivos explícitos e auditáveis.
- Atualizar catálogo/prompt/skills de pesquisa e rubricas com exemplos positivos/negativos por fonte, amostragem vinculada ao dado e recuperação orientada a lacunas.

## 2. Histórico institucional

- Ampliar contrato histórico com grade estruturada/texto e metadados de família, preservando defaults compatíveis; migração aditiva.
- Implementar percentis com empates por posto médio e normalização 0–100 na família; coorte menor que três cursos sinaliza insuficiência, sem fabricar ranking.
- Selecionar até três comparáveis por tema e grade quando disponível. Ausência de grade aparece como limitação; não afirmar comparação curricular. Agregar IPD dos selecionados, preservando IDs e motivos, nunca misturar famílias.
- Fórmula IPD 20% leads + 30% inscrições + 50% matrículas; qualidade e quantidade de coorte limitam confiança. Sem apoio suficiente, pilar ausente.

## 3. Preços de ofertas e contexto institucional

- Extrair condições por oferta (valor, parcelas, total, moeda, taxas/condições, tema, categoria, origem); não selecionar primeiro valor de página com vários cursos, notícia antiga ou taxa de matrícula.
- Média única por curso comparável com preços totais verificáveis internos e externos. Deduplicar cursos/condições, excluir própria instituição do conjunto externo, informar contagens e lacunas por origem.
- Metadados declarados da oferta e identidade do tenant são fatos separados da ementa, sem corte que omita preço/modalidade ou invente dúvidas.

## 4. Scoring e publicação

- Perfil novo preserva pesos como hipótese: interno 20%, externo 55%, aderência 15%, preço misto 10%. Cada sinal entra uma vez.
- Respeitar confiança real e revisão dos julgamentos; aderência exige necessidades/competências verificadas, não apenas ofertas similares.
- Separar contribuição ponderada, score observado normalizado, cobertura e confiança. Gates mantêm insuficiência de evidência; ausência não vira nota zero visível.
- API e dashboard mostram blocos, comparáveis, referência de preço e funil de evidências por fonte com motivos de exclusão.

## 5. Verificação e atualização

- Executar regressões e suíte completa, mypy, lint, validação de docs e revisão independente. Conferir interface com fixtures isoladas, sem publicar dados fictícios na base real.
- Documentar implementação, limitações de dados históricos e changelog. Build e atualização de API/worker somente sem tarefas ativas. Não iniciar análises pagas nem recalcular o dossiê homologado; homologação manual é do usuário.
