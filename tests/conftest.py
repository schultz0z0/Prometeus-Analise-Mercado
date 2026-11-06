"""Credenciais fictícias explícitas: os testes HTTP continuam atravessando o controle real."""

import json

import pytest


@pytest.fixture(autouse=True)
def isolated_access_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SERVICE_API_KEYS",
        json.dumps(
            [
                {
                    "key": "test-admin-key-12345678901234567890",
                    "subject": "test-operator",
                    "tenant_id": "ens",
                    "role": "admin",
                },
                {
                    "key": "test-infnet-key-12345678901234567890",
                    "subject": "test-infnet",
                    "tenant_id": "infnet",
                    "role": "admin",
                },
            ]
        ),
    )
    monkeypatch.setenv("AUTH_ADMIN_KEY_PATH", str(tmp_path / "admin.key"))
