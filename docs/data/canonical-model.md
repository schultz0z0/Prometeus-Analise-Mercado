# Modelo canônico de dados

## Histórico e auditoria portfolio-v2

`HistoricalCourse` inclui `family`, `curriculum_text` e `curriculum_modules`. `HistoricalFunnel` inclui `price_period`, `data_complete` e `cohort_status`. Valores desconhecidos são preservados; a migração não infere grade, fechamento nem unidade de ticket.

O checkpoint histórico registra família, janela, tamanho da referência, até três comparáveis, motivos, percentis, IPD, IDs e limitações. A preparação registra referência de preço por curso/origem e motivos de exclusão comercial. `Dossier.presentation.analysis_audit` congela esses dados, perdas por fonte e falhas de consulta. `ScoringResult.gate_details` mantém contribuição ponderada, score observado, blocos e perfil. As adições são opcionais na leitura de dossiês antigos.

## Entidades principais

### InstitutionConfig

Identidade, locale, moeda, timezone, modalidades, fontes, políticas, branding, scoring profile e adaptador institucional.

### CourseProposal

Título, descrição, objetivo, público, modalidade, duração, carga horária, formato, região, preço pretendido, competências, ementa, pré-requisitos e metadados de origem.

`price_period` declara `monthly` ou `total`; a ausência é `unknown`, sem comparação silenciosa. O formulário de mensalidade envia `monthly`. O entendimento preserva essa declaração em `proposed_price_period`; a LLM não define a unidade do preço informado pela instituição.

### HistoricalCourse

Identificador externo, taxonomia, datas, oferta, ticket, investimento, leads, inscritos, matriculados, cancelamentos, evasão, receita e qualidade do registro.

### Analysis

ID, proposta versionada, `status` (ciclo de vida), `recommendation` (nula até `COMPLETED`), etapas, configuração congelada, idempotency key, timestamps, custos e vínculo opcional `previous_analysis_id`. Ver [ADR-0005](../architecture/adr/0005-status-vs-recommendation.md).

### AnalysisStep

Etapa do workflow (01–15), estado, tentativas, checkpoint, idempotency key do step, duração, custo e erro normalizado.

### ConfigSnapshot

Cópia imutável e hash de configuração institucional, scoring profile, decision packs, prompts e skills usados pela análise.

### AuditEvent

Ator (serviço ou usuário), ação, entidade, estado anterior e novo, motivo, `correlation_id` e timestamp. Append-only.

### KeywordSet

Candidatos gerados pela LLM, decisões de relevância do JEV e conjunto final selecionado por regra em código.

### EvidenceItem

Fonte, tipo, URL ou ID externo, instante de coleta, período observado, conteúdo normalizado, hash, qualidade, limitações, licença/termos e classificação de sensibilidade.

O conteúdo bruto e seu hash permanecem como origem. `sanitized_data._qualification` guarda o julgamento de pertinência, confiança, motivo, pack, decisão e hash do entendimento; esse campo é sobrescrito por código a partir de um resultado persistido e não é aceito como autorização vinda do scraper. `context_only` preserva contexto setorial para a redação sem contar notícia, legislação ou empregador como concorrente educacional.

As agregações deduplicam ofertas por URL canônica e vagas/anúncios/comentários por identidade quando disponível, conservando os IDs das capturas que sustentam o dado. Queries diferentes podem manter evidências separadas para proveniência sem aumentar a contagem da entidade. Em `tool_runs.parameters`, `observation_status` distingue coleta observada, consulta vazia e itens rejeitados; estes últimos ficam em auditoria limitada, sem criar evidência útil falsa. `raw_items_count` conta o lote recebido, enquanto `dataset_total_items` conserva o total informado pelo fornecedor.

### DecisionResult

Decision pack, modelo, estado normalizado, resposta, distribuição, confidence, regra de aceite e evidências relacionadas.

### ScoreSnapshot

Perfil de scoring, features, sub-scores, cobertura, confiança, score e status.

### Dossier

Fatos estruturados, claims narrativas, referências, recomendações, limitações e versão do gerador.

O contrato de apresentação v2 é persistido em `dossiers.presentation`: `schema_version`, `executive_summary_claim_ids`, `highlights`, `limitations` e `counterevidence`. A migração aditiva usa `{}` para análises anteriores. As duas respostas REST que entregam dossiês expõem a apresentação com defaults compatíveis.

`highlights.pros/cons` referenciam claims. Critérios possuem texto, alvo, claims e estado exclusivamente `pending`; ações possuem área, prioridade, claims e estado exclusivamente `proposed`. Comparações de concorrentes e relações ementa/necessidade também referenciam claims. Nenhum campo concede aprovação institucional. A API mantém metadados técnicos para auditoria; a interface os concentra no inspetor.

### Claim

Texto, tipo, `evidence_ids`, nível de suporte (`observed`, `suggestive`, `hypothesis`), escopo e resultado da verificação.

### WebhookDelivery

`event_id`, tipo, destino, tentativas, status de entrega, último erro e envio para dead-letter.

### HumanDecision

Usuário, papel, decisão, justificativa, ajustes, timestamp e análise de origem.

### Outcome

Métricas reais pós-lançamento, janela, fonte e data de fechamento.

## Identificadores

IDs internos são UUID/ULID. IDs externos ficam em namespace do adaptador e nunca substituem a chave interna.
