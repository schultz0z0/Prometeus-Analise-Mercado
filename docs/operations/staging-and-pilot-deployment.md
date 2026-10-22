# Guia de Implantação em Staging e Operação do Piloto ENS

Este documento detalha o procedimento operacional completo para implantar o **Prometeus** em ambiente de homologação (staging) e conduzir com segurança a operação do piloto com a **Escola de Negócios e Seguros (ENS)**.

---

## 1. Visão Geral da Infraestrutura

A topologia do monólito Prometeus em staging e produção piloto é orientada a containers Docker com segregação de rede e persistência transacional em PostgreSQL:

```mermaid
graph TD
    User[Chatbot ENS / Comitê Acadêmico] -->|HTTPS :443| Nginx[Reverse Proxy TLS]
    Nginx -->|HTTP :8000| API[Container prometeus-api]
    API -->|Rede Interna| Postgres[(PostgreSQL 16)]
    API -->|Rede Interna| Redis[(Redis 7)]
    Worker[Container prometeus-worker] -->|Rede Interna| Postgres
    Worker -->|Rede Interna| Redis
    Worker -->|Egress Externo Controlado| External[JEV / Google Ads / Apify / LLM]
    Backup[Container prometeus-backup] -->|Snapshot Diário| Storage[(Volume Backups)]
```

### Componentes da Stack
- **API REST & Servidor MCP**: Imagem multi-stage Python 3.11 executada com usuário não-root `prometeus` (UID 10001).
- **Worker Assíncrono**: Celery worker executando a máquina de estados retomável do workflow de análise.
- **Banco de Dados**: PostgreSQL 16 com volume persistente e rede interna privada (`prometeus_internal`).
- **Fila e Cache**: Redis 7 para coordenação de tarefas Celery e limitação de taxa.
- **Backup Periódico**: Container acoplado executando dumps automatizados e verificação SHA-256.

---

## 2. Passo a Passo de Implantação em Staging

### Pré-requisitos
- Servidor VPS ou VM (Ubuntu 22.04 LTS / Debian 12 ou similar).
- Mínimo: 2 vCPUs, 4 GB de memória RAM, 40 GB de disco SSD.
- Docker Engine 24.0+ e Docker Compose V2 instalados.
- Domínio ou subdomínio apontado para o host (ex.: `staging-api.prometeus.agencia.com.br`).

### Passo 1: Obtenção do Código Fonte
```bash
git clone https://github.com/schultz0z0/Prometeus-Analise-Mercado.git /opt/prometeus
cd /opt/prometeus
git checkout main
```

### Passo 2: Configuração de Variáveis de Ambiente
Copiar o modelo e preencher as credenciais seguras no arquivo `/opt/prometeus/.env`:
```bash
cp .env.example .env
chmod 600 .env
```

Parâmetros essenciais para o staging:
```ini
APP_ENV=staging
LOG_LEVEL=INFO
PUBLIC_BASE_URL=https://staging-api.prometeus.agencia.com.br

# Banco e Cache
DATABASE_URL=postgresql+asyncpg://prometeus:SEU_PASSWORD_SEGURO@postgres:5432/prometeus
REDIS_URL=redis://redis:6379/0

# Configuração Institucional ENS
INSTITUTION_ID=ens
INSTITUTION_CONFIG_PATH=config/tenants/ens.example.yaml
SCORING_PROFILE_PATH=config/scoring/default-v1.example.yaml
JEV_MODEL=jev-v1.2.0

# Controles Operacionais do Piloto
SHADOW_MODE=true
KILL_SWITCH_ACTIVE=false

# Segredos de Conectores (armazenados exclusivamente no .env)
TYPESAFE_API_KEY=sua_chave_jev_aqui
APIFY_TOKEN=seu_token_apify_aqui
WEBHOOK_SECRET=seu_webhook_secret_hmac_aqui
```

### Passo 3: Inicialização dos Containers
```bash
docker compose up -d --build
```

O container `prometeus-api` executa o script `docker-entrypoint.sh`, que aplica automaticamente as migrações pendentes do Alembic (`alembic upgrade head`) antes de abrir a porta 8000.

### Passo 4: Verificação de Prontidão (Healthcheck)
Verificar status de liveness e readiness do banco e redis:
```bash
# Liveness
curl -f http://localhost:8000/health/live

# Readiness (PostgreSQL + Redis)
curl -f http://localhost:8000/health/ready
```
*Ambos devem responder com código HTTP 200 e payload indicando status `"ready"`.*

### Passo 5: Smoke Test Automatizado
Executar a suíte de testes de ponta a ponta e testes operacionais no ambiente:
```bash
docker compose exec api pytest tests/e2e/test_chatbot_flow.py tests/operational/ -v
```

---

## 3. Roteiro e Fases da Operação do Piloto ENS

O piloto é conduzido em duas etapas graduais para eliminar riscos à rotina acadêmica da ENS:

