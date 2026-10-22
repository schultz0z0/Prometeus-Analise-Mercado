"""Modelos de domínio e utilitários criptográficos para Webhooks (Fase 07)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class WebhookEventType(StrEnum):
    """Tipos de eventos emitidos via webhook pelo Prometeus."""

    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    ANALYSIS_BLOCKED = "analysis.blocked"
    ANALYSIS_REVIEW_REQUIRED = "analysis.review_required"


class WebhookDeliveryStatus(StrEnum):
    """Estado de entrega do webhook."""

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    SHADOW_DELIVERED = "SHADOW_DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class WebhookEvent:
    """Evento canônico empacotado para envio a endpoints externos de webhook."""

    event_id: str
    event_type: WebhookEventType
    analysis_id: str
    tenant_id: str
    timestamp: int
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        event_type: WebhookEventType,
        analysis_id: str,
        tenant_id: str,
        payload: dict[str, Any],
        event_id: str | None = None,
    ) -> WebhookEvent:
        return cls(
            event_id=event_id or f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            analysis_id=analysis_id,
            tenant_id=tenant_id,
            timestamp=int(time.time()),
            payload=payload,
        )

    def to_json(self) -> str:
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "analysis_id": self.analysis_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
        return json.dumps(data, ensure_ascii=False, sort_keys=True)


def compute_webhook_signature(secret: str, timestamp: int, body: str) -> str:
    """Calcula a assinatura HMAC-SHA256 no formato padrão Prometeus (t={timestamp}.{body})."""
    message = f"t={timestamp}.{body}"
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_webhook_signature(
    secret: str,
    signature_header: str,
    timestamp_header: str | int,
    body: str,
    max_drift_seconds: int = 300,
) -> bool:
    """Valida assinatura HMAC e verifica proteção contra replay attacks com tolerância temporal."""
    try:
        ts = int(timestamp_header)
    except (ValueError, TypeError):
        return False

    now = int(time.time())
    if abs(now - ts) > max_drift_seconds:
        return False

    expected_sig = compute_webhook_signature(secret, ts, body)

    # Extrai assinatura v1 se vier no formato t=...,v1=...
    candidate_sig = signature_header
    if "v1=" in signature_header:
        parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
        candidate_sig = parts.get("v1", "")

    return hmac.compare_digest(candidate_sig.strip(), expected_sig)
