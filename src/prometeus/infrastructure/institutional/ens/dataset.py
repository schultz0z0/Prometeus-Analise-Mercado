"""Dataset canônico sintético de alta fidelidade da ENS (Escola de Negócios e Seguros).

Estruturado especificamente com:
- 5 cursos em segmentos distintos do mercado de seguros (Gestão/MBA, Riscos Cibernéticos, Sinistros, Vendas e Direito Securitário).
- Ofertas de 2 anos (1 oferta por ano: 2024 e 2025).
- Exemplos calibrados de:
  * Alto Sucesso (MBA Executivo e Especialização Cyber)
  * Mediano (Gestão de Sinistros, quórum no limite)
  * Fraco (Capacitação de Vendas presenciais em declínio)
  * Cancelado por falta de quórum (Direito Securitário Doutrinário em 2025: 6 alunos vs quórum mín. de 15).
"""

from __future__ import annotations

from typing import Any

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
        "tags": ["seguros", "resseguros", "gestao executiva", "mba", "lideranca", "mercado segurador"],
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
        "tags": ["cyber", "riscos ciberneticos", "subscricao", "fraudes digitais", "lgpd", "seguranca"],
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
        "tags": ["sinistros", "regulacao", "pericia tecnica", "automovel", "patrimonial", "liquidacao"],
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
        "tags": ["direito securitario", "doutrina", "teoria pura", "presencial", "juridico", "academico"],
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
