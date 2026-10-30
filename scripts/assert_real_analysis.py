"""Aceitação de análise real concluída; somente leitura, sem inferência ou coleta."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.dossier_verifier import DossierVerifier
from prometeus.application.synthesize_dossier import DossierSynthesisService
from prometeus.domain.configuration import AppSettings
from prometeus.domain.dossiers import DossierOutput
from prometeus.infrastructure.factory import get_generative_model


async def verify(analysis_id: str, base_url: str, output: Path) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=20) as client:
        response = await client.get(f"/v1/analyses/{analysis_id}")
        response.raise_for_status()
        analysis = response.json()
        response = await client.get(f"/v1/analyses/{analysis_id}/dossier")
        response.raise_for_status()
        dossier = response.json()
    assert analysis["status"] == "COMPLETED", analysis.get("blocking")
    assert [(s["step_number"], s["status"]) for s in analysis["steps"]] == [
        (n, "COMPLETED") for n in range(1, 16)
    ]
    assert dossier["status"] == "VERIFIED"
    assert dossier["model_name"] != "fake-gpt-4o"
    settings = AppSettings()
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with async_sessionmaker(engine)() as db:
            facts = await DossierSynthesisService(db, get_generative_model(settings)).build_facts(
                analysis_id
            )
            document = DossierOutput.model_validate(
                {
                    k: v
                    for k, v in dossier.items()
                    if k not in {"scoring", "evidences", "analysis_audit", "limitations"}
                }
            )
            assert dossier["facts_hash"] == facts.compute_facts_hash()
            assert DossierVerifier().verify(document, facts).status == "VERIFIED"
            assert all(
                c.verification_status == "verified" and c.evidence_ids for c in document.claims
            )
            assert all(e["collector"].startswith("apify:") for e in dossier["evidences"])
            assert any("sintétic" in limitation for limitation in dossier["limitations"])
    finally:
        await engine.dispose()
    result = {
        "analysis_id": analysis_id,
        "dossier_id": dossier["id"],
        "status": analysis["status"],
        "checkpoints": len(analysis["steps"]),
        "claims": len(dossier["claims"]),
        "recommendation": dossier["scoring"]["recommendation"],
        "score": dossier["scoring"]["viability_score"],
        "coverage": dossier["scoring"]["coverage_score"],
        "confidence": dossier["scoring"]["confidence_score"],
        "model": dossier["model_name"],
        "facts_hash": dossier["facts_hash"],
        "tool_runs": len(analysis["tool_runs"]),
        "evidences": len(dossier["evidences"]),
        "checks": "all passed: state, checkpoints, references, hash, deterministic verification and provenance",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--base-url", default="http://api:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.analysis_id, args.base_url, args.output))
