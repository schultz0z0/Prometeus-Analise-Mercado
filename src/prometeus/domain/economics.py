"""Modelos canônicos do motor econômico-financeiro de cursos (Tarefa 4.2).

Implementa contratos com precisão Decimal, separação entre duração acadêmica
e recebimento financeiro, margem de contribuição, break-even e cenários.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CourseEconomicsInput(BaseModel):
    """Inputs econômico-financeiros com origem e unidade explícitas."""

    total_price_brl: Decimal = Field(default=Decimal("0.00"), description="Preço total de tabela do curso")
    installments: int = Field(default=1, ge=1, le=120, description="Número de parcelas oferecidas")
    discount_rate_pct: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, description="Desconto médio comercial em %")
    default_and_refund_rate_pct: Decimal = Field(default=Decimal("5.00"), ge=0, le=100, description="Taxa estimada de inadimplência e estornos em %")
    tax_rate_pct: Decimal = Field(default=Decimal("15.00"), ge=0, le=100, description="Tributos incidentes sobre a receita bruta em %")
    instruction_and_coordination_cost_brl: Decimal = Field(default=Decimal("0.00"), ge=0, description="Custo fixo de docência, coordenação e produção de conteúdo por turma")
    variable_cost_per_student_brl: Decimal = Field(default=Decimal("0.00"), ge=0, description="Custo variável direto por aluno (material, licenças, diplomas)")
    marketing_campaign_cost_brl: Decimal = Field(default=Decimal("0.00"), ge=0, description="Custo fixo de mídia, campanhas e divulgação comercial por turma")
    cac_per_enrolled_brl: Decimal = Field(default=Decimal("0.00"), ge=0, description="Custo de aquisição variável por matrícula (aplicado somente se não houver verba fixa de campanha)")
    min_capacity: int = Field(default=15, ge=1, description="Quórum mínimo viável da turma")
    max_capacity: int = Field(default=40, ge=1, description="Capacidade máxima de alunos por turma")
    academic_duration_months: int = Field(default=12, ge=1, le=60, description="Duração letiva/acadêmica do curso em meses")
    financial_duration_months: int = Field(default=12, ge=1, le=60, description="Prazo de recebimento das parcelas em meses")


class ScenarioProjection(BaseModel):
    """Projeção de resultado financeiro por cenário de ocupação da turma."""

    name: str
    enrolled_students: int
    discount_rate_pct: Decimal
    gross_revenue_brl: Decimal
    net_revenue_brl: Decimal
    total_fixed_costs_brl: Decimal
    total_variable_costs_brl: Decimal
    total_costs_brl: Decimal
    net_result_brl: Decimal
    profit_margin_pct: Decimal
    break_even_achieved: bool
    assumptions: list[str] = Field(default_factory=list)


class CashFlowMonth(BaseModel):
    """Projeção de fluxo de caixa mensal por turma."""

    month: int
    projected_receipts_brl: Decimal
    projected_disbursements_brl: Decimal
    net_cash_flow_brl: Decimal
    cumulative_cash_flow_brl: Decimal


class CourseEconomicsEvaluation(BaseModel):
    """Avaliação econômico-financeira determinística completa de uma turma."""

    status: Literal["calculable", "not_calculable"]
    missing_inputs: list[str] = Field(default_factory=list)
    message: str = ""
    inputs: CourseEconomicsInput | None = None
    net_revenue_per_student_brl: Decimal | None = None
    contribution_margin_per_student_brl: Decimal | None = None
    contribution_margin_ratio_pct: Decimal | None = None
    total_fixed_costs_cohort_brl: Decimal | None = None
    break_even_students: int | None = None
    is_margin_positive: bool = True
    is_break_even_compatible_with_capacity: bool = True
    scenarios: dict[str, ScenarioProjection] = Field(default_factory=dict)
    monthly_cash_flow: list[CashFlowMonth] = Field(default_factory=list)

