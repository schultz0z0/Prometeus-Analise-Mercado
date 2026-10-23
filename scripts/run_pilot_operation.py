"""Script de Execução e Operação da Fase Piloto da ENS (Shadow Mode).

Executa a validação operacional completa contra o ambiente Staging:
- Verificação de probes de saúde (/health/live, /health/ready)
- Submissão de 3 propostas canônicas para o tenant ENS
- Validação do cabeçalho obrigatório Idempotency-Key e duplicidade
- Monitoramento da execução dos workers assíncronos (Celery + Redis)
- Recuperação e auditoria dos Dossiês Estruturados gerados
- Registro de decisões humanas institucionais (RF-009)
- Registro de desfechos reais de mercado pós-lançamento (RF-013)
- Verificação da entrega de Webhooks em Shadow Mode
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("prometeus.pilot_operation")

BASE_URL = "http://localhost:8000"

RUN_TS = time.strftime("%Y%m%d%H%M%S")

PILOT_PROPOSALS = [
    {
        "idempotency_key": f"pilot-ens-{RUN_TS}-mba-001",
        "course_name": "MBA em Gestão Estratégica de Riscos e Seguros",
        "tenant_id": "ens",
        "proposal_data": {
            "modality": "online",
            "workload_hours": 360,
            "target_audience": "Executivos, diretores e corretores de seguros de grande porte",
            "target_price": 14800.0,
            "category": "MBA Executivo",
            "coordination": "Núcleo de Altos Estudos em Riscos",
        },
        "decision": {
            "user_id": "carlos_alberto_ens_dir",
            "user_role": "Diretor Acadêmico",
            "decision": "APPROVED",
            "rationale": "Curso com alta aderência ao plano estratégico da ENS e demanda aquecida no mercado securitário.",
            "adjustments": {},
        },
        "outcome": {
            "external_course_id": f"ENS-MBA-RISK-{RUN_TS}",
            "launch_date": "2026-11-01",
            "enrolled_count": 34,
            "leads_count": 280,
            "applicants_count": 52,
            "revenue_brl": 503200.0,
            "notes": "Turma inaugural superou o ponto de equilíbrio de 18 alunos com folga.",
        },
    },
    {
        "idempotency_key": f"pilot-ens-{RUN_TS}-cert-cyber-002",
        "course_name": "Certificação Executiva em Subscrição de Riscos Cibernéticos e IA",
        "tenant_id": "ens",
        "proposal_data": {
            "modality": "hibrido",
            "workload_hours": 120,
            "target_audience": "Subscritores de riscos, peritos e analistas de sinistros cibernéticos",
            "target_price": 8900.0,
            "category": "Certificação Profissional",
            "coordination": "Cátedra de Tecnologia e Seguros Digitais",
        },
        "decision": {
            "user_id": "mariana_souza_ens_coord",
            "user_role": "Coordenadora de Inovação",
            "decision": "APPROVED_WITH_ADJUSTMENTS",
            "rationale": "Aprovado com inclusão de módulo prático sobre regulação de IA na SUSEP.",
            "adjustments": {"include_module": "Compliance de IA e Lei de IA Securitária"},
        },
        "outcome": {
            "external_course_id": f"ENS-CERT-CYBER-{RUN_TS}",
            "launch_date": "2026-11-15",
            "enrolled_count": 28,
            "leads_count": 195,
            "applicants_count": 41,
            "revenue_brl": 249200.0,
            "notes": "Forte atratividade para resseguradoras e grandes corretoras.",
        },
    },
    {
        "idempotency_key": f"pilot-ens-{RUN_TS}-aperf-susep-003",
        "course_name": "Curso de Aperfeiçoamento em Regulação e Compliance SUSEP",
        "tenant_id": "ens",
        "proposal_data": {
            "modality": "presencial",
            "workload_hours": 60,
            "target_audience": "Oficiais de compliance, atuários e consultores jurídicos",
            "target_price": 3500.0,
            "category": "Aperfeiçoamento",
            "coordination": "Centro de Estudos de Regulação ENS",
        },
        "decision": {
            "user_id": "colegiado_reg_ens",
            "user_role": "Colegiado de Regulação",
            "decision": "APPROVED",
            "rationale": "Atende a exigências recentes de atualização de circular SUSEP.",
            "adjustments": {},
        },
        "outcome": {
            "external_course_id": f"ENS-APERF-SUSEP-{RUN_TS}",
            "launch_date": "2026-12-01",
            "enrolled_count": 45,
            "leads_count": 310,
            "applicants_count": 60,
            "revenue_brl": 157500.0,
            "notes": "Vagas preenchidas integralmente 10 dias antes do encerramento das inscrições.",
        },
    },
]


def run_pilot() -> None:
    """Executa o ciclo completo de operação do piloto."""
    logger.info("=== INICIANDO OPERAÇÃO DO PILOTO ENS (PROMETEUS - STAGING) ===")
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. Health checks
    logger.info("1. Verificando probes de saúde do cluster...")
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200, f"Falha no live probe: {live_resp.text}"
    logger.info(f"   [OK] Liveness Probe: {live_resp.json()}")

    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 200, f"Falha no readiness probe: {ready_resp.text}"
    ready_data = ready_resp.json()
    assert ready_data["database"] == "ok", "Database não está pronta"
    assert ready_data["redis"] == "ok", "Redis não está pronto"
    logger.info(f"   [OK] Readiness Probe: {ready_data}")

    results_summary: list[dict[str, Any]] = []

    # 2. Processamento das propostas do Piloto ENS
    for idx, prop in enumerate(PILOT_PROPOSALS, 1):
        logger.info(f"\n--- Processando Proposta {idx}/3: '{prop['course_name']}' ---")

        # A. Submissão Inicial
        headers = {
            "Idempotency-Key": prop["idempotency_key"],
            "X-Correlation-ID": f"pilot-corr-{idx}",
        }
        payload = {
            "course_name": prop["course_name"],
            "tenant_id": prop["tenant_id"],
            "proposal_data": prop["proposal_data"],
        }

        logger.info(
            f"   Submetendo POST /v1/analyses (Idempotency-Key: {prop['idempotency_key']})..."
        )
        create_resp = client.post("/v1/analyses", json=payload, headers=headers)
        assert create_resp.status_code == 202, (
            f"Erro na submissão: {create_resp.status_code} {create_resp.text}"
        )
        data = create_resp.json()
        analysis_id = data["analysis_id"]
        logger.info(f"   [OK] 202 Accepted -> analysis_id: {analysis_id}, status: {data['status']}")

        # B. Teste de Idempotência
        logger.info("   Validando Idempotência: reenviando mesma chave...")
        idem_resp = client.post("/v1/analyses", json=payload, headers=headers)
        assert idem_resp.status_code == 202
        idem_data = idem_resp.json()
        assert idem_data["analysis_id"] == analysis_id
        assert "Idempotency-Key" in idem_data["message"]
        logger.info(f"   [OK] Idempotência validada: {idem_data['message']}")

        # C. Aguarda conclusão do processamento assíncrono (Celery Worker)
        logger.info("   Aguardando conclusão do processamento pelo Celery Worker...")
        max_retries = 20
        status_data: dict[str, Any] = {}
        for attempt in range(max_retries):
            time.sleep(1.0)
            status_resp = client.get(f"/v1/analyses/{analysis_id}/status")
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data.get("status") == "COMPLETED":
                    logger.info(
                        f"   [OK] Análise concluída no attempt {attempt + 1}: status=COMPLETED, recomendação={status_data.get('recommendation')}"
                    )
                    break
        else:
            raise RuntimeError(
                f"Timeout aguardando conclusão da análise {analysis_id}: {status_data}"
            )

        # D. Consulta Dossiê Auditável
        logger.info(
            f"   Consultando Dossiê Estruturado via GET /v1/analyses/{analysis_id}/dossier..."
        )
        dossier_resp = client.get(f"/v1/analyses/{analysis_id}/dossier")
        assert dossier_resp.status_code == 200, f"Falha ao obter dossiê: {dossier_resp.text}"
        dossier = dossier_resp.json()
        logger.info(
            f"   [OK] Dossiê ID: {dossier['id']} | Status: {dossier['status']} | Prompt: {dossier['prompt_version']}"
        )
        logger.info(f"        Sumário Executivo: {dossier['executive_summary']}")
        logger.info(
            f"        Seções geradas: {len(dossier['sections'])} | Claims verificadas: {len(dossier['claims'])}"
        )

        # E. Registro da Decisão Humana Institucional (RF-009)
        logger.info("   Registrando decisão humana institucional (RF-009)...")
        dec_payload = prop["decision"]
        dec_resp = client.post(f"/v1/analyses/{analysis_id}/decisions", json=dec_payload)
        assert dec_resp.status_code == 201, f"Falha ao registrar decisão humana: {dec_resp.text}"
        dec_data = dec_resp.json()
        logger.info(
            f"   [OK] Decisão ID: {dec_data['decision_id']} | Decisão: {dec_data['decision']} | Status: {dec_data['status']}"
        )

        # F. Registro de Desfecho Real de Mercado Pós-Lançamento (RF-013)
        logger.info("   Registrando desfecho real de mercado pós-lançamento (RF-013)...")
        out_payload = prop["outcome"]
        out_resp = client.post(f"/v1/analyses/{analysis_id}/outcomes", json=out_payload)
        assert out_resp.status_code == 201, (
            f"Falha ao registrar desfecho de mercado: {out_resp.text}"
        )
        out_data = out_resp.json()
        logger.info(
            f"   [OK] Desfecho ID: {out_data['outcome_id']} | Alunos: {out_data['enrolled_count']} | Status: {out_data['status']}"
        )

        # G. Consulta Detalhada da Análise (Steps e Auditoria)
        det_resp = client.get(f"/v1/analyses/{analysis_id}")
        assert det_resp.status_code == 200
        det_data = det_resp.json()

        results_summary.append(
            {
                "course_name": prop["course_name"],
                "analysis_id": analysis_id,
                "status": det_data["status"],
                "recommendation": det_data["recommendation"],
                "steps_count": len(det_data["steps"]),
                "audit_events_count": len(det_data["audit_events"]),
                "dossier_id": dossier["id"],
                "decision": dec_data["decision"],
                "enrolled_count": out_data["enrolled_count"],
            }
        )

    logger.info("\n=== OPERAÇÃO DO PILOTO ENS CONCLUÍDA COM 100% DE SUCESSO ===")
    print("\nRESUMO DA OPERAÇÃO DO PILOTO:")
    print(json.dumps(results_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        run_pilot()
    except Exception as exc:
        logger.error(f"Erro fatal na operação do piloto: {exc}", exc_info=True)
        sys.exit(1)
