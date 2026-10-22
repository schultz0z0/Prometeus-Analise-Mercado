# Modelo canônico de dados

## Entidades principais

### InstitutionConfig

Identidade, locale, moeda, timezone, modalidades, fontes, políticas, branding, scoring profile e adaptador institucional.

### CourseProposal

Título, descrição, objetivo, público, modalidade, duração, carga horária, formato, região, preço pretendido, competências, ementa, pré-requisitos e metadados de origem.

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

### DecisionResult

Decision pack, modelo, estado normalizado, resposta, distribuição, confidence, regra de aceite e evidências relacionadas.

### ScoreSnapshot

Perfil de scoring, features, sub-scores, cobertura, confiança, score e status.

### Dossier

Fatos estruturados, claims narrativas, referências, recomendações, limitações e versão do gerador.

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
