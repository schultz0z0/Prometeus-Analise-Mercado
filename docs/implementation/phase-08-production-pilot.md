# Fase 08 — Produção e piloto ENS

## Objetivo

Operar com segurança em shadow mode e depois em piloto controlado.

## Arquivos principais previstos

- `compose.yaml`
- `deploy/docker/`
- `docs/operations/runbooks.md`
- configuração privada do deployment ENS
- dashboards e alertas de observabilidade

## Tarefas

1. Endurecer imagens, usuários, rede e volumes.
2. Configurar TLS, firewall, secrets e rotação.
3. Configurar backup externo e executar restore.
4. Aplicar migrations em staging e ensaiar rollback.
5. Executar teste de carga coerente com o volume esperado.
6. Simular falhas de JEV, CRM, Apify, LLM e webhook.
7. Revisar threat model, LGPD e retenção.
8. Treinar operadores e responsáveis de negócio.
9. Rodar shadow mode e registrar divergências.
10. Liberar piloto para grupo restrito com kill switch.

## Verificação

```bash
docker compose config --quiet
pytest tests/e2e tests/operational -q
```

## Gate

Assinatura conjunta de produto, engenharia e ENS após evidências de restore, segurança, shadow mode e runbooks.
