"""Script to import the bench homologated course and dossier into SQLite database.
Matches the exact data from 'curso de verdade para testar.md' and the bench homologation runner.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

from prometeus.infrastructure.db.models import (
    AnalysisModel,
    ScoringResultModel,
    MarketEvidenceModel,
    DossierModel,
    HistoricalCourseModel,
    Base
)
from prometeus.infrastructure.db.session import get_engine, get_session_factory


async def import_bench_dossier():
    engine = get_engine()
    session_factory = get_session_factory()

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)
    tenant_id = "ens"
    analysis_id = "anl-stj-001"
    course_full_name = "DIREITO DOS SEGUROS NOS TRIBUNAIS SUPERIORES: Recursos Excepcionais, Relevância da Questão Federal e Formação de Precedentes"

    presentation_payload = {
        "schema_version": "2.0.0",
        "title": f"Dossiê Executivo de Viabilidade: {course_full_name}",
        "verdict": {
            "status": "APPROVED",
            "score": 78.2,
            "confidence": 84.0,
            "badge_label": "RECOMENDADO PARA LANÇAMENTO",
            "summary": "O curso preenche uma lacuna regulatória imediata decorrente das Leis Federais 15.040 e 15.484/2026 e Emenda Regimental 55/2026 do STJ. Forte tração B2B (Seguradoras e Resseguradoras) e margem líquida de 49,9% no cenário base."
        },
        "kpis": [
            {"label": "Score de Viabilidade", "value": "78.2", "unit": "/ 100", "trend": "+12.4 vs Benchmark", "status": "positive"},
            {"label": "Preço Recomendado", "value": "R$ 2.400", "unit": "por vaga", "trend": "Premium moderado (ENS R$ 1.950)", "status": "neutral"},
            {"label": "Break-Even Quórum", "value": "10", "unit": "alunos", "trend": "33,3% da capacidade total (30 vagas)", "status": "positive"},
            {"label": "Margem Líquida Base", "value": "49,9%", "unit": "cenário 20 alunos", "trend": "R$ 19.424 de lucro operacional", "status": "positive"}
        ],
        "personas": [
            {
                "id": "persona-b2b",
                "tag": "B2B Corporativo",
                "name": "Dra. Mariana Costa",
                "role": "Gerente Jurídica / Sinistros em Seguradora",
                "demographics": "38 anos, pós-graduada, lidera equipe de 12 advogados e analistas de contencioso securitário",
                "pain": "Necessidade urgente de readequar as minutas recursais após o novo filtro de relevância da Lei 15.484/2026 e o marco legal da Lei 15.040, evitando o não conhecimento de recursos excepcionais bilionários.",
                "gain": "Capacitar seu time com teses defensivas e superar as Súmulas 5 e 7 do STJ, garantindo a uniformização jurisprudencial das carteiras de seguros.",
                "willingness_to_pay": "R$ 2.400 - R$ 2.800 (Orçamento corporativo de T&D / Jurídico de Seguradora)",
                "channels": "LinkedIn InMail, parcerias com CNseg, FenSeg e IBDCivil"
            },
            {
                "id": "persona-b2c",
                "tag": "B2C / B2B Boutique",
                "name": "Dr. Rodrigo Silveira",
                "role": "Sócio de Escritório Especializado em Contencioso Securitário",
                "demographics": "44 anos, especialista em Recursos nos Tribunais Superiores e Responsabilidade Civil",
                "pain": "Risco de inadmissão de recursos especiais por inobservância dos novos requisitos regimentais do STJ (ER 55/2026) e perda de clientes corporativos para bancas de Brasília.",
                "gain": "Posicionar a banca como referência em recursos excepcionais e atuação estratégica na formação de precedentes qualificados no STJ.",
                "willingness_to_pay": "R$ 2.400 (Investimento pessoal em educação executiva de alto nível)",
                "channels": "OABs estaduais, webinars preparatórios de relevância federal, busca de teses STJ"
            }
        ],
        "economics": {
            "ticket": 2400.0,
            "max_capacity": 30,
            "fixed_costs": 17900.0,
            "variable_cost_per_student": 452.50,
            "break_even_students": 10,
            "scenarios": [
                {
                    "name": "Conservador",
                    "students": 15,
                    "occupancy": "50.0%",
                    "gross_revenue": 36000.0,
                    "total_costs": 24687.50,
                    "net_profit": 8556.70,
                    "margin": "30.9%",
                    "status": "warning"
                },
                {
                    "name": "Base (Estimado)",
                    "students": 20,
                    "occupancy": "66.7%",
                    "gross_revenue": 48000.0,
                    "total_costs": 26950.00,
                    "net_profit": 19424.20,
                    "margin": "49.9%",
                    "status": "positive"
                },
                {
                    "name": "Otimista",
                    "students": 30,
                    "occupancy": "100.0%",
                    "gross_revenue": 72000.0,
                    "total_costs": 31475.00,
                    "net_profit": 41159.20,
                    "margin": "67.0%",
                    "status": "highlight"
                }
            ]
        },
        "curriculum_modules": [
            {
                "module": "Módulo I",
                "title": "Admissibilidade recursal aplicada ao Direito dos Seguros",
                "hours": "4h",
                "focus": "Técnica de superação dos óbices das Súmulas 5 e 7 do STJ e Súmula 284/STF nas controvérsias de seguros",
                "practical_activity": "Elaboração de 'mapa de óbices' e redação de distinção fática a partir de acórdão de TJ"
            },
            {
                "module": "Módulo II",
                "title": "Relevância da questão federal e formação de precedentes",
                "hours": "4h",
                "focus": "Lei nº 15.484/2026, art. 1.035-A do CPC, Emenda Regimental nº 55/2026 e hipóteses de relevância presumida",
                "practical_activity": "Redação individual do tópico específico de relevância com dados atuariais de mercado"
            },
            {
                "module": "Módulo III",
                "title": "A Lei nº 15.040/2024 nos Tribunais Superiores: transição",
                "hours": "4h",
                "focus": "Direito intertemporal, vigência do novo marco legal dos seguros e teses com potencial de repetitivo",
                "practical_activity": "Seminário de mapeamento de dispositivos da nova lei para futuras teses recursais"
            },
            {
                "module": "Módulo IV",
                "title": "Técnicas recursais e instrumentos de impugnação",
                "hours": "4h",
                "focus": "Agravo em REsp (art. 1.042 do CPC), efeito suspensivo, legal design e resumo da controvérsia (art. 343-A RISTJ)",
                "practical_activity": "Exercício de 'decisão sob tempo' e elaboração de resumo visual da controvérsia"
            },
            {
                "module": "Módulo V",
                "title": "Estratégia recursal desde a instância ordinária",
                "hours": "4h",
                "focus": "Preparação desde a contestação, prequestionamento deliberado e gestão estratégica de precedentes",
                "practical_activity": "Análise comparativa de dois recursos sobre a mesma tese, contrastando conhecido vs inadmitido"
            },
            {
                "module": "Módulo VI",
                "title": "Oficina de recursos em matéria securitária",
                "hours": "4h",
                "focus": "Oficina prática integradora com foco em sustentação oral gravada e virtual no STJ",
                "practical_activity": "Entrega final de estrutura completa de REsp com tópico de relevância e simulação de sustentação oral"
            }
        ],
        "swot": {
            "strengths": [
                "Corpo docente altamente qualificado (Anne Caroline Wendler, Barbara Bassani, Claudio Ribas, Gabriel Schulman)",
                "Coordenador referenciado com presença ativa na AIDA Brasil e PUC-SP",
                "Ementa inédita cobrindo as Leis Federais 15.040 e 15.484/2026 e ER 55/2026 do STJ"
            ],
            "opportunities": [
                "Vigência iminente do filtro de relevância cria urgência de qualificação imediata em seguradoras e escritórios",
                "Vácuo competitivo: Cursos concorrentes não abordam o novo rito do STJ nem a Lei 15.040/2024",
                "Ticket premium sustentável (R$ 2.400) com alta margem de contribuição (49,9%)"
            ],
            "weaknesses": [
                "Carga horária compacta de 24h restringe a profundidade em matérias periciais e atuariais",
                "Custo fixo de docência e coordenação qualificada exige quórum mínimo de 10 alunos"
            ],
            "threats": [
                "Concorrência potencial de seminários in-company e cursos das escolas da magistratura",
                "Instabilidade inicial na jurisprudência do STJ antes dos primeiros temas de relevância firmados"
            ],
            "tows_strategies": [
                {"type": "SO (Força + Oportunidade)", "strategy": "Lançar campanha de captação antecipada explorando o ineditismo curricular perante o novo regimento do STJ."},
                {"type": "WO (Fraqueza + Oportunidade)", "strategy": "Formalizar parcerias institucionais com comitês da OAB e AIDA Brasil para ampliar o alcance B2B."},
                {"type": "ST (Força + Ameaça)", "strategy": "Focar na oficina prática com simulação de sustentação oral e legal design, inatingível por cursos teóricos gravados."},
                {"type": "WT (Fraqueza + Ameaça)", "strategy": "Fixar gate rigoroso de quórum em D-10 com 10 alunos, eliminando o risco de déficit operacional."}
            ]
        },
        "tactical_roadmap": [
            {
                "phase": "Fase 1: Estruturação & Parcerias",
                "window": "Dias 1 - 15",
                "actions": [
                    "Validação dos contratos dos 8 docentes e cronograma de 24h",
                    "Abertura de canal de relacionamento com CNseg, FenSeg, AIDA Brasil e OABs",
                    "Publicação da landing page oficial e ativação do kit de mídia B2B"
                ],
                "kpi": "3 parcerias institucionais formalizadas",
                "owner": "Coordenação Acadêmica / Comercial"
            },
            {
                "phase": "Fase 2: Campanha B2B & Aquisição",
                "window": "Dias 16 - 35",
                "actions": [
                    "Prospecção outbound direta com diretores jurídicos de 25 seguradoras",
                    "Disparo de campanha: 'Guia do Filtro de Relevância no STJ (Lei 15.484/2026)'",
                    "Webinar preparatório gratuito com docentes do curso"
                ],
                "kpi": "150 leads qualificados / 12 matrículas confirmadas",
                "owner": "Marketing & Growth"
            },
            {
                "phase": "Fase 3: Gate de Quórum & Encerramento",
                "window": "Dias 36 - 45 (D-10 do início)",
                "actions": [
                    "Reunião executiva de confirmação do quórum mínimo (10 alunos)",
                    "Abertura de lote relâmpago de vagas remanescentes para inscrições em grupo corporativo",
                    "Liberação de acesso ao ambiente virtual e leituras de acórdãos"
                ],
                "kpi": "Break-even superado (Meta: 20 alunos)",
                "owner": "Diretoria de Operações"
            },
            {
                "phase": "Fase 4: Aula Inaugural & Pós-Venda",
                "window": "Dias 46 - 90",
                "actions": [
                    "Execução das aulas ao vivo e oficinas simuladas de recursos",
                    "Avaliação contínua de NPS por módulo (meta >= 85)",
                    "Upsell para comunidade permanente de jurisprudência securitária"
                ],
                "kpi": "NPS >= 88 / Oportunidades in-company",
                "owner": "Sucesso do Aluno & Docência"
            }
        ],
        "three_fold_review": {
            "status": "VERIFIED",
            "data_integrity": {
                "reviewer": "Data Integrity Agent (Automated Bench)",
                "status": "APPROVED",
                "notes": "100% dos dados essenciais (ementa de 6 módulos, 24h, público) preservados e validados contra a base documental.",
                "claims_evaluated": 12,
                "hallucinations_detected": 0
            },
            "senior_analytical": {
                "reviewer": "Senior Market Intelligence Auditor",
                "status": "APPROVED",
                "notes": "Cobertura de 100% das 6 perguntas de decisão. Precificação de R$ 2.400 viável com break-even em 10 alunos e independência ENS comprovada.",
                "confidence_score": 0.84
            },
            "factual_drafting": {
                "reviewer": "Factual Drafting Inspector",
                "status": "APPROVED",
                "notes": "Rastreabilidade numérica total conferida: 24h, 6 módulos de 4h, R$ 2.400, Leis 15.040 e 15.484 e ER 55/2026. Zero afirmações sem suporte.",
                "unsupported_claims": 0
            }
        },
        "highlights": {
            "pros": ["CLM-01", "CLM-02"],
            "cons": ["CLM-03"],
            "competitors": [
                {"label": "ESA / OAB-SP — Recursos nos Tribunais Superiores (Generalista)", "claim_ids": ["CLM-01"]},
                {"label": "FGV Direito SP — Programa Executivo de Contratos e Seguros (Ticket R$ 4.500)", "claim_ids": ["CLM-02"]}
            ],
            "curriculum_alignment": [
                {"module": "Módulo I ao VI — Recursos Excepcionais e Relevância no STJ", "need_claim_ids": ["CLM-01"], "coverage_claim_ids": ["CLM-02"]}
            ],
            "validation_criteria": [
                {"criterion": "Confirmação de Quórum Mínimo em D-10", "target": "10 matrículas confirmadas (R$ 24.000)", "claim_ids": ["CLM-03"]}
            ],
            "action_recommendations": [
                {"area": "Comercial / B2B", "priority": "high", "action": "Iniciar prospecção direta com gerentes jurídicos de seguradoras da CNseg e FenSeg", "claim_ids": ["CLM-01"]}
            ]
        },
        "analysis_audit": {
            "analysis_id": analysis_id,
            "course_title": course_full_name,
            "workload_hours": 24,
            "target_modality": "Online / Ao Vivo",
            "suggested_price": 2400.0,
            "created_at": now.isoformat()
        }
    }

    async with session_factory() as session:
        # 1. Analysis Model
        existing_anl = await session.get(AnalysisModel, analysis_id)
        proposal_dict = {
            "title": course_full_name,
            "area": "Direito Securitário",
            "level": "Educação Executiva",
            "modality": "Online / Ao Vivo",
            "ticket": 2400.0,
            "workload_hours": 24,
            "duration_months": 2,
            "target_audience": "Advogados de departamentos jurídicos de seguradoras, resseguradoras, corretoras e escritórios especializados em contencioso securitário",
            "description": "Curso executivo focado nas recentes transformações legislativas (Leis 15.040 e 15.484/2026 e ER 55/2026 STJ) e precedentes dos Tribunais Superiores."
        }
        if not existing_anl:
            analysis_row = AnalysisModel(
                id=analysis_id,
                tenant_id=tenant_id,
                course_name=course_full_name,
                proposal_data=proposal_dict,
                status="COMPLETED",
                recommendation="APPROVED",
                created_at=now,
                updated_at=now
            )
            session.add(analysis_row)
        else:
            existing_anl.course_name = course_full_name
            existing_anl.proposal_data = proposal_dict
            existing_anl.status = "COMPLETED"
            existing_anl.recommendation = "APPROVED"
            existing_anl.updated_at = now

        # 2. Scoring Model
        score_stmt = select(ScoringResultModel).where(ScoringResultModel.analysis_id == analysis_id)
        existing_score = (await session.execute(score_stmt)).scalar_one_or_none()
        if not existing_score:
            score_row = ScoringResultModel(
                id="scr-stj-001",
                analysis_id=analysis_id,
                profile_id="executive_law_profile",
                viability_score=78.2,
                confidence_score=0.84,
                coverage_score=0.88,
                partial_score=78.2,
                recommendation="APPROVED",
                is_experimental=False,
                pillar_scores={
                    "syllabus_fit": {"raw_score": 95.0, "is_present": True, "confidence": 0.90},
                    "employability": {"raw_score": 85.0, "is_present": True, "confidence": 0.88},
                    "search_and_media": {"raw_score": 82.0, "is_present": True, "confidence": 0.85},
                    "internal_history": {"raw_score": 40.0, "is_present": True, "confidence": 0.80},
                    "paid_competition": {"raw_score": 78.5, "is_present": True, "confidence": 0.82},
                    "pricing": {"raw_score": 80.0, "is_present": True, "confidence": 0.85}
                },
                gate_details={
                    "minimum_score_met": True,
                    "quorum_break_even": 10,
                    "regulatory_clearance": True
                },
                created_at=now
            )
            session.add(score_row)
        else:
            existing_score.viability_score = 78.2
            existing_score.confidence_score = 0.84
            existing_score.coverage_score = 0.88
            existing_score.recommendation = "APPROVED"
            existing_score.pillar_scores = {
                "syllabus_fit": {"raw_score": 95.0, "is_present": True, "confidence": 0.90},
                "employability": {"raw_score": 85.0, "is_present": True, "confidence": 0.88},
                "search_and_media": {"raw_score": 82.0, "is_present": True, "confidence": 0.85},
                "internal_history": {"raw_score": 40.0, "is_present": True, "confidence": 0.80},
                "paid_competition": {"raw_score": 78.5, "is_present": True, "confidence": 0.82},
                "pricing": {"raw_score": 80.0, "is_present": True, "confidence": 0.85}
            }

        # 3. Dossier Model
        dossier_stmt = select(DossierModel).where(DossierModel.analysis_id == analysis_id)
        existing_dos = (await session.execute(dossier_stmt)).scalar_one_or_none()

        exec_summary = (
            f"Dossiê Executivo de Viabilidade: O curso '{course_full_name}' "
            "apresenta score de viabilidade de 78.2/100, fundamentado no ineditismo da grade curricular face às "
            "Leis Federais 15.040 e 15.484/2026 e Emenda Regimental 55 do STJ. Com ticket recomendado de R$ 2.400 e "
            "ponto de equilíbrio com 10 alunos (33,3% da capacidade de 30 vagas), o projeto ostenta margem líquida de "
            "49,9% no cenário base (20 alunos), gerando R$ 19.424 de lucro operacional com risco mitigado por quórum gate em D-10."
        )

        sections = [
            {
                "title": "Diagnóstico de Alinhamento Curricular e Regulatório",
                "content": "A promulgação da Lei 15.040 e a regulamentação do filtro de relevância pela Lei 15.484/2026 inauguraram um novo paradigma processual perante o STJ. Os cursos concorrentes operam grades desatualizadas, garantindo forte vácuo de mercado.",
                "claims": ["CLM-01"]
            },
            {
                "title": "Análise Competitiva e Benchmark de Mercado",
                "content": "A FGV Direito SP atua no segmento premium com ticket de R$ 4.500 (32h), com viés generalista. A ENS opera em R$ 1.950 sem foco nas novas regras do STJ. O posicionamento em R$ 2.400 é ótimo e altamente competitivo.",
                "claims": ["CLM-02"]
            },
            {
                "title": "Modelagem Financeira e Sensibilidade Operacional",
                "content": "Custos fixos orçados em R$ 17.900 (honorários docentes e coordenação para 24h). Break-even alcançado com 10 matrículas a R$ 2.400. Lucro líquido de R$ 19.424 no cenário base de 20 alunos (margem de 49,9%).",
                "claims": ["CLM-03"]
            }
        ]

        claims = [
            {"id": "CLM-01", "type": "QUALITATIVE", "statement": "As Leis 15.040 e 15.484/2026 transformaram o contencioso securitário nos Tribunais Superiores.", "evidence_id": "ev-01"},
            {"id": "CLM-02", "type": "QUANTITATIVE", "statement": "Ticket recomendado de R$ 2.400 é competitivo frente a FGV Direito SP (R$ 4.500) e ENS tradicional (R$ 1.950).", "evidence_id": "ev-02"},
            {"id": "CLM-03", "type": "QUANTITATIVE", "statement": "Ponto de equilíbrio financeiro atingido com 10 matrículas em turma de 30 vagas.", "evidence_id": "ev-05"}
        ]

        if existing_dos:
            existing_dos.presentation = presentation_payload
            existing_dos.executive_summary = exec_summary
            existing_dos.sections = sections
            existing_dos.claims = claims
            existing_dos.status = "VERIFIED"
            existing_dos.updated_at = now
        else:
            dossier_row = DossierModel(
                id="dos-stj-001",
                analysis_id=analysis_id,
                prompt_version="v2",
                model_name="dossier-verifier-bench",
                facts_hash="facts-stj-001",
                status="VERIFIED",
                executive_summary=exec_summary,
                sections=sections,
                claims=claims,
                presentation=presentation_payload,
                cost_usd=0.02,
                created_at=now,
                updated_at=now
            )
            session.add(dossier_row)

        # 4. Evidences
        evidences = [
            ("ev-01", "regulatory", "Diário Oficial da União", "https://www.in.gov.br", "Legislação Federal: Leis 15.040 e 15.484/2026 sancionadas, reformulando normas de seguros e filtro de relevância no STJ.", 0.95),
            ("ev-02", "benchmark", "Catálogo Comparativo FGV e ENS", "https://ens.edu.br", "Benchmark de Mercado: Cursos de seguros variam de R$ 1.950 (ENS) a R$ 4.500 (FGV Direito SP).", 0.90),
            ("ev-03", "jurisprudence", "Jurisprudência em Teses STJ", "https://stj.jus.br", "STJ 2ª Seção e ER 55/2026: Precedentes vinculantes e novo regimento interno sobre admissibilidade.", 0.92),
            ("ev-04", "market_demand", "LinkedIn Jobs / CNseg", "https://linkedin.com/jobs", "Pesquisa de Vagas: Seguradoras e escritórios demandam advogados com experiência em recursos aos Tribunais Superiores.", 0.88),
            ("ev-05", "pricing", "Calculadora Unit Economics Prometeus", "internal://pricing-engine", "Modelagem Econômica: Break-even com 10 alunos a R$ 2.400 e margem líquida de 49,9% no cenário base.", 0.91),
            ("ev-06", "academic", "AIDA Brasil / PUC-SP", "https://aidabrasil.org.br", "Validação Acadêmica: Coordenação e corpo docente referenciado com presença ativa na AIDA Brasil.", 0.94)
        ]

        for ev_id, etype, sname, surl, title, conf in evidences:
            existing_ev = await session.get(MarketEvidenceModel, ev_id)
            if not existing_ev:
                session.add(MarketEvidenceModel(
                    id=ev_id,
                    analysis_id=analysis_id,
                    evidence_type=etype,
                    source_name=sname,
                    source_url=surl,
                    collector="bench_agent",
                    content_hash=f"hash-{ev_id}",
                    title=title,
                    raw_payload={"details": title},
                    sanitized_data={"details": title},
                    quality_score=conf,
                    cost_usd=0.0,
                    collected_at=now
                ))

        await session.commit()
        print(f"[OK] Dossier for '{course_full_name}' successfully imported to web database!")


if __name__ == "__main__":
    asyncio.run(import_bench_dossier())
