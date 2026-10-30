"""Serviço determinístico de avaliação econômico-financeira de cursos (Tarefa 4.2).

Implementa cálculos de margem de contribuição, break-even por capacidade,
cenários de sensibilidade e cronograma de fluxo de caixa mensal.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

from prometeus.domain.economics import (
    CashFlowMonth,
    CourseEconomicsEvaluation,
    CourseEconomicsInput,
    ScenarioProjection,
)


def _quantize(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CourseEconomicsService:
    """Motor determinístico de unit economics para turmas de cursos."""

    def evaluate(self, inputs: CourseEconomicsInput) -> CourseEconomicsEvaluation:
        # 1. Validação estrita de dados obrigatórios
        missing_inputs: list[str] = []
        if inputs.total_price_brl <= Decimal("0.00"):
            missing_inputs.append("total_price_brl")
        if inputs.instruction_and_coordination_cost_brl <= Decimal("0.00"):
            missing_inputs.append("instruction_and_coordination_cost_brl")

        if missing_inputs:
            return CourseEconomicsEvaluation(
                status="not_calculable",
                missing_inputs=missing_inputs,
                message=(
                    "Dados financeiros essenciais ausentes ou não calculáveis: "
                    f"{', '.join(missing_inputs)}. O score de preço não substitui o unit economics."
                ),
                inputs=inputs,
            )

        # 2. Receita líquida por aluno
        discount_factor = Decimal("1.0") - (inputs.discount_rate_pct / Decimal("100.0"))
        gross_per_student = _quantize(inputs.total_price_brl * discount_factor)
        default_factor = Decimal("1.0") - (inputs.default_and_refund_rate_pct / Decimal("100.0"))
        after_default = gross_per_student * default_factor
        tax_factor = Decimal("1.0") - (inputs.tax_rate_pct / Decimal("100.0"))
        net_revenue_per_student = _quantize(after_default * tax_factor)

        # 3. Custos fixos e custos variáveis
        total_fixed_costs = _quantize(
            inputs.instruction_and_coordination_cost_brl + inputs.marketing_campaign_cost_brl
        )
        # Regra de ouro: se há custo de campanha fixo, não duplicar com CAC por aluno
        effective_cac = (
            inputs.cac_per_enrolled_brl
            if inputs.marketing_campaign_cost_brl == Decimal("0.00")
            else Decimal("0.00")
        )
        variable_cost_per_student = _quantize(inputs.variable_cost_per_student_brl + effective_cac)

        # 4. Margem de contribuição por aluno
        contribution_margin_per_student = _quantize(net_revenue_per_student - variable_cost_per_student)
        cm_ratio_pct = (
            _quantize((contribution_margin_per_student / net_revenue_per_student) * Decimal("100.0"))
            if net_revenue_per_student > Decimal("0.00")
            else Decimal("0.00")
        )
        is_margin_positive = contribution_margin_per_student > Decimal("0.00")

        # 5. Ponto de Equilíbrio (Break-Even) e compatibilidade com capacidade
        if not is_margin_positive:
            break_even_students = None
            is_break_even_compatible = False
        else:
            be_calc = math.ceil(float(total_fixed_costs / contribution_margin_per_student))
            break_even_students = be_calc
            is_break_even_compatible = break_even_students <= inputs.max_capacity

        # 6. Projeção de Cenários (Conservador, Base, Otimista)
        scenarios: dict[str, ScenarioProjection] = {}

        scenario_configs = [
            (
                "conservative",
                inputs.min_capacity,
                min(Decimal("100.0"), inputs.discount_rate_pct + Decimal("5.0")),
                [
                    f"Quórum mínimo de {inputs.min_capacity} alunos",
                    f"Desconto aumentado para {inputs.discount_rate_pct + Decimal('5.0')}%",
                ],
            ),
            (
                "base",
                max(inputs.min_capacity, int(round(inputs.max_capacity * 0.65))),
                inputs.discount_rate_pct,
                [
                    f"Ocupação de {max(inputs.min_capacity, int(round(inputs.max_capacity * 0.65)))} alunos (65% da capacidade)",
                    f"Desconto padrão de {inputs.discount_rate_pct}%",
                ],
            ),
            (
                "optimistic",
                inputs.max_capacity,
                max(Decimal("0.0"), inputs.discount_rate_pct - Decimal("5.0")),
                [
                    f"Turma lotada com {inputs.max_capacity} alunos (100% da capacidade)",
                    f"Desconto reduzido para {max(Decimal('0.0'), inputs.discount_rate_pct - Decimal('5.0'))}%",
                ],
            ),
        ]

        for sc_name, students, discount, assumptions in scenario_configs:
            sc_gross_price = _quantize(inputs.total_price_brl * (Decimal("1.0") - (discount / Decimal("100.0"))))
            sc_net_price = _quantize(sc_gross_price * default_factor * tax_factor)
            sc_gross_rev = _quantize(sc_gross_price * Decimal(str(students)))
            sc_net_rev = _quantize(sc_net_price * Decimal(str(students)))
            sc_var_costs = _quantize(variable_cost_per_student * Decimal(str(students)))
            sc_tot_costs = _quantize(total_fixed_costs + sc_var_costs)
            sc_net_res = _quantize(sc_net_rev - sc_tot_costs)
            sc_margin_pct = (
                _quantize((sc_net_res / sc_net_rev) * Decimal("100.0"))
                if sc_net_rev > Decimal("0.00")
                else Decimal("0.00")
            )

            scenarios[sc_name] = ScenarioProjection(
                name=sc_name,
                enrolled_students=students,
                discount_rate_pct=discount,
                gross_revenue_brl=sc_gross_rev,
                net_revenue_brl=sc_net_rev,
                total_fixed_costs_brl=total_fixed_costs,
                total_variable_costs_brl=sc_var_costs,
                total_costs_brl=sc_tot_costs,
                net_result_brl=sc_net_res,
                profit_margin_pct=sc_margin_pct,
                break_even_achieved=sc_net_res >= Decimal("0.00"),
                assumptions=assumptions,
            )

        # 7. Fluxo de Caixa Mensal (cenário base)
        base_sc = scenarios["base"]
        cash_flow: list[CashFlowMonth] = []
        total_months = max(inputs.academic_duration_months, inputs.financial_duration_months)
        cumulative = Decimal("0.00")

        # Recebimento mensal distribuído no prazo financeiro
        monthly_receipt = (
            _quantize(base_sc.net_revenue_brl / Decimal(str(inputs.financial_duration_months)))
            if inputs.financial_duration_months > 0
            else Decimal("0.00")
        )
        # Desembolso docente distribuído no prazo acadêmico
        monthly_instruction = (
            _quantize(
                inputs.instruction_and_coordination_cost_brl / Decimal(str(inputs.academic_duration_months))
            )
            if inputs.academic_duration_months > 0
            else Decimal("0.00")
        )
        # Desembolso variável distribuído no prazo acadêmico
        monthly_variable = (
            _quantize(base_sc.total_variable_costs_brl / Decimal(str(inputs.academic_duration_months)))
            if inputs.academic_duration_months > 0
            else Decimal("0.00")
        )

        for m in range(1, total_months + 1):
            receipts = monthly_receipt if m <= inputs.financial_duration_months else Decimal("0.00")
            disbursements = Decimal("0.00")
            # Mídia paga concentrada no mês 1 de lançamento
            if m == 1:
                disbursements += inputs.marketing_campaign_cost_brl
            if m <= inputs.academic_duration_months:
                disbursements += monthly_instruction + monthly_variable

            disbursements = _quantize(disbursements)
            net_month = _quantize(receipts - disbursements)
            cumulative = _quantize(cumulative + net_month)

            cash_flow.append(
                CashFlowMonth(
                    month=m,
                    projected_receipts_brl=receipts,
                    projected_disbursements_brl=disbursements,
                    net_cash_flow_brl=net_month,
                    cumulative_cash_flow_brl=cumulative,
                )
            )

        return CourseEconomicsEvaluation(
            status="calculable",
            inputs=inputs,
            net_revenue_per_student_brl=net_revenue_per_student,
            contribution_margin_per_student_brl=contribution_margin_per_student,
            contribution_margin_ratio_pct=cm_ratio_pct,
            total_fixed_costs_cohort_brl=total_fixed_costs,
            break_even_students=break_even_students,
            is_margin_positive=is_margin_positive,
            is_break_even_compatible_with_capacity=is_break_even_compatible,
            scenarios=scenarios,
            monthly_cash_flow=cash_flow,
            message="Avaliação econômico-financeira determinística concluída com sucesso.",
        )
