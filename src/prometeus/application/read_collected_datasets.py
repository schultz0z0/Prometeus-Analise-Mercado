"""Persistência retomável da leitura dos datasets completos de uma análise."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.application.integral_evidence_reader import (
    IntegralEvidenceReader,
    IntegralEvidenceReadingError,
)
from prometeus.infrastructure.db.models import AnalysisModel, ToolRunModel

DATASET_READING_VERSION = "dataset-reading-v1"
ExecutionGuard = Callable[[], Awaitable[None]]


def _key(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class DatasetReadingService:
    """Lê arquivos privados higienizados; commits preservam cada parte validada.

    ``complete`` comprova cobertura de entrega/resposta, sem promover a execução
    do Actor nem a suficiência da evidência. Não substitui os gates de análise.
    A sessão deve pertencer ao workflow que possui a análise e sua lease.
    """

    def __init__(self, session: AsyncSession, reader: IntegralEvidenceReader) -> None:
        self.session = session
        self.reader = reader

    async def read(
        self,
        analysis_id: str,
        *,
        course_context: dict[str, Any],
        execution_guard: ExecutionGuard | None = None,
    ) -> dict[str, Any]:
        course_context = deepcopy(course_context)
        if execution_guard:
            await execution_guard()
        if await self.session.get(AnalysisModel, analysis_id) is None:
            raise ValueError("Análise não encontrada para leitura de datasets.")
        runs = list(
            (
                await self.session.scalars(
                    select(ToolRunModel)
                    .where(
                        ToolRunModel.analysis_id == analysis_id,
                    )
                    .order_by(ToolRunModel.id)
                )
            ).all()
        )
        # Freeze scalar metadata before checkpoints can expire ORM attributes.
        snapshots = [
            (
                run,
                {
                    "analysis_id": analysis_id,
                    "tool_run_id": run.id,
                    "provider": run.provider,
                    "capability": run.capability,
                    "actor_id": run.actor_id,
                    "actor_build": run.actor_build,
                    "query": run.query,
                    "run_status": run.status,
                    "run_error_code": run.error_code,
                    "current_provider_run_id": run.provider_run_id,
                    "current_dataset_id": run.dataset_id,
                    "produced_items": run.raw_items_count,
                },
                deepcopy(run.parameters or {}),
            )
            for run in runs
        ]
        files: list[dict[str, Any]] = []
        runs_without_dataset: list[dict[str, Any]] = []
        for run, metadata, parameters in snapshots:
            if execution_guard:
                await execution_guard()
            previous = parameters.get("prior_dataset_archives", [])
            archives = list(previous) if isinstance(previous, list) else [None]
            current = parameters.get("dataset_archive")
            has_remote_output = bool(
                metadata["current_provider_run_id"]
                or metadata["current_dataset_id"]
                or metadata["produced_items"]
            )
            if current is not None:
                archives.append(current)
            elif has_remote_output:
                archives.append(None)
            current_matches_remote = isinstance(current, dict) and all(
                not expected or current.get(field) == expected
                for field, expected in (
                    ("provider_run_id", metadata["current_provider_run_id"]),
                    ("dataset_id", metadata["current_dataset_id"]),
                )
            )
            if has_remote_output and not current_matches_remote and current is not None:
                # A previous capture remains useful, but cannot cover output
                # from a newer remote run that failed before being archived.
                archives.append(None)
            if not archives:
                runs_without_dataset.append({**metadata, "reason": "no_remote_dataset_produced"})
            for archive in archives:
                files.append(
                    await self._read_archive(
                        run,
                        metadata,
                        parameters,
                        archive,
                        course_context=course_context,
                        execution_guard=execution_guard,
                    )
                )
                if archive is None and has_remote_output and not current_matches_remote:
                    files[-1]["issues"].append("current_remote_archive_missing")
        items_total = sum(len(file["items"]) for file in files)
        items_complete = sum(item["complete"] for file in files for item in file["items"])
        return {
            "version": DATASET_READING_VERSION,
            "analysis_id": analysis_id,
            "tool_runs_total": len(snapshots),
            "remote_runs_total": len(files),
            "runs_without_dataset": runs_without_dataset,
            "complete": bool(files) and all(file["complete"] for file in files),
            "files_total": len(files),
            "files_complete": sum(file["complete"] for file in files),
            "files_pending": sum(not file["complete"] for file in files),
            "items_total": items_total,
            "items_complete": items_complete,
            "items_pending": items_total - items_complete,
            "issues": [] if files else ["no_collected_archives"],
            "files": files,
            "coverage_semantics": "All archived sanitized content delivered with validated responses; not proof of evidence sufficiency or successful Actor execution.",
        }

    async def _read_archive(
        self,
        run: ToolRunModel,
        metadata: dict[str, Any],
        parameters: dict[str, Any],
        archive: Any,
        *,
        course_context: dict[str, Any],
        execution_guard: ExecutionGuard | None,
    ) -> dict[str, Any]:
        file: dict[str, Any] = {
            **metadata,
            "provider_run_id": metadata.get("current_provider_run_id"),
            "dataset_id": metadata.get("current_dataset_id"),
            "source_sha256": None,
            "retrieval_complete": False,
            "complete": False,
            "issues": [],
            "items": [],
            "findings": [],
        }
        if not isinstance(archive, dict):
            file["issues"].append("missing_or_invalid_archive")
            return file
        metadata = {
            **metadata,
            "logical_task_status": metadata["run_status"],
            "run_status": archive.get("provider_status") or "UNKNOWN",
        }
        file.update(metadata)
        if type(archive.get("schema_version")) is not int or archive["schema_version"] != 1:
            file["issues"].append("unsupported_archive_schema")
        for field in ("provider_run_id", "dataset_id", "source_sha256"):
            file[field] = archive.get(field)
            if not isinstance(file[field], str) or not file[field]:
                file["issues"].append("invalid_" + field)
        file["retrieval_complete"] = archive.get("retrieval_complete") is True
        file["dataset_total_items"] = archive.get("dataset_total_items")
        file["items_read"] = archive.get("items_read")
        if not file["retrieval_complete"]:
            file["issues"].append("dataset_retrieval_incomplete")
        if archive.get("total_items_source") not in {
            "provider_pagination",
            "terminal_exhaustion",
        }:
            file["issues"].append("dataset_total_unverified")
        records = archive.get("items")
        if not isinstance(records, list):
            file["issues"].append("invalid_archive_items")
            return file
        for field in ("dataset_total_items", "items_read"):
            if not _count(archive.get(field)) or archive[field] != len(records):
                file["issues"].append(field + "_mismatch")
        indices = [record.get("index") if isinstance(record, dict) else None for record in records]
        valid_indices = [
            index for index in indices if isinstance(index, int) and not isinstance(index, bool)
        ]
        if len(valid_indices) != len(indices) or sorted(valid_indices) != list(range(len(records))):
            file["issues"].append("invalid_item_indices")
        for position, record in enumerate(records):
            if execution_guard:
                await execution_guard()
            item: dict[str, Any] = {
                "index": record.get("index") if isinstance(record, dict) else None,
                "position": position,
                "reading_key": None,
                "complete": False,
            }
            file["items"].append(item)
            if not isinstance(record, dict) or "sanitized_data" not in record:
                item["error"] = "missing_sanitized_data"
                continue
            if not isinstance(record.get("source_sha256"), str) or not record["source_sha256"]:
                file["issues"].append("invalid_item_source_sha256")
            source_context = {
                **metadata,
                "provider_run_id": file["provider_run_id"],
                "dataset_id": file["dataset_id"],
                "archive_source_sha256": file["source_sha256"],
                "item_index": item["index"],
                "item_position": position,
                "item_source_sha256": record.get("source_sha256"),
            }
            reading_key = _key(
                {
                    key: value
                    for key, value in source_context.items()
                    if key
                    in {
                        "analysis_id",
                        "tool_run_id",
                        "provider_run_id",
                        "dataset_id",
                        "archive_source_sha256",
                        "item_index",
                        "item_position",
                        "item_source_sha256",
                    }
                }
            )
            item["reading_key"] = reading_key
            stored = parameters.get("dataset_readings", {})
            prior = stored.get(reading_key) if isinstance(stored, dict) else None
            guard_error: Exception | None = None

            async def checkpoint(
                state: dict[str, Any],
                *,
                key: str = reading_key,
                context: dict[str, Any] = source_context,
            ) -> None:
                nonlocal guard_error
                if execution_guard:
                    try:
                        await execution_guard()
                    except Exception as error:
                        guard_error = error
                        raise
                await self._persist(run, parameters, key, state, context)

            try:
                state = await self.reader.read(
                    record["sanitized_data"],
                    course_context=course_context,
                    source_context=source_context,
                    prior=prior,
                    checkpoint=checkpoint,
                )
            except IntegralEvidenceReadingError as error:
                # A lost lease forbids writes; earlier validated checkpoints remain.
                if guard_error is not None:
                    raise guard_error from error
                await checkpoint(error.state)
                raise
            item["complete"] = state["complete"] is True
            item["manifest"] = deepcopy(state["manifest"])
            file["findings"].extend(
                {
                    **deepcopy(finding),
                    **source_context,
                    "reading_key": reading_key,
                }
                for finding in state["findings"]
            )
        file["complete"] = not file["issues"] and all(item["complete"] for item in file["items"])
        return file

    async def _persist(
        self,
        run: ToolRunModel,
        parameters: dict[str, Any],
        reading_key: str,
        state: dict[str, Any],
        source_context: dict[str, Any],
    ) -> None:
        stored = parameters.get("dataset_readings", {})
        readings = deepcopy(stored) if isinstance(stored, dict) else {}
        readings[reading_key] = {**deepcopy(state), "source_context": deepcopy(source_context)}
        parameters["dataset_readings"] = readings
        # Plain JSON columns do not track nested mutations. Assign a new object.
        run.parameters = deepcopy(parameters)
        await self.session.commit()
