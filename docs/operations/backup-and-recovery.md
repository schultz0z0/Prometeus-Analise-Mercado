# Backup e Recuperação

Este documento estabelece a política operacional, metas de recuperação (RPO/RTO) e procedimentos auditáveis para a infraestrutura do **Prometeus**.

---

## 1. Escopo de Proteção

- **PostgreSQL 16**: Tabelas de análises (`analyses`), etapas (`analysis_steps`), auditoria imutável (`audit_events`), snapshots de configuração (`config_snapshots`), dados históricos ENS (`historical_courses`, `historical_funnel_records`), dossiês compilados (`dossiers`), decisões humanas (`human_decisions`), desfechos reais de mercado (`course_outcomes`) e histórico de webhooks (`webhook_deliveries`).
- **Arquivos de Configuração**: Perfis de scoring (`config/scoring/`) e configurações de tenant (`config/tenants/`).
- **Segredos e Credenciais**: Armazenados exclusivamente em variáveis de ambiente seguras / secret manager da infraestrutura, **nunca incluídos nos dumps de dados**.

---

## 2. Objetivos de Recuperação (SLA)

| Parâmetro | Meta Homologação | Meta Produção Piloto ENS |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | 24 horas | 24 horas (diário automatizado) |
| **RTO (Recovery Time Objective)** | 2 horas | 30 minutos |
| **Integridade dos Dados** | SHA-256 verificado | SHA-256 verificado com manifesto assinado |
| **Ensaio de Restauração** | Por sprint | Trimestral e pré-release |

---

## 3. Rotina de Backup Automatizado

No `compose.yaml`, o serviço dedicado `backup` executa snapshot diário no PostgreSQL:
```bash
pg_dump -U prometeus -h postgres -d prometeus -F c -b -v -f /backups/prometeus_$(date +%Y%m%d_%H%M%S).dump
```

Adicionalmente, o utilitário Python determinístico [`scripts/backup_restore.py`](../../scripts/backup_restore.py) gera manifestos de integridade SHA-256 com validação de contagem de registros por tabela:
```bash
python scripts/backup_restore.py backup --output var/backups/prometeus_backup.json
```

---

## 4. Procedimento de Restauração e Validação de Integridade

1. **Validação de Checksum**:
   ```bash
   python scripts/backup_restore.py verify --file var/backups/prometeus_backup.json
   ```
   *Se o arquivo apresentar qualquer discrepância de bytes ou adulteração maliciosa, a operação é rejeitada com código de erro imediatamente.*

2. **Restauração Transacional Atômica**:
   ```bash
   python scripts/backup_restore.py restore --file var/backups/prometeus_backup.json --clean
   ```
   *A carga é executada dentro de uma única transação atômica em ordem estrita de chaves estrangeiras. Havendo qualquer falha, o rollback é instantâneo.*

3. **Verificação Automatizada**:
   ```bash
   pytest tests/operational/test_backup_restore.py -v
   ```
