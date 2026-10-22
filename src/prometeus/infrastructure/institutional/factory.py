"""Factory dinâmica de adaptadores institucionais para suporte multi-tenant e white-label."""

from __future__ import annotations

from typing import Any

from prometeus.domain.ports.institutional_data import InstitutionalDataAdapter
from prometeus.infrastructure.institutional.ens.client import ENSInstitutionalAdapter
from prometeus.infrastructure.institutional.infnet.client import InfnetInstitutionalAdapter
from prometeus.infrastructure.institutional.mock import MockInstitutionalAdapter

ADAPTER_REGISTRY: dict[str, type[InstitutionalDataAdapter]] = {
    "ens": ENSInstitutionalAdapter,
    "infnet": InfnetInstitutionalAdapter,
    "mock": MockInstitutionalAdapter,
}


def create_institutional_adapter(
    adapter_name: str,
    **kwargs: Any,
) -> InstitutionalDataAdapter:
    """Instancia o conector institucional correspondente à configuração do tenant."""
    key = adapter_name.strip().lower()
    adapter_cls = ADAPTER_REGISTRY.get(key)
    if not adapter_cls:
        raise ValueError(
            f"Adaptador institucional desconhecido: '{adapter_name}'. "
            f"Disponíveis: {list(ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls(**kwargs)
