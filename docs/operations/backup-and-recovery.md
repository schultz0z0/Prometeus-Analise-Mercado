# Backup e recuperação

## Escopo

- PostgreSQL;
- configurações versionadas;
- evidence storage quando a retenção permitir;
- chaves de referência para segredos, nunca os segredos em texto aberto.

## Política inicial

- Backup diário criptografado para local externo à VPS.
- Retenção diária/semanal/mensal a definir com a ENS.
- Restore trimestral no piloto e após mudanças críticas.
- Registro de duração, integridade e responsável.

## Recuperação

1. Isolar causa do incidente.
2. Provisionar stack limpa.
3. Restaurar banco e evidências compatíveis.
4. Validar migrações e checksums.
5. Reconciliar jobs em execução.
6. Rotacionar credenciais se necessário.
7. Registrar incidente e lições.
