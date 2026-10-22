"""Dispatcher de webhooks assinado com HMAC-SHA256, timestamps, retries e dead-letter (Fase 07)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from prometeus.domain.webhooks import (
    WebhookDeliveryStatus,
    WebhookEvent,
    compute_webhook_signature,
)
from prometeus.infrastructure.db.models import WebhookDeliveryModel

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Serviço de envio confiável e assinado de eventos para endpoints de webhook."""

    def __init__(
        self,
        db_session: AsyncSession,
        secret: str = "prometeus-webhook-secret-v1",
        timeout_seconds: float = 5.0,
        max_retries: int = 5,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db = db_session
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._custom_client = http_client

    async def dispatch(
        self,
        event: WebhookEvent,
        target_url: str,
    ) -> WebhookDeliveryModel:
        """Envia o evento assinado ao endpoint com rastreamento persistente de tentativas."""
        body = event.to_json()
        sig = compute_webhook_signature(self.secret, event.timestamp, body)

        headers = {
            "Content-Type": "application/json",
            "X-Prometeus-Signature": f"t={event.timestamp},v1={sig}",
            "X-Prometeus-Timestamp": str(event.timestamp),
            "X-Prometeus-Event-ID": event.event_id,
        }

        # Busca ou cria registro de entrega
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.event_id == event.event_id,
            WebhookDeliveryModel.target_url == target_url,
        )
        delivery = (await self.db.execute(stmt)).scalar_one_or_none()

        if not delivery:
            delivery = WebhookDeliveryModel(
                id=str(uuid.uuid4()),
                analysis_id=event.analysis_id,
                event_id=event.event_id,
                event_type=event.event_type.value,
                target_url=target_url,
                status=WebhookDeliveryStatus.PENDING.value,
                attempt_count=0,
                payload=event.payload,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.db.add(delivery)
            await self.db.flush()

        delivery.attempt_count += 1
        delivery.updated_at = datetime.now(UTC)

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        close_client = self._custom_client is None

        try:
            resp = await client.post(target_url, content=body, headers=headers)
            delivery.response_code = resp.status_code
            delivery.response_body = resp.text[:1000]

            if resp.is_success:
                delivery.status = WebhookDeliveryStatus.DELIVERED.value
                delivery.last_error = None
                logger.info(
                    f"Webhook {event.event_id} entregue com sucesso em {target_url} (HTTP {resp.status_code})"
                )
            else:
                delivery.last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if delivery.attempt_count >= self.max_retries:
                    delivery.status = WebhookDeliveryStatus.DEAD_LETTER.value
                    logger.error(
                        f"Webhook {event.event_id} atingiu limite de tentativas ({self.max_retries}). Enviado para DEAD_LETTER."
                    )
                else:
                    delivery.status = WebhookDeliveryStatus.FAILED.value
        except Exception as exc:
            delivery.response_code = None
            delivery.last_error = str(exc)
            if delivery.attempt_count >= self.max_retries:
                delivery.status = WebhookDeliveryStatus.DEAD_LETTER.value
                logger.error(
                    f"Webhook {event.event_id} falhou por erro de rede e foi para DEAD_LETTER: {exc}"
                )
            else:
                delivery.status = WebhookDeliveryStatus.FAILED.value
        finally:
            if close_client:
                await client.aclose()
            await self.db.commit()

        return delivery
