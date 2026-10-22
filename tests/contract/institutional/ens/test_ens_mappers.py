import json
from pathlib import Path

from prometeus.infrastructure.institutional.ens.mappers import (
    consolidate_funnel_metrics,
    map_ens_course,
    map_ens_inscritos,
    map_ens_leads,
    map_ens_matriculados,
    sanitize_raw_record,
)

FIXTURES_DIR = Path("tests/fixtures/institutional")


def test_sanitize_raw_record_removes_pii() -> None:
    raw = {
        "codigo_curso": "ENS-01",
        "nome_curso": "Gestão de Riscos",
        "nome_aluno": "João da Silva",
        "cpf": "123.456.789-00",
        "email": "joao@example.com",
        "telefone": "(11) 99999-9999",
        "total_leads": 150,
    }
    clean = sanitize_raw_record(raw)
    assert "codigo_curso" in clean
    assert "nome_curso" in clean
    assert "total_leads" in clean

    # PII estritamente descartada
    assert "nome_aluno" not in clean
    assert "cpf" not in clean
    assert "email" not in clean
    assert "telefone" not in clean


def test_map_ens_course() -> None:
    raw = {
        "codigo_curso": "ENS-SEG-01",
        "nome_curso": "MBA em Gestão de Seguros",
        "categoria": "Pós-graduação Lato Sensu",
        "modalidade": "ONLINE",
        "carga_horaria": "360",
    }
    course = map_ens_course(raw)
    assert course.external_id == "ENS-SEG-01"
    assert course.name == "MBA em Gestão de Seguros"
    assert course.modality == "online"
    assert course.workload_hours == 360
    assert course.status == "active"


def test_map_ens_leads_from_fixtures() -> None:
    fixture_path = FIXTURES_DIR / "ens_leads_page1.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))["data"]

    leads_map = map_ens_leads(data)
    assert leads_map[("ENS-SEG-01", "2025-1")] == 1400
    assert leads_map[("ENS-SEG-02", "2025-1")] == 850


def test_consolidate_funnel_metrics_and_quality_score() -> None:
    leads_raw = json.loads((FIXTURES_DIR / "ens_leads_page1.json").read_text(encoding="utf-8"))[
        "data"
    ]
    inscritos_raw = json.loads((FIXTURES_DIR / "ens_inscritos.json").read_text(encoding="utf-8"))[
        "items"
    ]
    matriculados_raw = json.loads(
        (FIXTURES_DIR / "ens_matriculados.json").read_text(encoding="utf-8")
    )["registros"]

    leads_map = map_ens_leads(leads_raw)
    inscritos_map = map_ens_inscritos(inscritos_raw)
    matriculados_map, financial_map = map_ens_matriculados(matriculados_raw)

    metrics, quality_score, warnings = consolidate_funnel_metrics(
        course_ids=["ENS-SEG-01"],
        leads_map=leads_map,
        inscritos_map=inscritos_map,
        matriculados_map=matriculados_map,
        period="2025-1",
    )

    assert len(metrics) == 1
    m1 = metrics[0]
    assert m1.external_course_id == "ENS-SEG-01"
    assert m1.leads == 1400
    assert m1.applicants == 280
    assert m1.enrolled == 98
    assert m1.conversion_lead_to_applicant == 0.20
    assert m1.conversion_applicant_to_enrolled == 0.35
    assert m1.conversion_lead_to_enrolled == 0.07

    # Dados consistentes têm score máximo
    assert quality_score == 1.0
    assert len(warnings) == 0


def test_consolidate_funnel_metrics_anomaly_detection() -> None:
    # Simula anomalia: mais matriculados do que inscritos
    leads_map = {("ENS-ERR", "2025-1"): 100}
    inscritos_map = {("ENS-ERR", "2025-1"): 10}
    matriculados_map = {("ENS-ERR", "2025-1"): 20}  # Anomalia: 20 > 10

    metrics, quality_score, warnings = consolidate_funnel_metrics(
        course_ids=["ENS-ERR"],
        leads_map=leads_map,
        inscritos_map=inscritos_map,
        matriculados_map=matriculados_map,
        period="2025-1",
    )

    assert quality_score < 1.0
    assert len(warnings) == 1
    assert "matriculados (20) > inscritos (10)" in warnings[0]
