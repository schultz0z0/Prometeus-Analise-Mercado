# Adaptadores institucionais

## Objetivo

Traduzir qualquer CRM autorizado para contratos canônicos sem contaminar o core com campos específicos.

## Portas

- `list_courses(filters)`
- `get_course(course_id)`
- `get_funnel_metrics(course_ids, period)`
- `get_financial_metrics(course_ids, period)` opcional
- `get_outcomes(course_ids, period)` opcional
- `healthcheck()`

## Primeiro adaptador: ENS

A ENS possui APIs de leads, inscritos e matriculados. Na Fase 00 serão coletados OpenAPI, autenticação, paginação, limites, campos, exemplos sanitizados e responsáveis.

Nenhum endpoint real ou segredo será documentado no repositório público. Mapeamentos ficam em configuração do deployment.

## Mock

O adaptador mock usa fixtures sintéticas, suporta cenários de erro e é o padrão local.

## Certificação de adaptador

Um adaptador somente é liberado após testes contratuais, reconciliação com amostra oficial, teste de paginação, timeout, retry, rate limit e validação de ausência de PII desnecessária.
