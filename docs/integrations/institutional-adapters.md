# Adaptadores institucionais

## Metadados de IPD e preço

O contrato histórico suporta família, grade textual/módulos, status da oferta, completude do funil e periodicidade do ticket. A migração `0010_historical_ipd_metadata` é aditiva; valores anteriores sem informação conservam status/unidade desconhecidos. Não se assume que um ticket é investimento total ou que uma oferta está encerrada. A [base sintética de homologação](ens-synthetic-test-data.md) pode ser ampliada com autorização explícita, mantendo cenários variados e identificação de teste; seus valores não são ajustados para obter aprovação de uma proposta.

O IPD usa somente cursos da instituição/família e observações encerradas completas na mesma janela. Ausência desses metadados, menos de três cursos de referência ou grades faltantes aparece como limitação. A seleção é de até três comparáveis; não força a existência de três. Preços internos entram no benchmark somente quando o total é explícito e a categoria/tema são compatíveis.

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
