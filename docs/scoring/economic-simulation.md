# Simulação econômica e apresentação factual

## Contrato da apresentação — 04/11/2026

As novas apresentações usam `presentation.contract_version = 2`. A síntese, claims, highlights e blocos referenciados permanecem sujeitos às revisões factual e semântica do contrato do dossiê. O projetor visual não acrescenta personas, currículo, SWOT, benchmarks, prazos de reação da concorrência ou planos de lançamento genéricos. Esses conteúdos só podem vir dos contratos de redação verificados e seus vínculos de evidência.

A interface usa o scoring canônico para indicadores e veredito, sem comparações de benchmark fixas. Blocos visuais legados sem a versão 2 não são renderizados como informação verificada; síntese, evidências e resultados históricos permanecem preservados. Não há recálculo automático das análises anteriores.

Na homologação real, o contrato factual evoluiu para `citable_contract_version=4`: a escala do índice integra metadata estruturada da fonte `scoring_result`. A verificação numérica reconhece o denominador apenas em construções restritas de escala, sem aceitá-lo como percentual ou volume de mercado. As revisões na interface são explicitamente automáticas; status/contagens ausentes não geram aprovação humana, números padrão ou conclusão de viabilidade.

## Entrada financeira explícita

O campo `proposal_data.economics` aceita as premissas de `CourseEconomicsInput`: preço total, parcelas, desconto, inadimplência/estornos, tributos, custos de docência/coordenação, custo variável por aluno, campanha de marketing, CAC, quórum/capacidade e prazos acadêmico/financeiro. Todos os campos devem ser informados explicitamente para gerar a simulação. Valores zero são premissas possíveis onde o contrato permite; ausência não equivale a zero.

As chaves planas canônicas também são aceitas. Para compatibilidade, `fixed_costs`, `variable_cost_per_student` e `installments_count` são mapeados aos campos correspondentes. `ticket` só fornece preço total quando `price_period=total`, ou quando `price_period=monthly` e há número inteiro válido de parcelas. Referência de preço do mercado e duração acadêmica não completam preço ou parcelas da proposta.

Cada entrada guarda sua origem em `input_sources`. Premissas ausentes ou inválidas geram `status=not_calculable`, lista de pendências e nenhum cenário ou equilíbrio. Não são usados defaults implícitos de custo, capacidade, tributos ou inadimplência na apresentação.

## Cálculo e limites

`CourseEconomicsService` é o único motor de cálculo financeiro. Usa Decimal, deduz desconto/inadimplência/tributos, aplica CAC variável somente quando não há campanha fixa e limita os cenários à capacidade. O quórum mínimo não pode superar a capacidade máxima. Contribuição não positiva implica equilíbrio inexistente; equilíbrio acima da capacidade permanece explicitamente incompatível.

Os cenários são hipóteses de ocupação e sensibilidade, não previsões de matrículas. O conservador usa o quórum mínimo e desconto adicional de cinco pontos; o base usa o maior entre o quórum e 65% da capacidade arredondado para baixo; o otimista usa a capacidade. Os ajustes de desconto e os números de alunos aparecem como premissas do cenário.

O fluxo mensal separa duração acadêmica e prazo financeiro. Rateios usam centavos e reconciliam o resíduo no último mês, sem pagamentos negativos ou diferença entre caixa acumulado e resultado da turma. Status e cores derivam do resultado e da compatibilidade, sem sinalizar prejuízo como positivo.

Valores monetários são normalizados uma vez para centavos com `ROUND_HALF_UP`, limitados a R$ 1 trilhão por campo; capacidade é limitada a 100 mil alunos para evitar entradas numericamente inviáveis. O fluxo mensal é um rateio gerencial, não um cronograma contratual de parcelas: `installments` informa a proposta comercial, enquanto `financial_duration_months` governa a distribuição hipotética dos recebimentos. O desconto conservador é limitado a 100%, inclusive no texto exibido.

O benchmark de ecossistema projeta somente registros e ausências no recorte; instituição configurada sem consulta fica `not_queried`. Ausência de oferta não se converte em vantagem ou pioneirismo. Diferenciais e conexões curriculares não validados são explicitamente pendentes; temas do radar são classificados como sugestões contextuais.

## Verificação

Regressões: `tests/unit/dossiers/test_verified_presentation.py`, persistência final em `tests/integration/dossiers/test_synthesize_dossier_integration.py` e renderização real do módulo JavaScript em `tests/operational/test_dossier_view_rendering.py`.

As correções não alteram a base histórica sintética ENS, fornecedores de IA ou o modo tradicional. Homologação manual e calibração comercial continuam etapas posteriores.
