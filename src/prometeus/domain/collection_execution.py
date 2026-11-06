"""Política explícita de coleta e identidade estável de tarefas lógicas."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from prometeus.domain.research import PlannedToolCall


class CollectionExecutionPolicy(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    policy_version: Literal["collection-v2"] = "collection-v2"
    spending_mode: Literal["monitor_only"] = "monitor_only"
    max_retries: int = Field(default=3, ge=0, le=3)

    @property
    def max_attempts(self) -> int:
        return 1 + self.max_retries


def collection_task_key(call: PlannedToolCall) -> str:
    """Não inclui plano/ID local: repetir a mesma tarefa não renova suas tentativas."""
    target = call.parameters.get("competitor_id") or call.parameters.get("competitor_ids")
    payload = {
        "capability": call.capability,
        "target": target,
        "query": " ".join(call.query.casefold().split()),
        "urls": sorted(call.parameters.get("urls") or []),
        "scope": {key: call.parameters[key] for key in (
            "country", "language", "geo", "location", "time_range", "time_window",
            "date_posted", "start_date", "end_date", "target_domains",
        ) if key in call.parameters},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
