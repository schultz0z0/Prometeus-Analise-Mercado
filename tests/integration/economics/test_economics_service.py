"""Testes de integração para o serviço de avaliação econômico-financeira de cursos (Tarefa 4.2).

Valida:
- Margem de contribuição, break-even por turma e compatibilidade com a capacidade máxima.
- Inviabilidade por capacidade (break-even > capacidade máxima) é resultado válido, não erro.
- Inviabilidade por margem negativa é tratada determininisticamente.
- Não duplicação de CAC quando campanha de marketing fixa é informada.
- Cenários conservador, base e otimista com premissas explícitas.
- Tratamento estrito de dados ausentes com status='not_calculable'.
"""

from __future__ import annotations

from decimal import Decimal

from prometeus.application.economics_service import CourseEconomicsService
from prometeus.domain.economics import CourseEconomicsInput


def test_viable_course_economics_evaluation():
    service = CourseEconomicsService()
    inp = CourseEconomicsInput(
        total_price_brl=Decimal("15000.00"),
        installments=12,
        discount_rate_pct=Decimal("10.0"),  # 10%
        default_and_refund_rate_pct=Decimal("5.0"),  # 5%
        tax_rate_pct=Decimal("15.0"),  # 15%
        instruction_and_coordination_cost_brl=Decimal("80000.00"),
        variable_cost_per_student_brl=Decimal("500.00"),
        marketing_campaign_cost_brl=Decimal("20000.00"),
        cac_per_enrolled_brl=Decimal("800.00"),  # Não deve ser duplicado com marketing fixo!
        min_capacity=15,
        max_capacity=40,
        academic_duration_months=12,
        financial_duration_months=12,
    )

    eval_res = service.evaluate(inp)

    assert eval_res.status == "calculable"
    assert eval_res.is_margin_positive is True
    assert eval_res.net_revenue_per_student_brl is not None
    # Gross = 15000 * 0.90 = 13500. Net = 13500 * 0.95 * 0.85 = 10901.25
    assert eval_res.net_revenue_per_student_brl == Decimal("10901.25")

    # Fixed costs: 80000 + 20000 = 100000.00
    assert eval_res.total_fixed_costs_cohort_brl == Decimal("100000.00")

    # Variable costs per student: 500.00 (CAC not duplicated because marketing campaign exists)
    # Contribution Margin = 10901.25 - 500.00 = 10401.25
    assert eval_res.contribution_margin_per_student_brl == Decimal("10401.25")

    # Break-even = ceil(100000.00 / 10401.25) = 10 students
    assert eval_res.break_even_students == 10
    assert eval_res.is_break_even_compatible_with_capacity is True
    assert eval_res.break_even_students <= inp.max_capacity

    # Scenarios generated
    assert "conservative" in eval_res.scenarios
    assert "base" in eval_res.scenarios
    assert "optimistic" in eval_res.scenarios
    assert eval_res.scenarios["base"].break_even_achieved is True

    # Monthly cash flow generated for 12 months
    assert len(eval_res.monthly_cash_flow) == 12


def test_inviable_course_due_to_capacity_constraint():
    service = CourseEconomicsService()
    # High fixed costs (R$ 350.000) and low ticket (R$ 4.000) with capacity capped at 30
    inp = CourseEconomicsInput(
        total_price_brl=Decimal("4000.00"),
        installments=6,
        discount_rate_pct=Decimal("0.0"),
        default_and_refund_rate_pct=Decimal("5.0"),
        tax_rate_pct=Decimal("15.0"),
        instruction_and_coordination_cost_brl=Decimal("300000.00"),
        variable_cost_per_student_brl=Decimal("300.00"),
        marketing_campaign_cost_brl=Decimal("50000.00"),
        min_capacity=10,
        max_capacity=30,  # Turma pequena
        academic_duration_months=6,
        financial_duration_months=6,
    )

    eval_res = service.evaluate(inp)

    assert eval_res.status == "calculable"
    assert eval_res.is_margin_positive is True
    # Break-even will require > 100 students, far exceeding max_capacity (30)
    assert eval_res.break_even_students is not None
    assert eval_res.break_even_students > inp.max_capacity
    assert eval_res.is_break_even_compatible_with_capacity is False


def test_inviable_course_due_to_negative_contribution_margin():
    service = CourseEconomicsService()
    # Variable cost per student (R$ 5.000) exceeds Net price (R$ 3.230)
    inp = CourseEconomicsInput(
        total_price_brl=Decimal("4000.00"),
        discount_rate_pct=Decimal("0.0"),
        default_and_refund_rate_pct=Decimal("5.0"),
        tax_rate_pct=Decimal("15.0"),
        instruction_and_coordination_cost_brl=Decimal("50000.00"),
        variable_cost_per_student_brl=Decimal("5000.00"),  # Maior que a receita líquida!
        marketing_campaign_cost_brl=Decimal("10000.00"),
        min_capacity=10,
        max_capacity=40,
    )

    eval_res = service.evaluate(inp)

    assert eval_res.status == "calculable"
    assert eval_res.is_margin_positive is False
    assert eval_res.break_even_students is None
    assert eval_res.is_break_even_compatible_with_capacity is False


def test_missing_mandatory_inputs_returns_not_calculable():
    service = CourseEconomicsService()
    inp = CourseEconomicsInput(
        total_price_brl=Decimal("0.00"),  # Preço ausente / zero
        instruction_and_coordination_cost_brl=Decimal("0.00"),  # Custo docente ausente
    )

    eval_res = service.evaluate(inp)

    assert eval_res.status == "not_calculable"
    assert "total_price_brl" in eval_res.missing_inputs
    assert "instruction_and_coordination_cost_brl" in eval_res.missing_inputs
    assert eval_res.break_even_students is None
