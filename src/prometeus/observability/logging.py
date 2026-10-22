"""Logs JSON estruturados com correlation IDs e redação estrita de segredos."""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# ContextVar para propagação transparente do correlation_id por requisição/tarefa
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="none")

# Padrões de campos sensíveis para mascaramento
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|authorization|credential|bearer)"
)


def redact_sensitive_data(data: Any) -> Any:
    """Mascara recursivamente valores de dicionários ou textos contendo chaves/senhas."""
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if isinstance(k, str) and SENSITIVE_KEY_PATTERN.search(k):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    if isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    if isinstance(data, str) and len(data) > 20 and ("Bearer " in data or "sk-" in data):
        return "[REDACTED]"
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formatador de logs em JSON compatível com agregadores modernos (Datadog, Grafana Loki)."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
        }

        # Anexa campos extras se fornecidos no logging
        extra_dict = getattr(record, "extra", None)
        if isinstance(extra_dict, dict):
            log_payload["extra"] = redact_sensitive_data(extra_dict)

        # Inclui stack trace se houver exceção
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(redact_sensitive_data(log_payload), ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configura o root logger para emissão exclusiva de JSON estruturado."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Remove handlers antigos
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)
