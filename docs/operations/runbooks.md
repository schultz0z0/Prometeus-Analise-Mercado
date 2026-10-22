# Runbooks Operacionais Prometeus

Este guia detalha procedimentos padronizados para operadores, engenheiros de confiabilidade (SRE) e equipes de suporte durante a operação do monólito Prometeus em ambiente de homologação e produção piloto com a ENS.

---

## 1. Ativação Imediata do Kill Switch (Contenção Operacional)

### Cenário de Aplicação
- Identificação de anomalia crítica de segurança, vazamento de credenciais, corrupção de dados ou inconsistência sistêmica na síntese de mercado.
- Necessidade de interromper novas submissões sem desligar a API para consultas e auditoria.

### Procedimento
1. Alterar a variável de ambiente no container ou secret manager:
   ```bash
   KILL_SWITCH_ACTIVE=true
   ```
2. Aplicar configuração a quente via Docker Compose:
   ```bash
   docker compose up -d api worker
   ```
3. Comportamento esperado:
   - Requisições para `POST /v1/analyses` e `POST /v1/analyses/{id}/reanalyze` retornam `HTTP 503 Service Unavailable` com corpo RFC 7807 explicativo.
   - Endpoints de leitura (`GET /v1/analyses/{id}`, `GET /v1/analyses/{id}/status`, `GET /health/live`) permanecem 100% funcionais para suporte e auditoria.
4. Para restabelecer operação normal:
   ```bash
   KILL_SWITCH_ACTIVE=false
   docker compose up -d api worker
   ```

---

## 2. Operação em Shadow Mode (Validação Sem Efeitos Colaterais)

### Cenário de Aplicação
- Validação do piloto em produção com dados reais da ENS sem disparar webhooks ou alterar estados em sistemas legados do cliente.

### Procedimento
1. Configurar variável de ambiente no deployment:
   ```bash
   SHADOW_MODE=true
   ```
2. Comportamento do sistema:
   - Propostas de análise recebem a flag interna `_shadow_mode=true` persistida nos metadados.
   - O `WebhookDispatcher` intercepta todos os envios: registra o evento com status `SHADOW_DELIVERED`, resposta HTTP 200 simulada e log estruturado, **sem abrir socket externo de rede para o endpoint do cliente**.
   - Toda a esteira determinística de scoring, dossiê e auditoria executa normalmente para fins de calibração e benchmarking.

---

## 3. Rollback de Migrações de Banco de Dados (Alembic)

### Cenário de Aplicação
- Falha na aplicação de schema ou necessidade de reversão após ensaio de staging.

### Procedimento
1. Verificar a revisão atual da base:
   ```bash
   alembic current
   ```
2. Reverter exatamente uma revisão:
   ```bash
   alembic downgrade -1
   ```
3. Ou reverter para uma revisão específica aprovada:
   ```bash
   alembic downgrade <revision_id>
   ```
4. Validar integridade e ausência de bloqueios relacionais via `pytest tests/operational/test_backup_restore.py`.

---

## 4. Procedimento de Disaster Recovery (Backup e Restore)

### Ferramenta Padrão
O utilitário oficial [`scripts/backup_restore.py`](../../scripts/backup_restore.py) garante atomicidade transacional e verificação estrita de integridade via checksum SHA-256.

### Criar Snapshot Manual
```bash
python scripts/backup_restore.py backup --output var/backups/prometeus_$(date +%Y%m%d_%H%M%S).json
```

### Validar Autenticidade e Integridade de um Backup
```bash
python scripts/backup_restore.py verify --file var/backups/prometeus_backup.json
```
*Gera código de saída 0 se o hash SHA-256 conferir perfeitamente com o manifesto assinado, ou código 1 com alerta de corrupção/adulteração.*

### Restaurar Banco em Ambiente Limpo
```bash
python scripts/backup_restore.py restore --file var/backups/prometeus_backup.json --clean
```
*Restaura todas as tabelas em ordem estrita de integridade referencial dentro de uma única transação atômica. Se qualquer tabela falhar, executa rollback automático sem deixar a base em estado inconsistente.*

---

## 5. Rotação de Segredos e Credenciais

### Escopo
- `TYPESAFE_API_KEY` (JEV)
- Chaves de API de LLM (Gemini, Claude, OpenAI)
- Chaves de conectores externos (Apify, Google Ads, YouTube)
- Segredos HMAC de Webhooks (`WEBHOOK_SECRET`)

### Procedimento
1. Nunca gravar chaves em repositórios Git ou arquivos `.yaml` sob controle de versão.
2. Atualizar o arquivo `.env` seguro ou secret manager da infraestrutura VPS/Kubernetes.
3. Para rotação de Webhook Secret:
   - Configurar o novo segredo na infraestrutura.
   - O `WebhookDispatcher` passa a assinar com o novo secret. O webhook receiver do cliente valida contra a chave ativa.
4. Reiniciar serviços sem downtime:
   ```bash
   docker compose restart api worker
   ```

---

## 6. Tratamento de Indisponibilidade de Serviços Externos

### JEV Indisponível
- O circuit breaker abre após 3 timeouts consecutivos de 15 segundos.
- Análises em processamento que dependem de nova categorização transicionam para o estado `BLOCKED` com motivo registrado em auditoria.
- Não substitui nem degrada silenciosamente para versões não fixadas (`jev-latest` é estritamente proibido em produção conforme ADR-0003).

### Apify Indisponível ou Quota Excedida
- O conector de scraping registra falha da fonte externa.
- Se a cobertura do pilar atingir o mínimo acordado no perfil de scoring, a análise é concluída com flag de cobertura parcial; caso contrário, a análise é marcada como `BLOCKED` para reexecução após regularização da quota.

### CRM da Instituição (ENS) Indisponível
- Aplica retry com backoff exponencial (máximo de 3 tentativas).
- Nunca substitui dados históricos por zeros ou valores fictícios.
- Registra `CRM_UNAVAILABLE` no log de auditoria.

### Falhas Consecutivas de Webhook
- Após 5 tentativas sem sucesso (HTTP >= 400 ou falha de rede), a entrega é enviada para o estado `DEAD_LETTER`.
- O payload permanece persistido de forma imutável na tabela `webhook_deliveries` para reprocessamento manual ou consumo via polling por parte do chatbot.
