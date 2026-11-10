"""Popula o dossiê completo de demonstração executiva (9 subpáginas CMS) para o curso real:
'DIREITO DOS SEGUROS NOS TRIBUNAIS SUPERIORES: Recursos Excepcionais, Relevância da Questão Federal e Formação de Precedentes' (anl-stj-001).

Este script utiliza exclusivamente os construtores determinísticos do Prometeus
(`DossierSynthesisService._build_economics_presentation`, `build_ecosystem_presentation_blocks`,
`build_cms_dossier_pages` e `DossierVerifier.verify_presentation`) para garantir que o dossiê
exemplar passe 100% nas regras de verificação e governança (AGENTS.md).
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.dossiers import (
    DataIntegrityReview,
    DossierAction,
    DossierClaim,
    DossierComparison,
    DossierCurriculumAlignment,
    DossierFactItem,
    DossierFacts,
    DossierHighlights,
    DossierOutput,
    DossierSection,
    DossierValidationCriterion,
    FactualDraftingReview,
    SeniorAnalyticalReview,
    ThreeFoldDossierReview,
)
from prometeus.domain.economics import CourseEconomicsInput
from prometeus.infrastructure.db.models import (
    AnalysisModel,
    Base,
    DossierAreaReviewModel,
    DossierModel,
    MarketEvidenceModel,
    ScoringResultModel,
)
from prometeus.infrastructure.institutional.ens.seeder import seed_historical_courses

ANALYSIS_ID = "anl-stj-001"
TENANT_ID = "ens"
COURSE_NAME = (
    "DIREITO DOS SEGUROS NOS TRIBUNAIS SUPERIORES: Recursos Excepcionais, "
    "Relevância da Questão Federal e Formação de Precedentes"
)


def build_showcase_proposal() -> dict[str, Any]:
    econ_input = CourseEconomicsInput(
        total_price_brl=2490.0,
        installments=6,
        discount_rate_pct=4.0,
        default_and_refund_rate_pct=2.0,
        tax_rate_pct=8.5,
        instruction_and_coordination_cost_brl=16200.0,
        variable_cost_per_student_brl=95.0,
        marketing_campaign_cost_brl=8500.0,
        cac_per_enrolled_brl=0.0,
        min_capacity=15,
        max_capacity=45,
        academic_duration_months=2,
        financial_duration_months=6,
    )
    return {
        "name": COURSE_NAME,
        "area": "Direito dos Seguros, Processo Civil e Tribunais Superiores",
        "level": "Extensão Executiva",
        "course_type": "11 | Extensão",
        "modality": "EAD Live (Online ao vivo)",
        "workload_hours": 24,
        "ticket": 2490.0,
        "price_period": "total",
        "schedule": "Segundas e Quartas, período noturno (6 módulos de 4h)",
        "audience": (
            "Advogados contenciosos de seguradoras, resseguradoras e corretoras, "
            "bancas especializadas em Direito Securitário, gestores jurídicos de sinistros "
            "e assessores de tribunais."
        ),
        "Objectives": (
            "Capacitar advogados e gestores jurídicos do setor de seguros na intersecção entre "
            "o novo marco material (Lei nº 15.040/2024) e o novo filtro processual da relevância "
            "da questão federal no STJ (Lei nº 15.484/2026 e Emendas Regimentais nº 53 e 55/2026)."
        ),
        "syllabus": (
            "Módulo I (4h): Admissibilidade recursal aplicada ao Direito dos Seguros (Súmulas 5, 7, 83, 211/STJ e STF). "
            "Módulo II (4h): Relevância da questão federal (Lei 15.484/2026, art. 1.035-A CPC, ER 55/2026 STJ) e formação de precedentes. "
            "Módulo III (4h): A Lei nº 15.040/2024 nos Tribunais Superiores: transição, agravamento de risco, regulação de sinistro, prescrição e seguro de vida. "
            "Módulo IV (4h): Técnicas recursais, Resumo da Controvérsia (ER 53/2026), Legal Design e Julgamento Virtual (art. 184-A RISTJ). "
            "Módulo V (4h): Estratégia recursal desde a instância ordinária e gestão de carteira contenciosa securitária. "
            "Módulo VI (4h): Oficina prática de recursos em matéria securitária e simulação de sustentação oral."
        ),
        "faculty": [
            "Dra. Anne Caroline Wendler (Doutora UFPR / AIDA Brasil)",
            "Dra. Barbara Bassani (Doutora USP / Prof. ENS / AIDA)",
            "Dr. Claudio Ribas (Doutor PUC-SP)",
            "Dr. Gabriel Schulman (Doutor UERJ / Prof. ENS)",
            "Dr. Henrique Mouta (Doutor UFPA / Procurador)",
            "Dra. Louise Rainer Pereira Gionédis (Doutora UFPR)",
            "Dra. Juliana Bizzaria (Doutora UNIMAR)",
            "Dra. Maria Amélia Mastrorosa Vianna (Doutora PUC-PR)",
        ],
        "economics": econ_input.model_dump(mode="json"),
        "_institution_context": {
            "competitors": [
                {"id": "fgv", "name": "FGV Educação Executiva", "category": "executive_business"},
                {"id": "insper", "name": "Insper", "category": "executive_business"},
                {"id": "puc", "name": "PUC-SP COGEAE", "category": "technical_academic"},
                {"id": "ibmec", "name": "Ibmec", "category": "executive_business"},
                {"id": "esa", "name": "ESA OAB", "category": "legal_niche"},
            ],
            "sector_radar": [
                {
                    "id": "porto-seguro",
                    "name": "Porto Seguro",
                    "priority": "primary",
                    "monitoring_focus": ["Lei 15.040/2024", "Sinistros", "Subscrição"],
                    "social": {"linkedin_scope": "national"},
                },
                {
                    "id": "bradesco-seguros",
                    "name": "Bradesco Seguros",
                    "priority": "primary",
                    "monitoring_focus": ["Contencioso Securitário", "Regulação", "Relevância STJ"],
                    "social": {"linkedin_scope": "national"},
                },
                {
                    "id": "tokio-marine",
                    "name": "Tokio Marine",
                    "priority": "primary",
                    "monitoring_focus": ["Seguros Corporativos", "RC", "Súmula 7 STJ"],
                    "social": {"linkedin_scope": "national"},
                },
                {
                    "id": "allianz",
                    "name": "Allianz Seguros",
                    "priority": "primary",
                    "monitoring_focus": ["Grandes Riscos", "Julgamento Virtual", "Precedentes"],
                    "social": {"linkedin_scope": "global"},
                },
            ],
        },
    }


def build_showcase_evidences() -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    return [
        # 1. Histórico Institucional ENS (4 turmas comparáveis com série histórica de alunos)
        {
            "id": "ev-stj-hist-01",
            "evidence_type": "INTERNAL_HISTORICAL",
            "source_name": "ens_historical_crm",
            "source_url": "https://ens.edu.br/cursos/extensao-direito-seguros",
            "collector": "internal_db",
            "title": "Novo Marco Legal dos Seguros (Lei 15.040/2024) — Turma 2025.2",
            "quality_score": 0.96,
            "sanitized_data": {
                "course_name": "Novo Marco Legal dos Seguros (Lei 15.040/2024)",
                "short_label": "Marco 25.2",
                "period": "2025.2",
                "enrolled": 42,
                "students": 42,
                "graduates": 39,
                "leads": 380,
                "applicants": 64,
                "average_ticket_brl": 2350.0,
                "completion_rate_pct": 92.8,
                "ipd_score": 88.0,
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=5),
        },
        {
            "id": "ev-stj-hist-02",
            "evidence_type": "INTERNAL_HISTORICAL",
            "source_name": "ens_historical_crm",
            "source_url": "https://ens.edu.br/cursos/contencioso-securitario-avancado",
            "collector": "internal_db",
            "title": "Contencioso Securitário e Regulação de Sinistros Complexos — Turma 2025.1",
            "quality_score": 0.95,
            "sanitized_data": {
                "course_name": "Contencioso Securitário e Sinistros Complexos",
                "short_label": "Contenc. 25.1",
                "period": "2025.1",
                "enrolled": 36,
                "students": 36,
                "graduates": 33,
                "leads": 310,
                "applicants": 52,
                "average_ticket_brl": 2190.0,
                "completion_rate_pct": 91.6,
                "ipd_score": 84.0,
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=5),
        },
        {
            "id": "ev-stj-hist-03",
            "evidence_type": "INTERNAL_HISTORICAL",
            "source_name": "ens_historical_crm",
            "source_url": "https://ens.edu.br/cursos/direito-do-seguro-e-resseguro",
            "collector": "internal_db",
            "title": "Direito do Seguro, Resseguro e Arbitragem — Turma 2024.2",
            "quality_score": 0.94,
            "sanitized_data": {
                "course_name": "Direito do Seguro, Resseguro e Arbitragem",
                "short_label": "Resseg. 24.2",
                "period": "2024.2",
                "enrolled": 31,
                "students": 31,
                "graduates": 28,
                "leads": 275,
                "applicants": 45,
                "average_ticket_brl": 2100.0,
                "completion_rate_pct": 90.3,
                "ipd_score": 81.0,
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=5),
        },
        {
            "id": "ev-stj-hist-04",
            "evidence_type": "INTERNAL_HISTORICAL",
            "source_name": "ens_historical_crm",
            "source_url": "https://ens.edu.br/cursos/processo-civil-aplicado-seguros",
            "collector": "internal_db",
            "title": "Processo Civil e Precedentes no Mercado Segurador — Turma 2026.1",
            "quality_score": 0.96,
            "sanitized_data": {
                "course_name": "Processo Civil e Precedentes em Seguros",
                "short_label": "Preced. 26.1",
                "period": "2026.1",
                "enrolled": 46,
                "students": 46,
                "graduates": 43,
                "leads": 415,
                "applicants": 71,
                "average_ticket_brl": 2450.0,
                "completion_rate_pct": 93.5,
                "ipd_score": 90.0,
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=4),
        },
        # 2. Ofertas de Concorrentes Fixos (OFFER com preço total e carga horária medidos)
        {
            "id": "ev-stj-comp-fgv",
            "evidence_type": "OFFER",
            "source_name": "apify_google_search",
            "source_url": "https://educacao-executiva.fgv.br/cursos/curta-media-duracao/direito/recursos-nos-tribunais-superiores",
            "collector": "apify",
            "title": "FGV Direito SP — Recursos nos Tribunais Superiores e Precedentes",
            "quality_score": 0.94,
            "sanitized_data": {
                "matched_actor_id": "fgv",
                "matched_actor_name": "FGV Educação Executiva",
                "observed_offer_title": "Recursos nos Tribunais Superiores e Precedentes (Geral)",
                "modality": "Online (EAD Live)",
                "workload_hours": 36,
                "price_brl": 3480.0,
                "total_price_brl": 3480.0,
                "price_display": "R$ 3.480",
                "has_direct_offer": True,
                "status": "adjacent_offer",
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=3),
        },
        {
            "id": "ev-stj-comp-insper",
            "evidence_type": "OFFER",
            "source_name": "apify_google_search",
            "source_url": "https://www.insper.edu.br/educacao-executiva/direito/contencioso-estrategico",
            "collector": "apify",
            "title": "Insper — Contencioso Estratégico e Gestão de Litígios Complexos",
            "quality_score": 0.93,
            "sanitized_data": {
                "matched_actor_id": "insper",
                "matched_actor_name": "Insper",
                "observed_offer_title": "Contencioso Estratégico e Gestão de Litígios Corporativos",
                "modality": "Híbrido",
                "workload_hours": 32,
                "price_brl": 4200.0,
                "total_price_brl": 4200.0,
                "price_display": "R$ 4.200",
                "has_direct_offer": True,
                "status": "adjacent_offer",
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=3),
        },
        {
            "id": "ev-stj-comp-puc",
            "evidence_type": "OFFER",
            "source_name": "apify_google_search",
            "source_url": "https://www.pucsp.br/cogeae/extensao/direito-processual-civil-tribunais",
            "collector": "apify",
            "title": "PUC-SP COGEAE — Recursos Excepcionais no STJ e STF",
            "quality_score": 0.91,
            "sanitized_data": {
                "matched_actor_id": "puc",
                "matched_actor_name": "PUC-SP COGEAE",
                "observed_offer_title": "Extensão em Recursos Excepcionais no STJ e STF",
                "modality": "Online (Ao vivo)",
                "workload_hours": 30,
                "price_brl": 2690.0,
                "total_price_brl": 2690.0,
                "price_display": "R$ 2.690",
                "has_direct_offer": True,
                "status": "adjacent_offer",
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=3),
        },
        {
            "id": "ev-stj-comp-ibmec",
            "evidence_type": "OFFER",
            "source_name": "apify_google_search",
            "source_url": "https://www.ibmec.br/curta-duracao/direito-securitario-contratos",
            "collector": "apify",
            "title": "Ibmec — Direito Securitário e Contratos de Seguro",
            "quality_score": 0.90,
            "sanitized_data": {
                "matched_actor_id": "ibmec",
                "matched_actor_name": "Ibmec",
                "observed_offer_title": "Direito Securitário e Novos Contratos de Seguro",
                "modality": "Online (EAD)",
                "workload_hours": 20,
                "price_brl": 1890.0,
                "total_price_brl": 1890.0,
                "price_display": "R$ 1.890",
                "has_direct_offer": True,
                "status": "adjacent_offer",
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=3),
        },
        {
            "id": "ev-stj-comp-esa",
            "evidence_type": "OFFER",
            "source_name": "apify_google_search",
            "source_url": "https://esa.oab.org.br/cursos/relevancia-questao-federal-stj",
            "collector": "apify",
            "title": "ESA Nacional OAB — Prática de Recurso Especial e Filtro da Relevância",
            "quality_score": 0.89,
            "sanitized_data": {
                "matched_actor_id": "esa",
                "matched_actor_name": "ESA OAB",
                "observed_offer_title": "Prática de Recurso Especial e Filtro da Relevância (Geral)",
                "modality": "Online (Gravado)",
                "workload_hours": 16,
                "price_brl": 1190.0,
                "total_price_brl": 1190.0,
                "price_display": "R$ 1.190",
                "has_direct_offer": True,
                "status": "adjacent_offer",
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=3),
        },
        # 3. Tendências de Busca & Mídia (TRENDS)
        {
            "id": "ev-stj-trends-01",
            "evidence_type": "TRENDS",
            "source_name": "apify_google_trends",
            "source_url": "https://trends.google.com.br/trends/explore?q=Lei%2015040%20seguros,relevancia%20questao%20federal%20STJ",
            "collector": "apify",
            "title": "Crescimento de buscas por Lei 15.040/2024, Lei 15.484/2026 e ER 55/2026 STJ",
            "quality_score": 0.92,
            "sanitized_data": {
                "keyword": "Lei 15.040/2024 + Relevância da Questão Federal STJ (Lei 15.484/2026)",
                "growth_trend_pct": 34.0,
                "search_interest_index": 86,
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=2),
        },
        # 4. Mercado de Trabalho & Demanda Profissional (JOB_MARKET)
        {
            "id": "ev-stj-jobs-01",
            "evidence_type": "JOB_MARKET",
            "source_name": "apify_linkedin_jobs",
            "source_url": "https://www.linkedin.com/jobs/search/?keywords=Advogado%20Contencioso%20Securitario%20Tribunais%20Superiores",
            "collector": "apify",
            "title": "Demanda por Advogados Sêniores em Contencioso Estratégico Securitário e Tribunais Superiores",
            "quality_score": 0.93,
            "sanitized_data": {
                "open_jobs_count": 38,
                "roles": [
                    "Advogado Sênior Contencioso Estratégico Securitário (STJ/STF)",
                    "Especialista Jurídico de Sinistros Complexos e Grandes Riscos",
                    "Coordenador de Contencioso Cível e Securitário (Lei 15.040/2024)",
                ],
                "_qualification": {"accepted": True, "used_in_score": True},
            },
            "collected_at": now - timedelta(days=2),
        },
        # 5. Sinais do Radar Setorial (Seguradoras Primárias e Resseguradoras)
        {
            "id": "ev-stj-radar-porto",
            "evidence_type": "REGULATORY_SIGNAL",
            "source_name": "sector_radar_insurers",
            "source_url": "https://www.portoseguro.com.br/institucional/relacoes-com-investidores",
            "collector": "apify",
            "title": "Porto Seguro — Revisão de teses recursais e governança de sinistros sob a Lei 15.040/2024",
            "quality_score": 0.91,
            "sanitized_data": {
                "actor_id": "porto-seguro",
                "insurer_name": "Porto Seguro",
                "theme_detected": "Transição da Lei 15.040/2024 e Prescrição Securitária",
                "market_or_broker_pain": "Necessidade de padronizar prequestionamento e capítulo autônomo de relevância federal nas carteiras massificadas e de automóvel/vida.",
                "_qualification": {"accepted": True, "context_only": True},
            },
            "collected_at": now - timedelta(days=2),
        },
        {
            "id": "ev-stj-radar-bradesco",
            "evidence_type": "REGULATORY_SIGNAL",
            "source_name": "sector_radar_insurers",
            "source_url": "https://www.bradescoseguros.com.br/clientes/institucional",
            "collector": "apify",
            "title": "Bradesco Seguros — Adequação das bancas credenciadas à ER 55/2026 e Lei 15.484/2026",
            "quality_score": 0.92,
            "sanitized_data": {
                "actor_id": "bradesco-seguros",
                "insurer_name": "Bradesco Seguros",
                "theme_detected": "Filtro da Relevância da Questão Federal (Lei 15.484/2026 e ER 55/2026)",
                "market_or_broker_pain": "Exigência de demonstração qualificada de relevância jurídica, econômica ou social nos recursos especiais interpostos após 03/09/2026.",
                "_qualification": {"accepted": True, "context_only": True},
            },
            "collected_at": now - timedelta(days=2),
        },
        {
            "id": "ev-stj-radar-tokio",
            "evidence_type": "REGULATORY_SIGNAL",
            "source_name": "sector_radar_insurers",
            "source_url": "https://www.tokiomarine.com.br/institucional/",
            "collector": "apify",
            "title": "Tokio Marine — Gestão de contencioso em seguros de danos, RC e prazos de liquidação de sinistro",
            "quality_score": 0.90,
            "sanitized_data": {
                "actor_id": "tokio-marine",
                "insurer_name": "Tokio Marine",
                "theme_detected": "Superação das Súmulas 5 e 7/STJ e Distinção Probatória",
                "market_or_broker_pain": "Alto índice de inadmissão por Súmulas 5 e 7/STJ quando a qualificação jurídica da apólice e do sinistro não é construída desde a apelação.",
                "_qualification": {"accepted": True, "context_only": True},
            },
            "collected_at": now - timedelta(days=2),
        },
        {
            "id": "ev-stj-radar-allianz",
            "evidence_type": "REGULATORY_SIGNAL",
            "source_name": "sector_radar_insurers",
            "source_url": "https://www.allianz.com.br/sobre-allianz.html",
            "collector": "apify",
            "title": "Allianz Seguros — Memorial estratégico, Resumo da Controvérsia (ER 53/2026) e Julgamento Virtual",
            "quality_score": 0.89,
            "sanitized_data": {
                "actor_id": "allianz",
                "insurer_name": "Allianz",
                "theme_detected": "Resumo da Controvérsia (ER 53/2026) e Julgamento Virtual",
                "market_or_broker_pain": "Adaptação das sustentações orais e memoriais ao art. 184-A e art. 343-A do RISTJ em disputas de grandes riscos.",
                "_qualification": {"accepted": True, "context_only": True},
            },
            "collected_at": now - timedelta(days=2),
        },
    ]


def _sync_sqlite_columns(sync_conn: Any) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            col_type = col.type.compile(sync_conn.dialect)
            default_clause = ""
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                default_clause = f" DEFAULT {col.server_default.arg}"
            elif not col.nullable:
                default_clause = " DEFAULT ''"
            sync_conn.execute(
                text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}{default_clause}')
            )


async def seed_showcase_dossier(db_path: str | None = None) -> dict[str, Any]:
    env_db_url = os.environ.get("DATABASE_URL")
    if db_path is not None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite+aiosqlite:///{path.as_posix()}"
    elif env_db_url:
        db_url = env_db_url
    else:
        path = Path("var/prometeus.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite+aiosqlite:///{path.as_posix()}"

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if db_url.startswith("sqlite"):
            await conn.run_sync(_sync_sqlite_columns)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as session:
        # 1. Garante portfólio histórico institucional da ENS
        await seed_historical_courses(session, tenant_id=TENANT_ID, reset=False)

        proposal = build_showcase_proposal()
        raw_evidences = build_showcase_evidences()

        # Remove registros anteriores de anl-stj-001 para recriação limpa e determinística
        await session.execute(
            delete(DossierAreaReviewModel).where(DossierAreaReviewModel.analysis_id == ANALYSIS_ID)
        )
        await session.execute(
            delete(DossierModel).where(DossierModel.analysis_id == ANALYSIS_ID)
        )
        await session.execute(
            delete(ScoringResultModel).where(ScoringResultModel.analysis_id == ANALYSIS_ID)
        )
        await session.execute(
            delete(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == ANALYSIS_ID)
        )
        await session.execute(
            delete(AnalysisModel).where(AnalysisModel.id == ANALYSIS_ID)
        )
        await session.flush()

        # 2. Cria AnalysisModel
        analysis = AnalysisModel(
            id=ANALYSIS_ID,
            tenant_id=TENANT_ID,
            course_name=COURSE_NAME,
            status="COMPLETED",
            recommendation="APPROVED",
            proposal_data=proposal,
        )
        session.add(analysis)

        # 3. Cria MarketEvidenceModel
        evidence_models: list[MarketEvidenceModel] = []
        for idx, ev in enumerate(raw_evidences, start=1):
            ev_model = MarketEvidenceModel(
                id=ev["id"],
                analysis_id=ANALYSIS_ID,
                evidence_type=ev["evidence_type"],
                source_name=ev["source_name"],
                source_url=ev["source_url"],
                collector=ev["collector"],
                content_hash=f"sha256-stj-showcase-{idx:02d}",
                title=ev["title"],
                raw_payload=ev["sanitized_data"],
                sanitized_data=ev["sanitized_data"],
                quality_score=ev["quality_score"],
                cost_usd=0.02,
                collected_at=ev["collected_at"],
            )
            session.add(ev_model)
            evidence_models.append(ev_model)

        # 4. Cria ScoringResultModel (6 pilares oficiais do modelo portfolio-v2)
        pillar_scores = {
            "internal_history": {
                "raw_score": 88.0,
                "weight": 0.20,
                "is_present": True,
                "confidence": 0.94,
                "evidence_count": 4,
                "features": {
                    "evidence_ids": [
                        "ev-stj-hist-01",
                        "ev-stj-hist-02",
                        "ev-stj-hist-03",
                        "ev-stj-hist-04",
                    ]
                },
            },
            "paid_competition": {
                "raw_score": 82.0,
                "weight": 0.20,
                "is_present": True,
                "confidence": 0.91,
                "evidence_count": 5,
                "features": {
                    "evidence_ids": [
                        "ev-stj-comp-fgv",
                        "ev-stj-comp-insper",
                        "ev-stj-comp-puc",
                        "ev-stj-comp-ibmec",
                        "ev-stj-comp-esa",
                    ]
                },
            },
            "search_and_media": {
                "raw_score": 85.0,
                "weight": 0.20,
                "is_present": True,
                "confidence": 0.89,
                "evidence_count": 1,
                "features": {"evidence_ids": ["ev-stj-trends-01"]},
            },
            "employability": {
                "raw_score": 84.0,
                "weight": 0.15,
                "is_present": True,
                "confidence": 0.90,
                "evidence_count": 1,
                "features": {"evidence_ids": ["ev-stj-jobs-01"]},
            },
            "syllabus_fit": {
                "raw_score": 92.0,
                "weight": 0.15,
                "is_present": True,
                "confidence": 0.95,
                "evidence_count": 5,
                "features": {
                    "evidence_ids": [
                        "ev-stj-radar-porto",
                        "ev-stj-radar-bradesco",
                        "ev-stj-radar-tokio",
                        "ev-stj-radar-allianz",
                        "ev-stj-hist-01",
                    ]
                },
            },
            "pricing": {
                "raw_score": 79.0,
                "weight": 0.10,
                "is_present": True,
                "confidence": 0.92,
                "evidence_count": 5,
                "features": {
                    "evidence_ids": [
                        "ev-stj-comp-fgv",
                        "ev-stj-comp-insper",
                        "ev-stj-comp-puc",
                        "ev-stj-comp-ibmec",
                        "ev-stj-comp-esa",
                    ]
                },
            },
        }
        # IVO = 88*0.20 + 82*0.20 + 85*0.20 + 84*0.15 + 92*0.15 + 79*0.10 = 17.6 + 16.4 + 17.0 + 12.6 + 13.8 + 7.9 = 85.3
        viability_score = 85.3
        coverage_score = 0.94
        confidence_score = 0.91

        scoring = ScoringResultModel(
            id="scr-stj-001",
            analysis_id=ANALYSIS_ID,
            profile_id="portfolio-v2",
            viability_score=viability_score,
            partial_score=viability_score,
            coverage_score=coverage_score,
            confidence_score=confidence_score,
            recommendation="APPROVED",
            is_experimental=False,
            pillar_scores=pillar_scores,
            gate_details={
                "profile_id": "portfolio-v2",
                "observed_score": viability_score,
                "score_blocks": {
                    "internal": {"score": 88.0, "coverage": 1.0, "confidence": 0.94},
                    "external": {"score": 84.6, "coverage": 0.92, "confidence": 0.90},
                },
            },
        )
        session.add(scoring)

        # 5. Constrói DossierFacts e DossierOutput verificados
        fact_items = [
            DossierFactItem(
                evidence_id=ev["id"],
                source_type=ev["evidence_type"],
                title=ev["title"],
                key_metrics={
                    **{k: v for k, v in ev["sanitized_data"].items() if k != "_qualification"},
                    **(
                        {
                            "evidence_role": "context_only",
                            "actor_role": "sector_radar",
                            "matched_actor_id": ev["sanitized_data"].get("actor_id"),
                            "matched_actor_name": ev["sanitized_data"].get("insurer_name"),
                        }
                        if ev["sanitized_data"].get("_qualification", {}).get("context_only")
                        else {}
                    ),
                    **(
                        {
                            "competition_relation": "adjacent",
                            "competition_reason": "Oferta de pós/extensão jurídica ou securitária comparável em carga horária e público-alvo.",
                            "collected_at": ev["collected_at"].isoformat(),
                        }
                        if ev["evidence_type"] == "OFFER"
                        else {}
                    ),
                },
                summary=ev["title"],
                source_url=ev["source_url"],
            )
            for ev in raw_evidences
        ]

        analysis_audit = {
            "reading": {
                "schema_version": 1,
                "complete": True,
                "status": "COMPLETE",
                "archives_total": 4,
                "items_produced": 15,
                "items_retrieved": 15,
                "items_preserved": 15,
                "items_read": 15,
                "items_pending": 0,
                "parts_total": 15,
                "parts_completed": 15,
                "fragments_total": 30,
                "fragments_covered": 30,
                "normalized_evidences_total": 15,
                "normalized_evidences_complete": 15,
                "archives": [],
            },
            "internal": {
                "mean_evasion_rate": 0.072,
                "comparables": [
                    {
                        "name": "Resseguro 2024.2",
                        "course_name": "Resseguro 2024.2",
                        "students_count": 31,
                        "evasion_rate": 0.097,
                        "leads": 275,
                        "applicants": 45,
                        "reason": "Turma histórica de Direito do Seguro e Resseguro (31 matriculados, 90,3% conclusão)",
                        "ipd_score": 81.0,
                    },
                    {
                        "name": "Contencioso 2025.1",
                        "course_name": "Contencioso 2025.1",
                        "students_count": 36,
                        "evasion_rate": 0.083,
                        "leads": 310,
                        "applicants": 52,
                        "reason": "Recorte aplicado a departamentos jurídicos de seguradoras (36 matriculados, 91,7% conclusão)",
                        "ipd_score": 84.0,
                    },
                    {
                        "name": "Marco Legal 2025.2",
                        "course_name": "Marco Legal 2025.2",
                        "students_count": 42,
                        "evasion_rate": 0.071,
                        "leads": 380,
                        "applicants": 64,
                        "reason": "Mesma família temática jurídica securitária da Lei 15.040/2024 (42 matriculados, 92,9% conclusão)",
                        "ipd_score": 88.0,
                    },
                    {
                        "name": "Precedentes 2026.1",
                        "course_name": "Precedentes 2026.1",
                        "students_count": 46,
                        "evasion_rate": 0.065,
                        "leads": 415,
                        "applicants": 71,
                        "reason": "Público-alvo idêntico de contencioso estratégico (46 matriculados, 93,5% conclusão)",
                        "ipd_score": 90.0,
                    },
                ],
            },
            "pricing": {
                "method": "arithmetic_mean_per_comparable_course",
                "mean_total_brl": 2690.0,
                "internal_count": 4,
                "external_count": 5,
                "comparables": [
                    {
                        "title": "FGV Direito SP — Recursos nos Tribunais Superiores",
                        "total_brl": 3480.0,
                        "origin": "external",
                        "evidence_ids": ["ev-stj-comp-fgv"],
                    },
                    {
                        "title": "Insper — Contencioso Estratégico e Litígios Complexos",
                        "total_brl": 4200.0,
                        "origin": "external",
                        "evidence_ids": ["ev-stj-comp-insper"],
                    },
                    {
                        "title": "PUC-SP COGEAE — Recursos Excepcionais no STJ e STF",
                        "total_brl": 2690.0,
                        "origin": "external",
                        "evidence_ids": ["ev-stj-comp-puc"],
                    },
                    {
                        "title": "Ibmec — Direito Securitário e Contratos de Seguro",
                        "total_brl": 1890.0,
                        "origin": "external",
                        "evidence_ids": ["ev-stj-comp-ibmec"],
                    },
                    {
                        "title": "ESA OAB — Prática de Recurso Especial",
                        "total_brl": 1190.0,
                        "origin": "external",
                        "evidence_ids": ["ev-stj-comp-esa"],
                    },
                ],
                "excluded": [],
            },
            "evidence": {
                "collected_records": 15,
                "accepted_records": 11,
                "context_records": 4,
                "excluded_records": 0,
                "used_in_score_records": 11,
                "sources": {
                    "ens_historical_crm": {
                        "collected_records": 4,
                        "accepted_records": 4,
                        "context_records": 0,
                        "excluded_records": 0,
                        "used_in_score_records": 4,
                        "reasons": {},
                    },
                    "apify_google_search": {
                        "collected_records": 5,
                        "accepted_records": 5,
                        "context_records": 0,
                        "excluded_records": 0,
                        "used_in_score_records": 5,
                        "reasons": {},
                    },
                    "apify_google_trends": {
                        "collected_records": 1,
                        "accepted_records": 1,
                        "context_records": 0,
                        "excluded_records": 0,
                        "used_in_score_records": 1,
                        "reasons": {},
                    },
                    "apify_linkedin_jobs": {
                        "collected_records": 1,
                        "accepted_records": 1,
                        "context_records": 0,
                        "excluded_records": 0,
                        "used_in_score_records": 1,
                        "reasons": {},
                    },
                    "sector_radar_insurers": {
                        "collected_records": 4,
                        "accepted_records": 0,
                        "context_records": 4,
                        "excluded_records": 0,
                        "used_in_score_records": 0,
                        "reasons": {},
                    },
                },
            },
        }

        limitations = [
            "Agenda concentrada de 8 docentes doutores atuantes em contencioso estratégico exige bloqueio de datas com 60 dias de antecedência.",
            "A vigência da Emenda Regimental nº 55/2026 do STJ (03/09/2026) demanda atualização contínua dos julgados da 2ª Seção durante a turma.",
            "Potencial lançamento de cursos livres de curta duração por escolas jurídicas generalistas após os primeiros precedentes sobre a Lei 15.484/2026.",
        ]

        comp_ids = ["fgv", "insper", "puc", "ibmec", "esa"]
        research_plan = {
            "tool_calls": [
                *[
                    {
                        "id": f"call-disc-{cid}",
                        "capability": "google_search",
                        "parameters": {"competitor_id": cid, "collection_phase": "discovery"},
                    }
                    for cid in comp_ids
                ],
                *[
                    {
                        "id": f"call-val-{cid}",
                        "capability": "web_crawler",
                        "parameters": {"competitor_id": cid, "collection_phase": "validation"},
                    }
                    for cid in comp_ids
                ],
            ],
            "tool_runs": [
                *[
                    {
                        "id": f"run-disc-{cid}",
                        "planned_call_id": f"call-disc-{cid}",
                        "capability": "google_search",
                        "status": "SUCCEEDED",
                        "valid_items_count": 1,
                        "provider_run_id": f"apify-disc-{cid}",
                        "parameters": {
                            "competitor_id": cid,
                            "collection_phase": "discovery",
                            "observation_status": "observed",
                        },
                    }
                    for cid in comp_ids
                ],
                *[
                    {
                        "id": f"run-val-{cid}",
                        "planned_call_id": f"call-val-{cid}",
                        "capability": "web_crawler",
                        "status": "SUCCEEDED",
                        "valid_items_count": 1,
                        "provider_run_id": f"apify-val-{cid}",
                        "parameters": {
                            "competitor_id": cid,
                            "collection_phase": "validation",
                            "observation_status": "observed",
                        },
                    }
                    for cid in comp_ids
                ],
            ],
        }

        facts = DossierFacts(
            analysis_id=ANALYSIS_ID,
            course_name=COURSE_NAME,
            target_audience=proposal["audience"],
            recommendation="APPROVED",
            viability_score=viability_score,
            coverage_score=coverage_score,
            confidence_score=confidence_score,
            pillar_summaries={k: float(v["raw_score"]) for k, v in pillar_scores.items()},
            pillar_details=pillar_scores,
            scoring_experimental=False,
            items=fact_items,
            limitations=limitations,
            research_plan=research_plan,
            counterevidence=[
                "Escolas generalistas (FGV Direito SP, PUC-SP e ESA OAB) oferecem cursos de técnica recursal em tribunais superiores, mas sem recorte verticalizado na Lei nº 15.040/2024."
            ],
            analysis_audit=analysis_audit,
        )

        claims = [
            DossierClaim(
                claim_id="CLM-STJ-01",
                statement=(
                    "A convergência entre a entrada em vigor da Lei nº 15.040/2024 (dezembro/2025) e a regulamentação "
                    "do filtro da relevância da questão federal (Lei nº 15.484/2026 e ER nº 55/2026 do STJ) abriu um "
                    "whitespace competitivo: nenhum dos 5 concorrentes com oferta ativa combina técnica recursal de "
                    "tribunais superiores com o novo Direito Material dos Seguros."
                ),
                evidence_ids=[
                    "ev-stj-comp-fgv",
                    "ev-stj-comp-insper",
                    "ev-stj-comp-puc",
                    "ev-stj-trends-01",
                ],
                verification_status="verified",
                support_level="observed",
            ),
            DossierClaim(
                claim_id="CLM-STJ-02",
                statement=(
                    "O portfólio histórico da ENS em Direito Securitário e Processo Civil registra média de 38,8 alunos "
                    "matriculados por turma (pico de 46 alunos em 2026.1) e taxa média de conclusão superior a 92%, "
                    "sustentando o cenário base de 32 matrículas (70% de ocupação)."
                ),
                evidence_ids=[
                    "ev-stj-hist-01",
                    "ev-stj-hist-02",
                    "ev-stj-hist-03",
                    "ev-stj-hist-04",
                ],
                verification_status="verified",
                support_level="observed",
            ),
            DossierClaim(
                claim_id="CLM-STJ-03",
                statement=(
                    "O ticket proposto de R$ 2.490 (24h, R$ 103,75/h) posiciona o curso 7,4% abaixo da média das "
                    "escolas comparáveis (R$ 2.690), entregando ponto de equilíbrio em 12 matrículas e resultado "
                    "líquido projetado de R$ 44.361 (margem de 60,8%) no cenário base."
                ),
                evidence_ids=[
                    "ev-stj-comp-fgv",
                    "ev-stj-comp-insper",
                    "ev-stj-comp-puc",
                    "ev-stj-comp-ibmec",
                    "ev-stj-comp-esa",
                ],
                verification_status="verified",
                support_level="observed",
            ),
            DossierClaim(
                claim_id="CLM-STJ-04",
                statement=(
                    "O Radar Setorial capturou sinais diretos em Porto Seguro, Bradesco Seguros, Tokio Marine e Allianz "
                    "sobre a necessidade imediata de capacitar bancas credenciadas e jurídicos internos para superar as "
                    "Súmulas 5 e 7/STJ, estruturar o capítulo de relevância (art. 1.035-A CPC) e redigir o Resumo da "
                    "Controvérsia (ER 53/2026)."
                ),
                evidence_ids=[
                    "ev-stj-radar-porto",
                    "ev-stj-radar-bradesco",
                    "ev-stj-radar-tokio",
                    "ev-stj-radar-allianz",
                ],
                verification_status="verified",
                support_level="observed",
            ),
            DossierClaim(
                claim_id="CLM-STJ-05",
                statement=(
                    "Foram identificadas 38 posições abertas e crescimento de 34% nas buscas por contencioso estratégico "
                    "securitário e filtro da relevância no STJ, confirmando alta absorção profissional para os 6 módulos "
                    "e para a oficina prática do Módulo VI."
                ),
                evidence_ids=["ev-stj-jobs-01", "ev-stj-trends-01"],
                verification_status="verified",
                support_level="observed",
            ),
        ]

        sections = [
            DossierSection(
                section_id="sec-executive",
                title="Parecer Executivo para Diretoria",
                target_audience="executive",
                content=(
                    "Recomendação: APROVADO PARA LANÇAMENTO IMEDIATO (IVO 85/100 · IE 93/100). "
                    "O curso 'Direito dos Seguros nos Tribunais Superiores' captura uma janela regulatória e "
                    "jurisprudencial única no mercado segurador brasileiro: a combinação entre a vigência da "
                    "Lei nº 15.040/2024 e o novo filtro da relevância da questão federal no STJ (Lei nº 15.484/2026 "
                    "e ER nº 55/2026). Enquanto FGV Direito SP (R$ 3.480), Insper (R$ 4.200) e PUC-SP (R$ 2.690) "
                    "ofertam cursos generalistas de processo nos tribunais superiores e o Ibmec (R$ 1.890) aborda "
                    "apenas direito material, a ENS detém autoridade institucional exclusiva para unir os dois eixos "
                    "com um corpo docente de 8 doutores atuantes na AIDA Brasil e nos tribunais."
                ),
                claim_ids=["CLM-STJ-01", "CLM-STJ-02", "CLM-STJ-03"],
            ),
            DossierSection(
                section_id="sec-curriculum",
                title="Diretrizes para Coordenação Acadêmica e Produto",
                target_audience="academic",
                content=(
                    "A arquitetura de 24 horas dividida em 6 módulos de 4 horas (segundas e quartas à noite) "
                    "apresenta aderência curricular nota 92/100. Recomenda-se destacar como entregáveis práticos: "
                    "(1) Matriz de superação das Súmulas 5 e 7/STJ em contratos de seguro (Módulo I); "
                    "(2) Template de Tópico Demonstração da Relevância da Questão Federal conforme art. 1.035-A CPC "
                    "e ER 55/2026 (Módulo II); (3) Mapa das novas questões federais da Lei 15.040/2024 em prescrição, "
                    "agravamento de risco, regulação de sinistro e título executivo no seguro de vida art. 132 (Módulo III); "
                    "e (4) Oficina prática com simulação de sustentação oral e Resumo da Controvérsia ER 53/2026 (Módulos IV a VI)."
                ),
                claim_ids=["CLM-STJ-01", "CLM-STJ-04", "CLM-STJ-05"],
            ),
            DossierSection(
                section_id="sec-marketing",
                title="Estratégia Comercial, Precificação e Captação B2B/B2C",
                target_audience="marketing",
                content=(
                    "Com ticket de R$ 2.490 e breakeven em apenas 12 matrículas (26,7% da capacidade de 45 vagas), "
                    "a estratégia comercial deve priorizar pacotes corporativos B2B para os departamentos jurídicos "
                    "de seguradoras (Porto Seguro, Bradesco Seguros, Tokio Marine, Allianz, Mapfre) e escritórios "
                    "credenciados, além de divulgação conjunta com a AIDA Brasil."
                ),
                claim_ids=["CLM-STJ-02", "CLM-STJ-03", "CLM-STJ-04"],
            ),
        ]

        highlights = DossierHighlights(
            pros=["CLM-STJ-01", "CLM-STJ-02", "CLM-STJ-03", "CLM-STJ-04", "CLM-STJ-05"],
            cons=[],
            competitors=[
                DossierComparison(
                    label="FGV Direito SP / Insper / PUC-SP",
                    claim_ids=["CLM-STJ-01", "CLM-STJ-03"],
                ),
                DossierComparison(
                    label="Ibmec / ESA OAB",
                    claim_ids=["CLM-STJ-01", "CLM-STJ-03"],
                ),
            ],
            curriculum_alignment=[
                DossierCurriculumAlignment(
                    module="Módulos I e II — Admissibilidade (Súmulas 5 e 7) e Relevância da Questão Federal (Lei 15.484/2026 e ER 55/2026)",
                    need_claim_ids=["CLM-STJ-01", "CLM-STJ-04"],
                    coverage_claim_ids=["CLM-STJ-01", "CLM-STJ-04"],
                ),
                DossierCurriculumAlignment(
                    module="Módulo III — A Lei nº 15.040/2024 nos Tribunais Superiores: transição e novas questões federais",
                    need_claim_ids=["CLM-STJ-01", "CLM-STJ-04"],
                    coverage_claim_ids=["CLM-STJ-04", "CLM-STJ-05"],
                ),
                DossierCurriculumAlignment(
                    module="Módulos IV, V e VI — Resumo da Controvérsia (ER 53/2026), Gestão de Carteira e Oficina Prática",
                    need_claim_ids=["CLM-STJ-04", "CLM-STJ-05"],
                    coverage_claim_ids=["CLM-STJ-04", "CLM-STJ-05"],
                ),
            ],
            validation_criteria=[
                DossierValidationCriterion(
                    criterion="Homologar tabela de desconto progressivo B2B para pacotes de 5+ inscrições de seguradoras e bancas credenciadas",
                    target="Diretoria Financeira & Comercial",
                    claim_ids=["CLM-STJ-03"],
                ),
                DossierValidationCriterion(
                    criterion="Confirmar cronograma de bancas docentes dos 8 doutores para a Oficina Prática do Módulo VI",
                    target="Coordenação Acadêmica Produto",
                    claim_ids=["CLM-STJ-02", "CLM-STJ-05"],
                ),
            ],
            action_recommendations=[
                DossierAction(
                    area="comercial",
                    action="Estruturar oferta corporativa B2B (in-company / lotes) para diretorias jurídicas de seguradoras e escritórios credenciados antes do marco de vigência da ER 55/2026",
                    claim_ids=["CLM-STJ-03", "CLM-STJ-04"],
                    priority="high",
                ),
                DossierAction(
                    area="marketing",
                    action="Realizar webinar de lançamento 'Lei 15.040/2024 e o Filtro da Relevância no STJ' com o Coordenador e docentes da AIDA Brasil",
                    claim_ids=["CLM-STJ-01", "CLM-STJ-05"],
                    priority="high",
                ),
                DossierAction(
                    area="academic",
                    action="Consolidar caderno de casos reais e acórdãos da 3ª e 4ª Turmas do STJ para a Oficina Prática do Módulo VI",
                    claim_ids=["CLM-STJ-04", "CLM-STJ-05"],
                    priority="medium",
                ),
            ],
        )

        executive_summary = (
            "O curso de extensão 'Direito dos Seguros nos Tribunais Superiores: Recursos Excepcionais, "
            "Relevância da Questão Federal e Formação de Precedentes' (24h, Online ao vivo, R$ 2.490) "
            "apresenta altíssima viabilidade de lançamento (IVO 85/100 e IE 93/100). A proposta ocupa "
            "uma lacuna competitiva clara ao integrar o novo marco contratual securitário (Lei nº 15.040/2024) "
            "à regulamentação do filtro da relevância da questão federal no STJ (Lei nº 15.484/2026 e "
            "Emendas Regimentais nº 53 e 55/2026), com ponto de equilíbrio em 12 alunos e margem líquida "
            "projetada de 60,8% no cenário base (32 matrículas)."
        )

        three_fold_review = ThreeFoldDossierReview(
            data_integrity=DataIntegrityReview(
                source_count=15,
                observations_count=15,
                brief_facts_count=15,
            ),
            senior_analytical=SeniorAnalyticalReview(
                question_coverage={"demand": True, "competition": True, "economics": True, "curriculum": True},
            ),
            factual_drafting=FactualDraftingReview(),
            summary="Revisão automática concluída nas três frentes; encaminhado para homologação departamental.",
        )

        dossier_obj = DossierOutput(
            id="dos-stj-001",
            analysis_id=ANALYSIS_ID,
            prompt_version="dossier-v1@3.1.0",
            model_name="gpt-5.4",
            executive_summary=executive_summary,
            executive_summary_claim_ids=[
                "CLM-STJ-01",
                "CLM-STJ-02",
                "CLM-STJ-03",
                "CLM-STJ-04",
            ],
            highlights=highlights,
            sections=sections,
            claims=claims,
            facts_hash=facts.compute_facts_hash(),
            three_fold_review=three_fold_review,
        )

        # 6. Calcula blocos determinísticos de Economia, Ecossistema e 9 Subpáginas CMS via serviço oficial
        visual_blocks = DossierSynthesisService._build_visual_presentation_blocks(
            analysis,
            scoring,
            facts,
            dossier_obj,
        )

        presentation = {
            "schema_version": dossier_obj.schema_version,
            "executive_summary_claim_ids": dossier_obj.executive_summary_claim_ids,
            "highlights": highlights.model_dump(mode="json"),
            "limitations": limitations,
            "counterevidence": facts.counterevidence,
            "analysis_audit": analysis_audit,
            "verification": {"attempt_count": 1, "attempts": []},
            "three_fold_review": three_fold_review.to_dict(),
            **visual_blocks,
        }

        # 7. Valida no DossierVerifier oficial antes de persistir!
        verifier = DossierVerifier()
        issues = verifier.verify_presentation(
            dossier=dossier_obj,
            facts=facts,
            presentation=presentation,
            proposal=proposal,
        )
        if issues:
            raise RuntimeError(
                f"Falha na verificação determinística do dossiê showcase: {issues}"
            )

        # 8. Persiste Revisões Departamentais na tabela SQL `dossier_area_reviews` (Aba 8 — Revisões)
        base_time = datetime.now(UTC) - timedelta(hours=6)
        area_reviews_seed = [
            DossierAreaReviewModel(
                id="arev-stj-001",
                analysis_id=ANALYSIS_ID,
                tenant_id=TENANT_ID,
                area="marketing",
                status="APPROVED",
                reviewer_name="Ana Ribeiro",
                comment=(
                    "Demanda validada (+34% em buscas por Lei 15.040/2024 e filtro da relevância no STJ). "
                    "Campanha B2B com AIDA Brasil e webinar de lançamento aprovados."
                ),
                version_label="v1.1",
                created_at=base_time + timedelta(hours=1),
            ),
            DossierAreaReviewModel(
                id="arev-stj-002",
                analysis_id=ANALYSIS_ID,
                tenant_id=TENANT_ID,
                area="produto",
                status="APPROVED",
                reviewer_name="Bruno Castro",
                comment=(
                    "Estrutura de 24h (6 módulos de 4h às segundas e quartas) e quadro de 8 docentes doutores "
                    "homologados. Oficina prática do Módulo VI alinhada ao RISTJ (ER 53 e 55/2026)."
                ),
                version_label="v1.2",
                created_at=base_time + timedelta(hours=2),
            ),
            DossierAreaReviewModel(
                id="arev-stj-003",
                analysis_id=ANALYSIS_ID,
                tenant_id=TENANT_ID,
                area="comercial",
                status="APPROVED",
                reviewer_name="Carla Menezes",
                comment=(
                    "Meta do cenário base (32 matrículas) validada junto às carteiras corporativas de "
                    "seguradoras e escritórios credenciados. Breakeven em 12 alunos oferece alta segurança."
                ),
                version_label="v1.3",
                created_at=base_time + timedelta(hours=3),
            ),
            DossierAreaReviewModel(
                id="arev-stj-004",
                analysis_id=ANALYSIS_ID,
                tenant_id=TENANT_ID,
                area="financeiro",
                status="IN_REVIEW",
                reviewer_name="Diego Martins",
                comment=(
                    "Cascata financeira determinística conferida (Receita Líquida Base R$ 72.907 e Resultado "
                    "R$ 44.361 · Margem 60,8%). Em revisão final da política de desconto para lotes corporativos (5+ vagas)."
                ),
                version_label="v1.4",
                created_at=base_time + timedelta(hours=4),
            ),
        ]
        for rev in area_reviews_seed:
            session.add(rev)

        dossier_model = DossierModel(
            id=dossier_obj.id,
            analysis_id=ANALYSIS_ID,
            prompt_version=dossier_obj.prompt_version,
            model_name=dossier_obj.model_name,
            facts_hash=dossier_obj.facts_hash,
            status="VERIFIED",
            executive_summary=dossier_obj.executive_summary,
            sections=[s.model_dump(mode="json") for s in dossier_obj.sections],
            claims=[c.model_dump(mode="json") for c in dossier_obj.claims],
            presentation=presentation,
            cost_usd=0.14,
            created_at=datetime.now(UTC),
        )
        session.add(dossier_model)
        await session.flush()

        # Atualiza também todos os demais dossiês existentes no banco de dados
        from sqlalchemy import select

        from prometeus.entrypoints.rest.app import _hydrate_dossier_presentation

        other_dossiers = (
            await session.execute(select(DossierModel).where(DossierModel.analysis_id != ANALYSIS_ID))
        ).scalars().all()
        for existing_dos in other_dossiers:
            anl_row = await session.get(AnalysisModel, existing_dos.analysis_id)
            if not anl_row:
                continue
            scr_row = (
                await session.execute(
                    select(ScoringResultModel).where(ScoringResultModel.analysis_id == existing_dos.analysis_id)
                )
            ).scalar_one_or_none()
            ev_rows = list(
                (
                    await session.execute(
                        select(MarketEvidenceModel).where(MarketEvidenceModel.analysis_id == existing_dos.analysis_id)
                    )
                ).scalars().all()
            )
            rev_rows = list(
                (
                    await session.execute(
                        select(DossierAreaReviewModel)
                        .where(DossierAreaReviewModel.analysis_id == existing_dos.analysis_id)
                        .order_by(DossierAreaReviewModel.created_at.desc())
                    )
                ).scalars().all()
            )
            existing_dos.presentation = _hydrate_dossier_presentation(
                analysis_id=existing_dos.analysis_id,
                course_name=anl_row.course_name,
                proposal=dict(anl_row.proposal_data or {}),
                dossier=existing_dos,
                scoring=scr_row,
                evidences=ev_rows,
                area_reviews=rev_rows,
            )

        await session.commit()

    await engine.dispose()
    return {
        "analysis_id": ANALYSIS_ID,
        "course_name": COURSE_NAME,
        "viability_score": viability_score,
        "verification_valid": len(issues) == 0,
        "subpages": list(presentation["cms_pages"]["pages"].keys()),
    }


if __name__ == "__main__":
    result = asyncio.run(seed_showcase_dossier())
    print("Showcase Dossier populado com sucesso:", result)
