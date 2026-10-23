from prometeus.domain.research import (
    CourseResearchPlan,
    CourseUnderstanding,
    PlannedToolCall,
    ResearchQuestion,
    ToolRun,
    ToolRunStatus,
)


def test_course_understanding_hash_is_stable_for_equivalent_payloads() -> None:
    first = CourseUnderstanding(
        analysis_id="anl-1",
        course_title="MBA em IA para Seguros",
        subject_domains=["seguros", "inteligência artificial"],
        target_audiences=["gestores de seguradoras"],
        learning_outcomes=["avaliar riscos com IA"],
        geography="Brasil",
    )
    second = CourseUnderstanding(
        analysis_id="anl-1",
        course_title="MBA em IA para Seguros",
        subject_domains=["inteligência artificial", "seguros"],
        target_audiences=["gestores de seguradoras"],
        learning_outcomes=["avaliar riscos com IA"],
        geography="Brasil",
    )

    assert first.snapshot_hash == second.snapshot_hash


def test_research_plan_requires_unique_calls_and_can_report_blocking_failures() -> None:
    plan = CourseResearchPlan(
        analysis_id="anl-1",
        understanding_hash="abc123",
        questions=[
            ResearchQuestion(
                id="q-demand",
                question="Existe demanda de busca atual?",
                evidence_need="search demand",
            )
        ],
        tool_calls=[
            PlannedToolCall(
                id="call-google",
                capability="google_search",
                query="MBA inteligência artificial seguros",
                required=True,
                rationale="Mapear demanda e ofertas concorrentes",
            ),
            PlannedToolCall(
                id="call-social",
                capability="instagram",
                query="curso inteligência artificial seguros",
                required=False,
                rationale="Coletar voz social complementar",
            ),
        ],
        budget_limit_usd=5.0,
    )
    runs = [
        ToolRun.from_call(plan.tool_calls[0]).finish_failed("timeout"),
        ToolRun.from_call(plan.tool_calls[1]).finish_empty(),
    ]

    assert plan.blocking_failures(runs) == ["call-google"]
    assert plan.has_sufficient_required_evidence(runs) is False


def test_successful_tool_run_preserves_provider_provenance() -> None:
    call = PlannedToolCall(
        id="call-jobs",
        capability="linkedin_jobs",
        query="atuário inteligência artificial",
        required=True,
        rationale="Medir demanda ocupacional",
        max_items=50,
    )
    run = ToolRun.from_call(call, provider="apify", actor_id="owner/jobs@1.2.3")
    completed = run.finish_success(
        run_id="run-123",
        dataset_id="dataset-456",
        raw_items_count=42,
        valid_items_count=37,
        cost_usd=0.17,
    )

    assert completed.status == ToolRunStatus.SUCCEEDED
    assert completed.run_id == "run-123"
    assert completed.dataset_id == "dataset-456"
    assert completed.valid_items_count == 37
    assert completed.cost_usd == 0.17

