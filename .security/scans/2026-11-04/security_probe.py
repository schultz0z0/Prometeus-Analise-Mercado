"""Isolated audit reproduction: in-memory DB, fake config, no external calls."""
import asyncio
import importlib
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.domain.analyses import Analysis, AnalysisRecommendation
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.models import Base, DossierModel, ScoringResultModel
from prometeus.infrastructure.db.session import get_db_session

api = importlib.import_module("prometeus.entrypoints.rest.app")


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    results = {}
    with tempfile.TemporaryDirectory(prefix="prometeus-security-audit-") as directory:
        env_file = Path(directory) / "isolated.env"
        config = SimpleNamespace(
            GEN_LLM_PROVIDER="openai", CHATGPT_CREDENTIALS_PATH=str(Path(directory) / "none.json")
        )
        async with factory() as session:
            analysis = Analysis.create(
                tenant_id="ens", course_name='<img src=x onerror="window.__audit_xss=1">',
                correlation_id="isolated-security-audit",
                proposal_data={"area": "Audit", "level": "Test", "modality": "EAD"},
            )
            await AnalysisRepository(session).save(analysis)
            await session.commit()

            async def isolated_session():
                yield session

            api.app.dependency_overrides[get_db_session] = isolated_session
            try:
                transport = httpx.ASGITransport(app=api.app)
                async with httpx.AsyncClient(transport=transport, base_url="http://isolated") as client:
                    listing = await client.get("/v1/analyses?tenant_id=ens")
                    results["anonymous_list"] = {"status": listing.status_code, "name": listing.json()["items"][0]["name"]}
                    decision = await client.post(f"/v1/analyses/{analysis.id}/decisions", json={
                        "user_id": "forged-director", "user_role": "director", "decision": "APPROVED",
                        "rationale": "Isolated audit proof",
                    })
                    results["anonymous_forged_decision"] = {"status": decision.status_code, "body": decision.json()}
                    analysis.start(correlation_id="audit")
                    analysis.complete(AnalysisRecommendation.INSUFFICIENT_EVIDENCE, correlation_id="audit")
                    await AnalysisRepository(session).save(analysis)
                    session.add(ScoringResultModel(
                        id="audit-score", analysis_id=analysis.id, profile_id="audit",
                        viability_score=0, coverage_score=0, confidence_score=0, partial_score=0,
                        recommendation="INSUFFICIENT_EVIDENCE",
                    ))
                    session.add(DossierModel(
                        id="audit-dossier", analysis_id=analysis.id, prompt_version="audit",
                        model_name="audit-fixture", facts_hash="audit", status="VERIFIED",
                        executive_summary="Fixture isolada: não representa uma geração LLM real.",
                    ))
                    await session.commit()
                    completed = await client.get("/v1/analyses?tenant_id=ens")
                    item = completed.json()["items"][0]
                    results["completed_verified_xss_fixture"] = {
                        "status": completed.status_code,
                        "name": item["name"], "analysis_status": item["status"],
                        "dossier_status": item["dossier"]["status"],
                        "passes_store_filter": item["status"] == "COMPLETED" and item["dossier"]["status"] == "VERIFIED",
                    }
                    Path(__file__).with_name("completed-xss-fixture.json").write_text(
                        json.dumps(completed.json(), ensure_ascii=False), encoding="utf-8"
                    )
                    with patch.object(api, "AppSettings", return_value=config), patch.object(api, "_env_path", return_value=env_file):
                        settings = await client.post("/v1/settings", json={"openai_base_url": "http://127.0.0.1:19999/capture", "apify_max_charge": 99999})
                        results["anonymous_settings_write"] = {"status": settings.status_code, "persisted": env_file.read_text()}
                    spa = await client.get("/")
                    results["spa_csp"] = spa.headers.get("Content-Security-Policy")
            finally:
                api.app.dependency_overrides.clear()
    await engine.dispose()
    output = Path(__file__).with_name("security-probe-output.json")
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output.read_text(encoding="utf-8"))


asyncio.run(main())
