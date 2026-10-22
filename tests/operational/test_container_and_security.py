"""Testes operacionais de arquitetura de containers, princípio de menor privilégio e isolamento de rede."""

from pathlib import Path

import yaml


def test_compose_yaml_network_isolation_and_services() -> None:
    compose_path = Path("compose.yaml")
    assert compose_path.exists(), "compose.yaml não encontrado na raiz"

    with compose_path.open("r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    networks = compose_data.get("networks", {})

    # 1. Validação de isolamento de rede interna
    assert "prometeus_internal" in networks
    assert networks["prometeus_internal"].get("internal") is True

    # 2. Banco e Redis devem estar estritamente isolados na rede interna
    assert "postgres" in services
    assert services["postgres"]["networks"] == ["prometeus_internal"]

    assert "redis" in services
    assert services["redis"]["networks"] == ["prometeus_internal"]

    # 3. API deve estar conectada à rede interna e à pública
    assert "api" in services
    assert "prometeus_internal" in services["api"]["networks"]
    assert "prometeus_public" in services["api"]["networks"]

    # 4. Worker deve estar apenas na rede interna
    assert "worker" in services
    assert services["worker"]["networks"] == ["prometeus_internal"]

    # 5. Serviço de backup deve existir com snapshot configurado
    assert "backup" in services
    assert services["backup"]["networks"] == ["prometeus_internal"]


def test_dockerfile_hardening_and_least_privilege() -> None:
    dockerfile_path = Path("deploy/docker/Dockerfile")
    assert dockerfile_path.exists(), "deploy/docker/Dockerfile não encontrado"

    content = dockerfile_path.read_text(encoding="utf-8")

    # 1. Multi-stage build
    assert "FROM python:3.11-slim AS builder" in content
    assert "FROM python:3.11-slim AS runner" in content

    # 2. Princípio do menor privilégio (Non-root user)
    assert "useradd -u 10001 -g prometeus -s /bin/sh -m prometeus" in content
    assert "USER prometeus" in content

    # 3. Healthcheck nativo
    assert "HEALTHCHECK" in content
