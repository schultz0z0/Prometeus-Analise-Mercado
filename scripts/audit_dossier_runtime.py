"""Auditoria opt-in com LLM real e fatos persistidos, sem publicar nem refazer coleta.

Executar no worker com --live e --analysis-id; artefatos ficam em var/diagnostics.
"""

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.decision_service import DecisionService
from prometeus.application.synthesize_dossier import (
    DossierSynthesisService,
    DossierVerificationError,
)
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.factory import get_decision_model, get_generative_model


async def audit(analysis_id: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    settings = AppSettings()
    engine = create_async_engine(settings.DATABASE_URL)
    llm = get_generative_model(settings)
    decisions = DecisionService(get_decision_model(settings), session=None)
    async with async_sessionmaker(engine)() as db:
        service = DossierSynthesisService(db, llm, decisions=decisions)
        facts = await service.build_facts(analysis_id)
        (output / "facts.json").write_text(
            json.dumps(asdict(facts), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        draft = await llm.synthesize_dossier(facts)
        reports = []
        for attempt in (1, 2):
            print(f"GENERATION {attempt}: {len(draft.claims)} claims", flush=True)
            (output / f"draft-{attempt}.json").write_text(
                draft.model_dump_json(indent=2), encoding="utf-8"
            )
            try:
                verified = await service._verify_generated_dossier(draft, facts)
            except DossierVerificationError as exc:
                report = {**(exc.report or {}), "attempt": attempt}
                reports.append(report)
                (output / f"verification-{attempt}.json").write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(
                    f"REJECTED {attempt}: gate={report.get('gate')}, issues={len(report.get('issues', []))}",
                    flush=True,
                )
                if attempt == 2 or not exc.can_revise:
                    (output / "result.json").write_text(
                        json.dumps(
                            {"status": "REJECTED", "reports": reports}, ensure_ascii=False, indent=2
                        ),
                        encoding="utf-8",
                    )
                    return
                draft = await llm.revise_dossier(facts, draft, report)
            else:
                (output / "verified.json").write_text(
                    verified.model_dump_json(indent=2), encoding="utf-8"
                )
                (output / "result.json").write_text(
                    json.dumps(
                        {
                            "status": "VERIFIED",
                            "attempt_count": attempt,
                            "model": verified.model_name,
                            "facts_hash": facts.compute_facts_hash(),
                            "reports": reports,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print(f"VERIFIED in {attempt} generation(s); no publication", flush=True)
                return
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(audit(args.analysis_id, args.output))
