import pytest

from prometeus.domain.analyses import (
    Analysis,
    AnalysisRecommendation,
    AnalysisStatus,
    InvalidRecommendationError,
    InvalidStateTransitionError,
)


def test_initial_state_is_queued_with_null_recommendation() -> None:
    analysis = Analysis.create(
        tenant_id="ens",
        course_name="MBA em Gestão de Seguros",
        correlation_id="corr-123",
    )
    assert analysis.status == AnalysisStatus.QUEUED
    assert analysis.recommendation is None
    assert analysis.tenant_id == "ens"
    assert analysis.course_name == "MBA em Gestão de Seguros"
    assert len(analysis.audit_events) == 1
    initial_event = analysis.audit_events[0]
    assert initial_event.from_status is None
    assert initial_event.to_status == AnalysisStatus.QUEUED
    assert initial_event.correlation_id == "corr-123"


def test_allowed_transitions_from_queued() -> None:
    # QUEUED -> RUNNING
    a1 = Analysis.create(tenant_id="ens", course_name="Curso A", correlation_id="c1")
    a1.start(reason="Worker picked up job", correlation_id="c2")
    assert a1.status == AnalysisStatus.RUNNING
    assert a1.recommendation is None
    assert len(a1.audit_events) == 2
    assert a1.audit_events[-1].from_status == AnalysisStatus.QUEUED
    assert a1.audit_events[-1].to_status == AnalysisStatus.RUNNING

    # QUEUED -> CANCELLED
    a2 = Analysis.create(tenant_id="ens", course_name="Curso B", correlation_id="c3")
    a2.cancel(reason="User cancelled before execution", correlation_id="c4")
    assert a2.status == AnalysisStatus.CANCELLED
    assert a2.is_terminal is True


def test_invalid_transitions_from_queued() -> None:
    a = Analysis.create(tenant_id="ens", course_name="Curso C", correlation_id="c1")

    # Cannot jump directly to COMPLETED, BLOCKED, WAITING_FOR_INPUT, FAILED
    with pytest.raises(InvalidStateTransitionError):
        a.complete(recommendation=AnalysisRecommendation.APPROVED, correlation_id="c2")

    with pytest.raises(InvalidStateTransitionError):
        a.block(reason="Missing JEV", correlation_id="c2")

    with pytest.raises(InvalidStateTransitionError):
        a.wait_for_input(reason="Chatbot needs syllabus", correlation_id="c2")

    with pytest.raises(InvalidStateTransitionError):
        a.fail(reason="Unexpected crash", correlation_id="c2")


def test_allowed_transitions_from_running() -> None:
    # RUNNING -> WAITING_FOR_INPUT -> RUNNING
    a = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="c1")
    a.start(correlation_id="c2")
    a.wait_for_input(reason="Awaiting target audience clarification", correlation_id="c3")
    assert a.status == AnalysisStatus.WAITING_FOR_INPUT
    a.resume(reason="Audience provided", correlation_id="c4")
    assert a.status == AnalysisStatus.RUNNING

    # RUNNING -> BLOCKED -> RUNNING
    a.block(reason="JEV dependency temporarily unavailable", correlation_id="c5")
    assert a.status == AnalysisStatus.BLOCKED
    a.resume(reason="JEV recovered", correlation_id="c6")
    assert a.status == AnalysisStatus.RUNNING

    # RUNNING -> COMPLETED with recommendation
    a.complete(
        recommendation=AnalysisRecommendation.APPROVED_WITH_ADJUSTMENTS,
        correlation_id="c7",
        reason="Dossier finalized",
    )
    assert a.status == AnalysisStatus.COMPLETED
    assert a.recommendation == AnalysisRecommendation.APPROVED_WITH_ADJUSTMENTS
    assert a.is_terminal is True


def test_blocked_can_fail_or_cancel() -> None:
    a1 = Analysis.create(tenant_id="ens", course_name="Curso 1", correlation_id="c1")
    a1.start(correlation_id="c2")
    a1.block(reason="Timeout waiting for JEV", correlation_id="c3")
    a1.fail(reason="Max retries exceeded for JEV", correlation_id="c4")
    assert a1.status == AnalysisStatus.FAILED
    assert a1.is_terminal is True

    a2 = Analysis.create(tenant_id="ens", course_name="Curso 2", correlation_id="c5")
    a2.start(correlation_id="c6")
    a2.block(reason="Quota exhausted", correlation_id="c7")
    a2.cancel(reason="Tenant cancelled blocked analysis", correlation_id="c8")
    assert a2.status == AnalysisStatus.CANCELLED
    assert a2.is_terminal is True


def test_terminal_states_cannot_transition() -> None:
    # COMPLETED is terminal
    a_comp = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="c1")
    a_comp.start(correlation_id="c2")
    a_comp.complete(recommendation=AnalysisRecommendation.APPROVED, correlation_id="c3")

    with pytest.raises(InvalidStateTransitionError):
        a_comp.start(correlation_id="c4")
    with pytest.raises(InvalidStateTransitionError):
        a_comp.cancel(correlation_id="c5")
    with pytest.raises(InvalidStateTransitionError):
        a_comp.fail(correlation_id="c6")

    # FAILED is terminal
    a_fail = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="c1")
    a_fail.start(correlation_id="c2")
    a_fail.fail(reason="Network crash", correlation_id="c3")

    with pytest.raises(InvalidStateTransitionError):
        a_fail.resume(correlation_id="c4")

    # CANCELLED is terminal
    a_canc = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="c1")
    a_canc.cancel(correlation_id="c2")

    with pytest.raises(InvalidStateTransitionError):
        a_canc.start(correlation_id="c3")


def test_recommendation_must_be_none_unless_completed() -> None:
    a = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="c1")
    assert a.recommendation is None

    # Cannot set recommendation while QUEUED
    with pytest.raises(InvalidRecommendationError):
        a.set_recommendation(AnalysisRecommendation.APPROVED)

    a.start(correlation_id="c2")
    # Cannot set recommendation while RUNNING
    with pytest.raises(InvalidRecommendationError):
        a.set_recommendation(AnalysisRecommendation.APPROVED)

    # Must provide recommendation when completing
    with pytest.raises(InvalidRecommendationError):
        a.complete(recommendation=None, correlation_id="c3")  # type: ignore[arg-type]


def test_audit_event_structure_and_order() -> None:
    a = Analysis.create(tenant_id="ens", course_name="Curso", correlation_id="req-1")
    a.start(reason="Worker started", correlation_id="req-2")
    a.fail(reason="Critical failure", correlation_id="req-3")

    events = a.audit_events
    assert len(events) == 3
    assert events[0].to_status == AnalysisStatus.QUEUED
    assert events[1].from_status == AnalysisStatus.QUEUED
    assert events[1].to_status == AnalysisStatus.RUNNING
    assert events[1].reason == "Worker started"
    assert events[1].correlation_id == "req-2"
    assert events[2].from_status == AnalysisStatus.RUNNING
    assert events[2].to_status == AnalysisStatus.FAILED
    assert events[2].reason == "Critical failure"
    assert events[2].correlation_id == "req-3"
