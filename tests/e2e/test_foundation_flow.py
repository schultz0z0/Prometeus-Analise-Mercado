from collections.abc import AsyncGeneratorfrom typing import Anyimport pytestfrom sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_enginefrom prometeus.domain.analyses import Analysisfrom prometeus.domain.configuration import AppSettingsfrom prometeus.infrastructure.db.analysis_repository import AnalysisRepositoryfrom prometeus.infrastructure.db.models import Basefrom prometeus.workers.tasks import WORKFLOW_STEPS, execute_workflow_steps@pytest.fixture
async def e2e_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_is_a_thin_adapter_for_the_fifteen_step_use_case(
    e2e_session: AsyncSession,
) -> None:
    calls: list[tuple[str, str]] = []

    class StubUseCase:
        async def execute(self, analysis_id: str, correlation_id: str) -> Any:
            calls.append((analysis_id, correlation_id))

    assert len(WORKFLOW_STEPS) == 15
    assert [number for number, _ in WORKFLOW_STEPS] == list(range(1, 16))

    await execute_workflow_steps(
        analysis_id="analysis-1",
        correlation_id="correlation-1",
        repository=AnalysisRepository(e2e_session),
        use_case=StubUseCase(),  # type: ignore[arg-type]
    )

    assert calls == [("analysis-1", "correlation-1")]


@pytest.mark.asyncio
async def test_worker_blocks_before_external_cost_when_runtime_preflight_fails(
    e2e_session: AsyncSession,
) -> None:
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="Curso sem credencial válida",
        correlation_id="correlation-preflight",
    )
    repository = AnalysisRepository(e2e_session)
    await repository.save(analysis)
    await e2e_session.commit()

    await execute_workflow_steps(
        analysis_id=analysis.id,
        correlation_id="correlation-preflight",
        repository=repository,
        runtime_settings=AppSettings(
            _env_file=None,
            AI_MODE="traditional",
            GEN_LLM_PROVIDER="chatgpt_oauth",
            CHATGPT_ACCESS_TOKEN="not-an-api-key",
            OPENAI_API_KEY="",
            APIFY_REQUIRED_SOURCES="",
            CHATGPT_CREDENTIALS_PATH="var/test-non-existent-creds.json",
        ),
    )

    persisted = await repository.get_by_id(analysis.id)
    assert persisted is not None
    assert persisted.status.value == "BLOCKED"
    assert "llm_credentials_missing" in (persisted.audit_events[-1].reason or "")
