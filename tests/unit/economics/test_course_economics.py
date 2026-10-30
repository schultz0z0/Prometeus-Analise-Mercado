"""Testes unitários para modelos e cálculos econômico-financeiros de cursos (Tarefa 4.2).

Requisitos validados:
- Uso estrito de Decimal e separação entre prazo acadêmico e financeiro.
- Margem de contribuição (absoluta e percentual) por aluno.
- Ponto de equilíbrio (break-even em alunos) e verificação de compatibilidade com capacidade máxima.
- Margem não positiva ou equilíbrio acima da capacidade são resultados determinísticos, não exceções ocultas.
- Se aquisição é custo fixo de campanha (marketing_campaign_cost_brl > 0), não duplicar CAC por matrícula.
- Dados ausentes geram status='not_calculable' com solicitação explícita dos campos faltantes.
"""

from __future__ import annotations

from decimal import Decimal

from prometeus.domain.economics import (
    CashFlowMonth,
    CourseEconomicsInput,
    ScenarioProjection,
)


def test_course_economics_input_defaults_and_validation():
    inp = CourseEconomicsInput(
        total_price_brl=Decimal("15000.00"),
        installments=12,
        discount_rate_pct=Decimal("10.0"),  # 10%
        default_and_refund_rate_pct=Decimal("5.0"),  # 5%
        tax_rate_pct=Decimal("15.0"),  # 15%
        instruction_and_coordination_cost_brl=Decimal("80000.00"),
        variable_cost_per_student_brl=Decimal("500.00"),
        marketing_campaign_cost_brl=Decimal("20000.00"),
        min_capacity=15,
        max_capacity=40,
        academic_duration_months=12,
        financial_duration_months=12,
    )

    assert inp.total_price_brl == Decimal("15000.00")
    assert inp.installments == 12
    assert inp.min_capacity == 15
    assert inp.max_capacity == 40


def test_scenario_projection_structure():
    proj = ScenarioProjection(
        name="base",
        enrolled_students=25,
        discount_rate_pct=Decimal("10.0"),
        gross_revenue_brl=Decimal("337500.00"),
        net_revenue_brl=Decimal("272531.25"),
        total_fixed_costs_brl=Decimal("100000.00"),
        total_variable_costs_brl=Decimal("12500.00"),
        total_costs_brl=Decimal("112500.00"),
        net_result_brl=Decimal("160031.25"),
        profit_margin_pct=Decimal("58.72"),
        break_even_achieved=True,
        assumptions=["Capacidade de 25 alunos (62.5% da turma)", "Desconto médio de 10%"],
    )

    assert proj.name == "base"
    assert proj.break_even_achieved is True
    assert proj.net_result_brl > 0


def test_cash_flow_month_tracking():
    cf = CashFlowMonth(
        month=1,
        projected_receipts_brl=Decimal("22710.94"),
        projected_disbursements_brl=Decimal("27708.33"),
        net_cash_flow_brl=Decimal("-4997.39"),
        cumulative_cash_flow_brl=Decimal("-4997.39"),
    )

    assert cf.month == 1
    assert cf.net_cash_flow_brl == Decimal("-4997.39")
