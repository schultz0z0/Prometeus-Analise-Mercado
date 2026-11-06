import pytest
from pydantic import ValidationError

from prometeus.domain.research import CourseResearchPlan


def test_monitoring_policy_has_no_monetary_cap_and_four_total_attempts():
    from prometeus.domain.collection_execution import CollectionExecutionPolicy

    policy = CollectionExecutionPolicy()
    assert policy.spending_mode == "monitor_only"
    assert policy.max_retries == 3
    assert policy.max_attempts == 4
    plan = CourseResearchPlan(
        analysis_id="ens-analysis",
        understanding_hash="hash",
        budget_limit_usd=None,
        execution_policy=policy,
    )
    assert plan.budget_limit_usd is None
    assert plan.execution_policy == policy


def test_legacy_plan_does_not_gain_new_authorization_policy():
    plan = CourseResearchPlan.model_validate(
        {
            "analysis_id": "legacy",
            "understanding_hash": "hash",
            "budget_limit_usd": 5,
        }
    )
    assert plan.execution_policy is None
    assert plan.budget_limit_usd == 5


def test_recovery_policy_cannot_authorize_a_fourth_retry():
    from prometeus.domain.collection_execution import CollectionExecutionPolicy

    with pytest.raises(ValidationError):
        CollectionExecutionPolicy(max_retries=4)


def test_task_identity_survives_new_plan_ids_and_query_whitespace():
    from prometeus.domain.collection_execution import collection_task_key
    from prometeus.domain.research import PlannedToolCall

    a = PlannedToolCall(
        id="first",
        capability="google_search",
        query=" Curso   IA ",
        rationale="discovery",
        parameters={"competitor_id": "fgv"},
    )
    b = a.model_copy(update={"id": "repair", "query": "curso ia"})
    assert collection_task_key(a) == collection_task_key(b)
    assert collection_task_key(a) != collection_task_key(
        b.model_copy(update={"parameters": {"competitor_id": "insper"}})
    )


def test_task_identity_preserves_geography_language_and_time_scope():
    from prometeus.domain.collection_execution import collection_task_key
    from prometeus.domain.research import PlannedToolCall

    call = PlannedToolCall(capability="google_search", query="curso ia", rationale="test", parameters={"country": "BR", "language": "pt", "time_range": "month"})
    for scope in ({"country": "US"}, {"language": "en"}, {"time_range": "year"}):
        changed = call.model_copy(update={"parameters": {**call.parameters, **scope}})
        assert collection_task_key(call) != collection_task_key(changed)
