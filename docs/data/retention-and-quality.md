# Retenção e qualidade de dados

## Classes

- Configuração e auditoria.
- Propostas e documentos.
- Métricas agregadas de CRM.
- Evidências públicas.
- Conteúdo de redes sociais.
- Outputs de modelos.
- Logs e telemetria.

## Princípios

- Minimização por padrão.
- Preferência por agregados de CRM, sem PII de aluno.
- Retenção configurável por instituição e categoria.
- Exclusão auditável e backup com expiração compatível.
- Dados sintéticos em testes e desenvolvimento.

## Qualidade

Cada dataset registra schema, origem, cobertura, duplicatas, nulos, outliers, frescor e regras de reconciliação. Falhas de qualidade impedem que o pilar conte para cobertura quando excedem limites configurados.

## Valores a decidir com a ENS

- janelas de retenção;
- campos permitidos por API;
- responsável pelo tratamento;
- processo de atendimento a titulares;
- necessidade de anonimização adicional;
- classificação de documentos acadêmicos.
