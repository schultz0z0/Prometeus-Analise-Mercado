import json
import logging

from prometeus.observability.logging import (
    StructuredJsonFormatter,
    correlation_id_ctx,
    redact_sensitive_data,
)


def test_redact_sensitive_keys_in_dict() -> None:
    data = {
        "tenant_id": "ens",
        "api_key": "secret-api-key-12345",
        "auth_token": "bearer-token-abc",
        "nested": {
            "password": "super-secret-password",
            "openai_api_key": "sk-proj-1234567890abcdefghij",
            "normal_field": "public_value",
        },
    }
    redacted = redact_sensitive_data(data)

    assert redacted["tenant_id"] == "ens"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["auth_token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["openai_api_key"] == "[REDACTED]"
    assert redacted["nested"]["normal_field"] == "public_value"


def test_redact_sensitive_tokens_in_strings() -> None:
    bearer_str = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30"
    sk_str = "sk-proj-abc1234567890xyz"
    normal_str = "Este é um curso de MBA em Seguros"

    assert redact_sensitive_data(bearer_str) == "[REDACTED]"
    assert redact_sensitive_data(sk_str) == "[REDACTED]"
    assert redact_sensitive_data(normal_str) == normal_str


def test_structured_json_formatter_output() -> None:
    correlation_id_ctx.set("corr-test-log-999")
    formatter = StructuredJsonFormatter()

    record = logging.LogRecord(
        name="prometeus.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Teste de log estruturado com segredo",
        args=(),
        exc_info=None,
    )
    # Atribui extra com campo sensível
    record.extra = {"api_key": "should-be-masked", "user": "admin"}  # type: ignore[attr-defined]

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "prometeus.test"
    assert parsed["message"] == "Teste de log estruturado com segredo"
    assert parsed["correlation_id"] == "corr-test-log-999"
    assert parsed["extra"]["api_key"] == "[REDACTED]"
    assert parsed["extra"]["user"] == "admin"
    assert "timestamp" in parsed
