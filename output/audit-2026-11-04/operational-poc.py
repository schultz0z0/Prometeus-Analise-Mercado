"""Reproducoes isoladas de auditoria. Somente fixtures, SQLite e arquivos temporarios."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from prometeus.application.create_analysis import CreateAnalysisCommand, CreateAnalysisUseCase
from prometeus.application.decision_service import DecisionService
from prometeus.application.keywords import KeywordPipeline
from prometeus.domain.analyses import Analysis
from prometeus.domain.configuration import AppSettings
from prometeus.infrastructure.db.analysis_repository import AnalysisRepository
from prometeus.infrastructure.db.backup import TABLE_MODELS, BackupRestoreManager
from prometeus.infrastructure.db.models import Base, ExecutionEnvelopeModel, ScoringResultModel
from prometeus.infrastructure.jev.fake_client import FakeDecisionClient
from scripts.evaluate_jev import BenchmarkEvaluationModel


async def engine_and_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def keyword_poc():
    engine, factory = await engine_and_factory()
    async def candidates(**kwargs):
        return [f"seguros {i}" for i in range(15)]
    async with factory() as session:
        service = DecisionService(FakeDecisionClient(), session=session)
        result = await KeywordPipeline(SimpleNamespace(generate_keyword_candidates=candidates), service).build_keyword_set("Seguros", "Seguros", "Profissionais")
        await session.commit()
        rows = (await session.execute(select(ExecutionEnvelopeModel))).scalars().all()
        output = {
            "provider_behavior": "HIGH_RELEVANCE para todos os 15 termos, sem falhas",
            "judged": Counter(candidate.relevance for candidate in result.evaluated_candidates),
            "unnecessarily_rejected": [candidate.term for candidate in result.evaluated_candidates if candidate.relevance == "IRRELEVANT"],
            "db_envelopes": len(rows),
            "envelopes_without_analysis": sum(row.analysis_id is None for row in rows),
        }
    await engine.dispose()
    return output


async def backup_poc():
    source, source_factory = await engine_and_factory()
    target, target_factory = await engine_and_factory()
    with tempfile.TemporaryDirectory(prefix="prometeus-audit-backup-") as directory:
        backup_file = Path(directory) / "dummy-backup.json"
        async with source_factory() as session:
            analysis = Analysis.create(tenant_id="ens", course_name="AUDIT FIXTURE", correlation_id="audit")
            await AnalysisRepository(session).save(analysis)
            session.add(ScoringResultModel(id="audit-score", analysis_id=analysis.id, profile_id="portfolio-v2", viability_score=75, coverage_score=80, confidence_score=.8, partial_score=60, recommendation="REQUIRES_HUMAN_REVIEW"))
            await session.commit()
            manifest = await BackupRestoreManager(session).create_backup(backup_file)
        async with target_factory() as session:
            restored = await BackupRestoreManager(session).restore_backup(backup_file)
            score_count = await session.scalar(select(func.count()).select_from(ScoringResultModel))
        output = {
            "source_scores": 1,
            "restored_scores": score_count,
            "restore_status": restored["status"],
            "manifest_tables": sorted(manifest.table_counts),
            "omitted_tables": sorted(set(Base.metadata.tables) - {name for name, _ in TABLE_MODELS}),
        }
    await source.dispose()
    await target.dispose()
    return output


async def idempotency_poc():
    engine, factory = await engine_and_factory()
    settings = AppSettings(_env_file=None, APP_ENV="test", SCORING_PROFILE_PATH="config/scoring/portfolio-v2.yaml")
    async with factory() as session:
        use_case = CreateAnalysisUseCase(session, settings)
        first = await use_case.execute(CreateAnalysisCommand(tenant_id="ens", course_name="ENS FIXTURE", proposal_data={}, idempotency_key="same-key", correlation_id="audit"))
        await session.commit()
        second = await use_case.execute(CreateAnalysisCommand(tenant_id="infnet", course_name="INFNET FIXTURE", proposal_data={}, idempotency_key="same-key", correlation_id="audit"))
        row = await AnalysisRepository(session).get_by_id(second.analysis_id)
        output = {"requested_tenant": "infnet", "returned_tenant": row.tenant_id, "same_analysis_as_ens": first.analysis_id == second.analysis_id, "second_is_existing": second.is_existing}
    await engine.dispose()
    return output


async def benchmark_poc():
    service = DecisionService(BenchmarkEvaluationModel())
    pack = service.get_pack("keywords-relevance-v1")
    results = []
    for expected in pack.options:
        # Mesmo input sem conteudo semantico: so a resposta esperada varia.
        result = await service.execute_judgment(pack.pack_id, {"course_title": "", "search_term": "", "_expected": expected})
        results.append({"expected_injected": expected, "returned": result.selected_choice})
    return {"provider": "BenchmarkEvaluationModel (sem chamada JEV)", "identical_blank_input_different_labels": results}


async def main():
    result = {}
    for name, check in [("keyword_concurrent_session", keyword_poc), ("backup_loses_scoring", backup_poc), ("idempotency_cross_tenant", idempotency_poc), ("evaluation_target_leakage", benchmark_poc)]:
        try:
            result[name] = await check()
        except Exception as error:
            result[name] = {"poc_error": type(error).__name__, "detail": str(error)}
    destination = Path(__file__).with_name("operational-poc.json")
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