### Fase 1: Operação em Shadow Mode (Semanas 1 e 2)

- **Objetivo**: Avaliar a calibração do score e a factualidade do dossiê em propostas reais da ENS sem gerar efeitos colaterais nos sistemas legados do cliente.
- **Configuração**:
  ```ini
  SHADOW_MODE=true
  KILL_SWITCH_ACTIVE=false
  ```
- **Comportamento**:
  - O chatbot ou coordenador acadêmico submete propostas reais de cursos pelo endpoint `POST /v1/analyses`.
  - A esteira completa executa: histórico interno ENS $\rightarrow$ JEV $\rightarrow$ concorrência e buscas $\rightarrow$ scoring determinístico $\rightarrow$ síntese factual auditada.
  - O [`WebhookDispatcher`](../../src/prometeus/infrastructure/webhooks/dispatcher.py) intercepta a notificação e registra `SHADOW_DELIVERED`, **sem disparar requisição externa para o CRM da ENS**.
- **Atividades de Avaliação**:
  - Exportar os dossiês gerados via `GET /v1/analyses/{id}/dossier`.
  - Apresentar semanalmente à coordenação da ENS para comparar a recomendação algorítmica (`APPROVED`, `APPROVED_WITH_ADJUSTMENTS`, `REJECTED`) contra a decisão humana histórica.

### Fase 2: Piloto Ativo com Grupo Restrito (Semanas 3 a 6)

- **Objetivo**: Operação assistida com entrega real de pareceres e registro de decisões humanas.
- **Configuração**:
  ```ini
  SHADOW_MODE=false
  KILL_SWITCH_ACTIVE=false
  ```
- **Grupo de Usuários**: 5 a 10 coordenadores de cursos e analistas de novos negócios selecionados pela diretoria da ENS.
- **Fluxo Operacional**:
  1. Coordenador submete proposta via Chatbot integrado via MCP ou API REST.
  2. Recebe webhook assinado com HMAC-SHA256 assim que a análise é concluída.
  3. Coordenador lê o sumário executivo e o dossiê.
  4. Registra o parecer institucional formal via `POST /v1/analyses/{id}/decisions`.
  5. Caso o curso seja lançado, as matrículas e receita são registradas em `POST /v1/analyses/{id}/outcomes` para retroalimentação do modelo.

---

## 4. Critérios de Sucesso e Saída do Piloto

Para que o piloto seja considerado aprovado e apto para rollout amplo:

| Critério | Meta | Método de Medição |
| :--- | :--- | :--- |
| **Disponibilidade da API** | $\ge 99.5\%$ | Monitoramento de liveness e uptime |
| **Tempo de Resposta do Workflow** | p95 $< 180\text{ s}$ | Duração total registrada nos steps |
| **Factualidade dos Dossiês** | $100\%$ claims validadas | TOOL-15 Verifier sem alucinações |
| **Confiabilidade de Entrega Webhook** | $\ge 99.0\%$ | Taxa de entrega sem cair em dead-letter |
| **Aderência das Recomendações** | $\ge 80\%$ de concordância | Comparação das decisões humanas x score |

---

## 5. Rotinas Diárias do Operador (SRE / Suporte)

1. **Inspeção de Filas e Dead-Letters**:
   Consultar se há eventos retidos na fila morta de webhooks:
   ```bash
   docker compose exec postgres psql -U prometeus -d prometeus -c \
     "SELECT event_id, target_url, last_error, attempt_count FROM webhook_deliveries WHERE status = 'DEAD_LETTER';"
   ```
2. **Checagem de Análises Bloqueadas**:
   Identificar análises que entraram no estado `BLOCKED` por falha de conector externo:
   ```bash
   docker compose exec postgres psql -U prometeus -d prometeus -c \
     "SELECT id, course_name, status, updated_at FROM analyses WHERE status = 'BLOCKED';"
   ```
3. **Auditoria dos Backups Diários**:
   Validar que o backup foi gerado e está integro:
   ```bash
   python scripts/backup_restore.py verify --file var/backups/prometeus_backup.json
   ```

---

## 6. Procedimento de Emergência e Escalonamento

### Acionamento do Kill Switch
Caso seja detectada qualquer inconsistência crítica de dados ou vulnerabilidade:
1. Definir `KILL_SWITCH_ACTIVE=true` no arquivo `.env`.
2. Reiniciar o serviço:
   ```bash
   docker compose up -d api worker
   ```
3. Todas as submissões serão rejeitadas com `HTTP 503 Service Unavailable`, protegendo a base de dados. Consultas existentes continuam acessíveis.

### Matriz de Escalonamento
- **Incidente de Infraestrutura / Indisponibilidade**: Engenharia Agência Prometeus (SRE).
- **Divergência de Dados / Fórmulas Acadêmicas**: Coordenação de Negócios ENS.
- **Suspeita de Vazamento / Segurança da Informação**: DPO Prometeus e DPO ENS.
