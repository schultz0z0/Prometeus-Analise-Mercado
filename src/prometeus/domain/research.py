"""Contratos canônicos para entendimento, planejamento e execução de pesquisa."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ImmutableModel(BaseModel):
    model_config = {"frozen": True}


class CourseUnderstanding(ImmutableModel):
    schema_version: int = 1
    analysis_id: str
    course_title: str
    summary: str = ""
    subject_domains: list[str] = Field(default_factory=list)
    target_audiences: list[str] = Field(default_factory=list)
    learning_outcomes: list[str] = Field(default_factory=list)
    level: str = ""
    modality: str = ""
    geography: str = "Brasil"
    language: str = "pt-BR"
    proposed_price_brl: float | None = None
    duration_months: int | None = None
    supplied_materials: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def snapshot_hash(self) -> str:
        payload = self.model_dump(exclude={"created_at"}, mode="json")
        for key in (
            "subject_domains",
            "target_audiences",
            "learning_outcomes",
            "supplied_materials",
            "uncertainties",
            "hypotheses",
        ):
            payload[key] = sorted(payload[key])
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ResearchQuestion(ImmutableModel):
    id: str = Field(default_factory=lambda: f"question-{uuid.uuid4().hex[:12]}")
    question: str
    evidence_need: str
    priority: int = Field(default=1, ge=1, le=5)


class PlannedToolCall(ImmutableModel):
    id: str = Field(default_factory=lambda: f"call-{uuid.uuid4().hex[:12]}")
    capability: str
    query: str
    required: bool = True
    rationale: str
    max_items: int = Field(default=50, ge=1, le=1000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    question_ids: list[str] = Field(default_factory=list)


class ToolRunStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


class ToolRun(ImmutableModel):
    id: str = Field(default_factory=lambda: f"run-{uuid.uuid4().hex[:12]}")
    planned_call_id: str
    capability: str
    query: str
    required: bool
    provider: str = "apify"
    actor_id: str = ""
    status: ToolRunStatus = ToolRunStatus.PLANNED
    run_id: str | None = None
    dataset_id: str | None = None
    raw_items_count: int = 0
    valid_items_count: int = 0
    cost_usd: float = 0.0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def from_call(
        cls,
        call: PlannedToolCall,
        provider: str = "apify",
        actor_id: str = "",
    ) -> ToolRun:
        return cls(
            planned_call_id=call.id,
            capability=call.capability,
            query=call.query,
            required=call.required,
            provider=provider,
            actor_id=actor_id,
            status=ToolRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

    def finish_success(
        self,
        *,
        run_id: str,
        dataset_id: str,
        raw_items_count: int,
        valid_items_count: int,
        cost_usd: float,
    ) -> ToolRun:
        return self.model_copy(
            update={
                "status": ToolRunStatus.SUCCEEDED,
                "run_id": run_id,
                "dataset_id": dataset_id,
                "raw_items_count": raw_items_count,
                "valid_items_count": valid_items_count,
                "cost_usd": round(cost_usd, 4),
                "finished_at": datetime.now(UTC),
            }
        )

    def finish_empty(self, *, run_id: str | None = None, dataset_id: str | None = None) -> ToolRun:
        return self.model_copy(
            update={
                "status": ToolRunStatus.EMPTY,
                "run_id": run_id,
                "dataset_id": dataset_id,
                "finished_at": datetime.now(UTC),
            }
        )

    def finish_failed(self, message: str, *, code: str = "provider_error") -> ToolRun:
        return self.model_copy(
            update={
                "status": ToolRunStatus.FAILED,
                "error_code": code,
                "error_message": message,
                "finished_at": datetime.now(UTC),
            }
        )


class CourseResearchPlan(ImmutableModel):
    schema_version: int = 1
    id: str = Field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:12]}")
    analysis_id: str
    understanding_hash: str
    questions: list[ResearchQuestion] = Field(default_factory=list)
    tool_calls: list[PlannedToolCall] = Field(default_factory=list)
    budget_limit_usd: float = Field(default=5.0, ge=0.0)
    skill_snapshots: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_unique_ids(self) -> CourseResearchPlan:
        call_ids = [call.id for call in self.tool_calls]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("planned tool call ids must be unique")
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("research question ids must be unique")
        return self

    @property
    def snapshot_hash(self) -> str:
        payload = self.model_dump(exclude={"created_at"}, mode="json")
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def blocking_failures(self, runs: list[ToolRun]) -> list[str]:
        by_call = {run.planned_call_id: run for run in runs}
        blocking: list[str] = []
        for call in self.tool_calls:
            if not call.required:
                continue
            run = by_call.get(call.id)
            if run is None or run.status in {ToolRunStatus.FAILED, ToolRunStatus.EMPTY}:
                blocking.append(call.id)
        return blocking

    def has_sufficient_required_evidence(self, runs: list[ToolRun]) -> bool:
        if self.blocking_failures(runs):
            return False
        by_call = {run.planned_call_id: run for run in runs}
        return all(
            by_call.get(call.id) is not None
            and by_call[call.id].status == ToolRunStatus.SUCCEEDED
            and by_call[call.id].valid_items_count > 0
            for call in self.tool_calls
            if call.required
        )
