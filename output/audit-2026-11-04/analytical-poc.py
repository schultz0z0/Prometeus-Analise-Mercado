"""Read-only local reproduction of the dossier presentation audit findings.

Run from the repository root with .venv/Scripts/python.exe. No external calls,
credentials, database connection, or application mutations are used.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.dossiers import DossierFacts, DossierOutput


def main() -> None:
    facts = DossierFacts(
        analysis_id="local-audit-only",
        course_name="Python para iniciantes",
        target_audience="Estudantes iniciantes",
        recommendation="INSUFFICIENT_EVIDENCE",
        viability_score=0,
        coverage_score=0,
        confidence_score=0,
    )
    dossier = DossierOutput(
        analysis_id=facts.analysis_id,
        executive_summary="Evidencia insuficiente para concluir.",
        facts_hash=facts.compute_facts_hash(),
    )
    scoring = SimpleNamespace(
        viability_score=0,
        recommendation="INSUFFICIENT_EVIDENCE",
        confidence_score=0,
    )
    cases = {
        "missing_financial_inputs": {},
        "negative_contribution": {
            "ticket": 100,
            "fixed_costs": 15000,
            "variable_cost_per_student": 452.5,
            "max_capacity": 30,
        },
        "break_even_above_capacity": {
            "ticket": 2400,
            "fixed_costs": 100000,
            "variable_cost_per_student": 452.5,
            "max_capacity": 30,
        },
    }
    outputs = {}
    for name, proposal in cases.items():
        analysis = SimpleNamespace(course_name=facts.course_name, proposal_data=proposal)
        presentation = DossierSynthesisService._build_visual_presentation_blocks(
            analysis, scoring, facts, dossier
        )
        outputs[name] = {
            "input_proposal": proposal,
            "input_fact_count": len(facts.items),
            "recommendation": facts.recommendation,
            "kpis": presentation["kpis"],
            "economics": presentation["economics"],
            "personas": presentation["personas"],
            "swot": presentation["swot"],
            "curriculum_modules": presentation["curriculum_modules"],
        }
    output_path = Path(__file__).with_suffix(".json")
    output_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        name: {
            "ticket": result["economics"]["ticket"],
            "break_even": result["economics"]["break_even_students"],
            "base": result["economics"]["scenarios"][1],
            "personas": [p["role"] for p in result["personas"]],
            "opportunities": result["swot"]["opportunities"],
        }
        for name, result in outputs.items()
    }, indent=2, ensure_ascii=True))
    print(f"Artifact: {output_path.resolve()}")


if __name__ == "__main__":
    main()
