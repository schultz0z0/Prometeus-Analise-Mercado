"""Base de homologação com resultados sintéticos, sem representar resultados da ENS.

33 cursos: 10 por família principal e três exemplos de categorias distintas.
12 nomes/categorias têm referência oficial; grades e 66 ofertas 2024/2025 são
simulados. Inclui sucesso, queda e cancelamento, sem calibrar aprovação do MBA.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from prometeus.infrastructure.institutional.ens.catalog_references import (
    OFFICIAL_ACADEMIC_REFERENCES,
)

DATASET_VERSION = "ens-synthetic-ipd-v2"

ENS_HISTORICAL_PORTFOLIO: list[dict[str, Any]] = [
    # =========================================================================
    # 1. CURSO BEM-SUCEDIDO (Top Performer Corporativo - MBA Executivo)
    # Segmento: Gestão Estratégica, Resseguros e Liderança Executiva
    # =========================================================================
    {
        "external_id": "ENS-MBA-SEG-01",
        "name": "MBA em Gestão Estratégica de Seguros e Resseguros",
        "category": "MBA Executivo",
        "modality": "online",
        "workload_hours": 360,
        "status": "active",
        "performance_tier": "BEM_SUCEDIDO",
        "quorum_minimum": 20,
        "target_audience": [
            "Gerentes e superintendentes de seguradoras",
            "Corretores corporate e brokers de resseguro",
            "Subscritores seniores e gestores de riscos corporativos",
        ],
        "tags": [
            "seguros",
            "resseguros",
            "gestao executiva",
            "mba",
            "lideranca",
            "mercado segurador",
        ],
        "funnel_history": [
            {
                "period": "2024",
                "cohort_year": 2024,
                "leads": 1250,
                "applicants": 260,
                "enrolled": 84,
                "average_ticket_brl": 15800.0,
                "total_revenue_brl": 1327200.0,
                "quorum_achieved": 84,
                "status": "COMPLETED",
                "notes": "Turma 2024 superou a meta institucional em 420%. NPS 91.",
            },
            {
                "period": "2025",
                "cohort_year": 2025,
                "leads": 1480,
                "applicants": 310,
                "enrolled": 102,
                "average_ticket_brl": 16900.0,
                "total_revenue_brl": 1723800.0,
                "quorum_achieved": 102,
                "status": "COMPLETED",
                "notes": "Turma 2025 com expansão recorde de matrículas via convênios corporativos B2B.",
            },
        ],
    },
    # =========================================================================
    # 2. CURSO BEM-SUCEDIDO (Nicho Técnico Emergente em Alta Expansão)
    # Segmento: Cibersegurança, Subscrição Especializada e Proteção de Dados
    # =========================================================================
    {
        "external_id": "ENS-ESP-CYBER-02",
        "name": "Especialização em Subscrição de Riscos Cibernéticos e Fraudes Digitais",
        "category": "Pós-Graduação Lato Sensu",
        "modality": "online",
        "workload_hours": 180,
        "status": "active",
        "performance_tier": "BEM_SUCEDIDO",
        "quorum_minimum": 18,
        "target_audience": [
            "Subscritores de riscos cibernéticos e linhas financeiras",
            "Analistas de segurança da informação e ciberdefesa",
            "Advogados especializados em Direito Digital, LGPD e incidentes",
        ],
        "tags": [
            "cyber",
            "riscos ciberneticos",
            "subscricao",
            "fraudes digitais",
            "lgpd",
            "seguranca",
        ],
        "funnel_history": [
            {
                "period": "2024",
                "cohort_year": 2024,
                "leads": 780,
                "applicants": 155,
                "enrolled": 54,
                "average_ticket_brl": 9200.0,
                "total_revenue_brl": 496800.0,
                "quorum_achieved": 54,
                "status": "COMPLETED",
                "notes": "Turma inaugural 2024 bateu quórum de 300%. Forte procura do setor bancário e segurador.",
            },
            {
                "period": "2025",
                "cohort_year": 2025,
                "leads": 960,
                "applicants": 198,
                "enrolled": 72,
                "average_ticket_brl": 10400.0,
                "total_revenue_brl": 748800.0,
                "quorum_achieved": 72,
                "status": "COMPLETED",
                "notes": "Crescimento de +33% de alunos YoY impulsionado pela alta de ataques cibernéticos.",
            },
        ],
    },
    # =========================================================================
    # 3. CURSO MEDIANO (Quórum no Limite de Sustentabilidade Econômica)
    # Segmento: Operações Técnicas, Sinistros e Regulação Pericial
    # =========================================================================
    {
        "external_id": "ENS-EXT-SIN-03",
        "name": "Extensão Executiva em Gestão e Regulação Técnica de Sinistros",
        "category": "Extensão Universitária",
        "modality": "hibrido",
        "workload_hours": 90,
        "status": "active",
        "performance_tier": "MEDIANO",
        "quorum_minimum": 18,
        "target_audience": [
            "Reguladores e peritos judiciais de sinistros",
            "Assistentes técnicos de seguradoras e montadoras",
            "Supervisores de sinistros de ramos elementares e automóvel",
        ],
        "tags": [
            "sinistros",
            "regulacao",
            "pericia tecnica",
            "automovel",
            "patrimonial",
            "liquidacao",
        ],
        "funnel_history": [
            {
                "period": "2024",
                "cohort_year": 2024,
                "leads": 490,
                "applicants": 72,
                "enrolled": 22,
                "average_ticket_brl": 5200.0,
                "total_revenue_brl": 114400.0,
                "quorum_achieved": 22,
                "status": "COMPLETED",
                "notes": "Quórum mínimo de 18 alunos foi atingido no limite (22 matriculados). Margem operacional de 26%.",
            },
            {
                "period": "2025",
                "cohort_year": 2025,
                "leads": 520,
                "applicants": 76,
                "enrolled": 24,
                "average_ticket_brl": 5600.0,
                "total_revenue_brl": 134400.0,
                "quorum_achieved": 24,
                "status": "COMPLETED",
                "notes": "Desempenho estável no limite. Ponto de equilíbrio de 18 alunos preservado.",
            },
        ],
    },
    # =========================================================================
    # 4. CURSO FRACO (Procura em Declínio, Margem Estreita / Deficitária)
    # Segmento: Vendas Presenciais Tradicionais para Pequenas Corretoras
    # =========================================================================
    {
        "external_id": "ENS-CAP-VEND-04",
        "name": "Capacitação em Técnicas Tradicionais de Vendas para Corretores Locais",
        "category": "Aperfeiçoamento Profissional",
        "modality": "presencial",
        "workload_hours": 40,
        "status": "active",
        "performance_tier": "FRACO",
        "quorum_minimum": 15,
        "target_audience": [
            "Vendedores iniciantes de balcão",
            "Corretores autônomos de carteiras locais",
        ],
        "tags": ["vendas", "comercial", "corretor", "presencial", "negociacao", "tradicional"],
        "funnel_history": [
            {
                "period": "2024",
                "cohort_year": 2024,
                "leads": 340,
                "applicants": 42,
                "enrolled": 16,
                "average_ticket_brl": 1800.0,
                "total_revenue_brl": 28800.0,
                "quorum_achieved": 16,
                "status": "COMPLETED",
                "notes": "Abriu turma com apenas 1 aluno acima do breakeven de 15 alunos. Margem quase nula.",
            },
            {
                "period": "2025",
                "cohort_year": 2025,
                "leads": 260,
                "applicants": 29,
                "enrolled": 12,
                "average_ticket_brl": 1900.0,
                "total_revenue_brl": 22800.0,
                "quorum_achieved": 12,
                "status": "COMPLETED",
                "notes": "Queda severa de interesse (-23% leads). Turma realizada com 12 alunos com prejuízo operacional assumido.",
            },
        ],
    },
    # =========================================================================
    # 5. OFERTA CANCELADA POR FALTA DE QUÓRUM
    # Segmento: Doutrina Jurídica Pura / Teoria Acadêmica
    # =========================================================================
    {
        "external_id": "ENS-APERF-DIR-05",
        "name": "Aperfeiçoamento em Doutrina e Teoria Pura do Direito Securitário",
        "category": "Aperfeiçoamento Jurídico",
        "modality": "presencial",
        "workload_hours": 60,
        "status": "archived",
        "performance_tier": "CANCELADO_POR_QUORUM",
        "quorum_minimum": 15,
        "target_audience": [
            "Advogados acadêmicos e pesquisadores de Direito dos Seguros",
            "Bacharéis em Direito interessados em teoria contratual clássica",
        ],
        "tags": [
            "direito securitario",
            "doutrina",
            "teoria pura",
            "presencial",
            "juridico",
            "academico",
        ],
        "funnel_history": [
            {
                "period": "2024",
                "cohort_year": 2024,
                "leads": 210,
                "applicants": 24,
                "enrolled": 15,
                "average_ticket_brl": 3900.0,
                "total_revenue_brl": 58500.0,
                "quorum_achieved": 15,
                "status": "COMPLETED",
                "notes": "Turma 2024 abriu exatamente no ponto de equilíbrio (15 alunos).",
            },
            {
                "period": "2025",
                "cohort_year": 2025,
                "leads": 115,
                "applicants": 11,
                "enrolled": 6,
                "average_ticket_brl": 4500.0,
                "total_revenue_brl": 0.0,
                "quorum_achieved": 6,
                "status": "CANCELLED_LOW_QUORUM",
                "notes": "OFERTA CANCELADA: Atingiu apenas 6 matrículas (quórum mínimo exigido: 15 alunos). Turma não viável; valores estornados aos matriculados e oferta arquivada.",
            },
        ],
    },
]


# Os cinco IDs e seus funis anteriores são preservados. Grades e metadados
# abaixo também são fictícios, criados explicitamente para esta homologação.
_BASE_CURRICULA: dict[str, tuple[str, list[str]]] = {
    "ENS-MBA-SEG-01": (
        "pos_mba",
        [
            "Estratégia e gestão de seguros",
            "Resseguros e gestão de riscos",
            "Subscrição e sinistros",
            "Liderança e finanças de seguradoras",
            "Governança e transformação digital",
        ],
    ),
    "ENS-ESP-CYBER-02": (
        "pos_mba",
        [
            "Subscrição de riscos cibernéticos",
            "Fraudes digitais e análise de dados",
            "Gestão de incidentes e proteção de dados",
            "Contratos de seguros cyber",
        ],
    ),
    "ENS-EXT-SIN-03": (
        "extensao",
        [
            "Regulação de sinistros",
            "Perícia técnica e análise de cobertura",
            "Liquidação e atendimento",
            "Gestão de fraudes em seguros",
        ],
    ),
    "ENS-CAP-VEND-04": (
        "qualificacao_tecnica",
        [
            "Prospecção local de seguros",
            "Negociação comercial",
            "Atendimento em corretoras",
            "Renovação de carteiras",
        ],
    ),
    "ENS-APERF-DIR-05": (
        "qualificacao_tecnica",
        [
            "Teoria dos contratos de seguros",
            "Doutrina do direito securitário",
            "Responsabilidade civil",
            "Interpretação de cláusulas e jurisprudência",
        ],
    ),
}
for _course in ENS_HISTORICAL_PORTFOLIO:
    _family, _modules = _BASE_CURRICULA[_course["external_id"]]
    _course.update(
        family=_family,
        curriculum_modules=_modules,
        curriculum_text="; ".join(_modules),
        is_synthetic=True,
        dataset_version=DATASET_VERSION,
    )
    for _funnel in _course["funnel_history"]:
        _funnel.update(price_period="total", data_complete=True)
        _funnel["notes"] = "Cenário sintético de homologação. " + _funnel["notes"]


def _test_course(
    external_id: str,
    name: str,
    category: str,
    family: str,
    modules: list[str],
    history: Sequence[tuple[int, int, int, float]],
) -> dict[str, Any]:
    """Expande observações explícitas, sem sorteio nem ajuste ao score desejado."""
    quorum = 20 if family == "pos_mba" else 15
    final_enrolled = history[-1][2]
    tier = (
        "CANCELADO_POR_QUORUM"
        if final_enrolled < 10
        else "FRACO"
        if final_enrolled < 20
        else "MEDIANO"
        if final_enrolled < 40
        else "BEM_SUCEDIDO"
    )
    funnels = []
    for year, (leads, applicants, enrolled, ticket) in zip((2024, 2025), history, strict=True):
        cancelled = enrolled < 10
        funnels.append(
            {
                "period": str(year),
                "cohort_year": year,
                "leads": leads,
                "applicants": applicants,
                "enrolled": enrolled,
                "average_ticket_brl": ticket,
                "price_period": "total",
                "data_complete": True,
                "total_revenue_brl": 0.0 if cancelled else round(ticket * enrolled, 2),
                "quorum_achieved": enrolled,
                "status": "CANCELLED_LOW_QUORUM" if cancelled else "COMPLETED",
                "notes": "Cenário sintético: inscrições confirmadas e valores estornados."
                if cancelled
                else "Cenário sintético: oferta encerrada; ticket representa o curso completo.",
            }
        )
    return {
        "external_id": external_id,
        "name": name,
        "category": category,
        "family": family,
        "modality": "online",
        "workload_hours": 360 if family == "pos_mba" else 60,
        "status": "archived" if final_enrolled < 10 else "active",
        "performance_tier": tier,
        "quorum_minimum": quorum,
        "target_audience": ["Profissionais do mercado de seguros"],
        "tags": ["seguros", *modules],
        "curriculum_modules": modules,
        "curriculum_text": "; ".join(modules),
        "funnel_history": funnels,
        "is_synthetic": True,
        "dataset_version": DATASET_VERSION,
    }


ENS_HISTORICAL_PORTFOLIO.extend(
    [
        _test_course(
            "ENS-MBA-RISC-06",
            "MBA em Gestão de Riscos e Subscrição de Seguros",
            "MBA Executivo",
            "pos_mba",
            [
                "Gestão de riscos de seguros",
                "Subscrição de riscos corporativos",
                "Resseguros e sinistros",
                "Estratégia e governança de seguradoras",
            ],
            [(1100, 210, 68, 14800), (1020, 198, 64, 15600)],
        ),
        _test_course(
            "ENS-MBA-OPER-07",
            "MBA em Gestão de Operações e Sinistros de Seguros",
            "MBA Executivo",
            "pos_mba",
            [
                "Gestão de operações de seguros",
                "Sinistros e subscrição",
                "Gestão de riscos e resseguros",
                "Liderança e finanças de seguradoras",
            ],
            [(880, 146, 42, 14200), (920, 158, 46, 15100)],
        ),
        _test_course(
            "ENS-MBA-COM-08",
            "MBA em Liderança e Gestão Comercial de Seguros",
            "MBA Executivo",
            "pos_mba",
            [
                "Estratégia comercial de seguros",
                "Liderança de equipes",
                "Canais e relacionamento com corretores",
                "Finanças e gestão de carteiras",
            ],
            [(790, 130, 38, 16000), (810, 125, 35, 16800)],
        ),
        _test_course(
            "ENS-MBA-FIN-09",
            "MBA em Finanças e Gestão Atuarial de Seguros",
            "MBA Executivo",
            "pos_mba",
            [
                "Finanças de seguradoras",
                "Fundamentos atuariais",
                "Solvência e gestão de riscos",
                "Precificação e reservas técnicas",
            ],
            [(650, 95, 30, 18500), (610, 90, 27, 19200)],
        ),
        _test_course(
            "ENS-MBA-DIG-10",
            "MBA em Transformação Digital e Inovação em Seguros",
            "MBA Executivo",
            "pos_mba",
            [
                "Inovação em seguros",
                "Produtos digitais e experiência do cliente",
                "Dados e automação",
                "Estratégia e liderança da transformação",
            ],
            [(540, 84, 25, 17500), (430, 59, 16, 18400)],
        ),
        _test_course(
            "ENS-POS-RES-11",
            "Pós-Graduação em Gestão de Resseguros",
            "Pós-Graduação Lato Sensu",
            "pos_mba",
            [
                "Estrutura de resseguros",
                "Gestão de riscos e tratados",
                "Subscrição de grandes riscos",
                "Sinistros e contratos internacionais",
            ],
            [(900, 160, 50, 11800), (980, 184, 58, 12400)],
        ),
        _test_course(
            "ENS-POS-COMP-12",
            "Pós-Graduação em Compliance e Direito dos Seguros",
            "Pós-Graduação Lato Sensu",
            "pos_mba",
            [
                "Direito dos seguros",
                "Compliance e governança",
                "Contratos e proteção de dados",
                "Controles internos e gestão de riscos",
            ],
            [(470, 76, 23, 10400), (450, 70, 22, 11000)],
        ),
        _test_course(
            "ENS-POS-PREV-13",
            "Pós-Graduação em Previdência e Capitalização",
            "Pós-Graduação Lato Sensu",
            "pos_mba",
            [
                "Previdência complementar",
                "Produtos de capitalização",
                "Planejamento financeiro",
                "Gestão de riscos de longevidade",
            ],
            [(380, 49, 15, 9800), (250, 27, 8, 10200)],
        ),
        _test_course(
            "ENS-EXT-RES-14",
            "Extensão em Operações de Resseguros",
            "Extensão Universitária",
            "extensao",
            [
                "Fundamentos de resseguros",
                "Tratados e facultativos",
                "Gestão de riscos",
                "Recuperação de sinistros",
            ],
            [(680, 120, 46, 3200), (720, 140, 52, 3400)],
        ),
        _test_course(
            "ENS-EXT-SUB-15",
            "Extensão em Subscrição de Seguros Patrimoniais",
            "Extensão Universitária",
            "extensao",
            [
                "Riscos patrimoniais",
                "Inspeção e subscrição",
                "Coberturas de seguros",
                "Precificação técnica",
            ],
            [(600, 106, 39, 2800), (640, 115, 43, 3000)],
        ),
        _test_course(
            "ENS-EXT-CYB-16",
            "Extensão em Seguros Cibernéticos",
            "Extensão Universitária",
            "extensao",
            ["Riscos digitais", "Seguros cyber", "Resposta a incidentes", "Análise de fraudes"],
            [(500, 87, 31, 2600), (590, 100, 37, 2900)],
        ),
        _test_course(
            "ENS-EXT-DAD-17",
            "Extensão em Análise de Dados para Seguros",
            "Extensão Universitária",
            "extensao",
            [
                "Dados do mercado de seguros",
                "Indicadores de sinistros",
                "Visualização e análise",
                "Modelos de risco",
            ],
            [(740, 128, 48, 3100), (850, 150, 57, 3300)],
        ),
        _test_course(
            "ENS-EXT-FRA-18",
            "Extensão em Prevenção a Fraudes em Seguros",
            "Extensão Universitária",
            "extensao",
            [
                "Tipologias de fraude",
                "Investigação de sinistros",
                "Controles preventivos",
                "Análise de documentos",
            ],
            [(430, 69, 24, 2400), (460, 74, 26, 2500)],
        ),
        _test_course(
            "ENS-EXT-VID-19",
            "Extensão em Seguros de Vida e Previdência",
            "Extensão Universitária",
            "extensao",
            [
                "Seguros de pessoas",
                "Previdência complementar",
                "Coberturas e benefícios",
                "Atendimento consultivo",
            ],
            [(390, 58, 21, 2200), (360, 52, 19, 2300)],
        ),
        _test_course(
            "ENS-EXT-RUR-20",
            "Extensão em Seguros Rurais",
            "Extensão Universitária",
            "extensao",
            ["Riscos agrícolas", "Coberturas rurais", "Subscrição rural", "Regulação de perdas"],
            [(300, 44, 17, 2100), (270, 35, 12, 2200)],
        ),
        _test_course(
            "ENS-EXT-MAR-21",
            "Extensão em Seguros de Transportes e Marítimos",
            "Extensão Universitária",
            "extensao",
            [
                "Seguros de transportes",
                "Riscos marítimos",
                "Contratos e coberturas",
                "Gestão de avarias",
            ],
            [(250, 32, 12, 2400), (180, 19, 6, 2600)],
        ),
        _test_course(
            "ENS-EXT-DOUT-22",
            "Extensão em Estudos Teóricos de Seguros Históricos",
            "Extensão Universitária",
            "extensao",
            [
                "História dos seguros",
                "Teoria contratual",
                "Doutrina comparada",
                "Pesquisa documental",
            ],
            [(160, 17, 5, 1900), (100, 8, 0, 2000)],
        ),
        _test_course(
            "ENS-CAP-NEG-23",
            "Capacitação em Negociação Consultiva de Seguros",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Negociação de seguros",
                "Diagnóstico de necessidades",
                "Relacionamento comercial",
                "Propostas e renovação",
            ],
            [(510, 95, 31, 1600), (490, 84, 28, 1700)],
        ),
        _test_course(
            "ENS-CAP-CRM-24",
            "Capacitação em CRM e Carteiras de Seguros",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "CRM para corretoras",
                "Gestão de carteiras de seguros",
                "Automação de atendimento",
                "Indicadores comerciais",
            ],
            [(580, 105, 36, 1400), (620, 110, 34, 1500)],
        ),
        _test_course(
            "ENS-CAP-ATD-25",
            "Capacitação em Atendimento de Sinistros",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Atendimento de sinistros",
                "Documentação de seguros",
                "Comunicação com segurados",
                "Fluxos operacionais",
            ],
            [(380, 65, 23, 1200), (350, 53, 19, 1300)],
        ),
        _test_course(
            "ENS-CAP-PAP-26",
            "Capacitação em Rotinas Manuais de Corretoras",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Arquivos físicos de seguros",
                "Rotinas administrativas",
                "Conferência de propostas",
                "Atendimento presencial",
            ],
            [(280, 35, 12, 1100), (190, 20, 7, 1200)],
        ),
        _test_course(
            "ENS-CAP-PRO-27",
            "Capacitação em Prospecção Digital de Seguros",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Prospecção de seguros",
                "Canais digitais",
                "Qualificação de leads",
                "Comunicação comercial",
            ],
            [(710, 134, 47, 1500), (780, 145, 45, 1600)],
        ),
        _test_course(
            "ENS-CAP-ARQ-28",
            "Capacitação em Arquivamento Analógico de Apólices",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Arquivo de apólices",
                "Conservação documental",
                "Protocolos físicos",
                "Rotinas de escritório",
            ],
            [(140, 12, 3, 900), (80, 5, 0, 950)],
        ),
        _test_course(
            "ENS-CAP-LGP-29",
            "Capacitação em Proteção de Dados para Corretores",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Proteção de dados em seguros",
                "Consentimento e atendimento",
                "Segurança da informação",
                "Gestão de incidentes",
            ],
            [(330, 49, 18, 1300), (320, 44, 17, 1400)],
        ),
        _test_course(
            "ENS-CAP-REN-30",
            "Capacitação em Renovação e Retenção de Seguros",
            "Aperfeiçoamento Profissional",
            "qualificacao_tecnica",
            [
                "Renovação de seguros",
                "Retenção de carteiras",
                "Análise de cancelamentos",
                "Relacionamento com clientes",
            ],
            [(410, 70, 25, 1500), (400, 66, 23, 1600)],
        ),
    ]
)

# Exemplos adicionais testam a exclusão de categorias incompatíveis com MBA.
for _extra_id, _extra_family, _extra_history, _extra_hours in [
    ("ENS-TEST-GRAD-31", "graduacao", [(950, 180, 65, 18000), (1010, 194, 70, 19500)], 1600),
    ("ENS-TEST-IMERSAO-32", "imersao", [(280, 46, 18, 22000), (310, 52, 20, 24500)], 40),
    ("ENS-TEST-CERT-33", "certificacao_avancada", [(360, 64, 25, 1800), (410, 78, 30, 2100)], 20),
]:
    _ref = OFFICIAL_ACADEMIC_REFERENCES[_extra_id]
    _extra = _test_course(
        _extra_id,
        _ref["name"],
        _ref["category"],
        _extra_family,
        _ref["synthetic_modules"],
        _extra_history,
    )
    _extra["workload_hours"] = _extra_hours
    ENS_HISTORICAL_PORTFOLIO.append(_extra)

for _course in ENS_HISTORICAL_PORTFOLIO:
    _course.update(
        curriculum_origin="synthetic", funnel_origin="synthetic", price_origin="synthetic"
    )
    _reference = OFFICIAL_ACADEMIC_REFERENCES.get(_course["external_id"])
    if _reference:
        _course.update(
            name=_reference["name"],
            category=_reference["category"],
            curriculum_modules=_reference["synthetic_modules"],
            curriculum_text="; ".join(_reference["synthetic_modules"]),
            tags=["seguros", *_reference["synthetic_modules"]],
            academic_reference={
                "source_url": _reference["source_url"],
                "checked_at": "2026-10-28",
                "verified_fields": ["name", "category"],
                "scope": "academic_identity_only",
            },
        )
