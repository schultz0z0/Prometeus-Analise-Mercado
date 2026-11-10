"""Canonical declared curriculum, preserving text and structured modules."""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any

CURRICULUM_FIELDS = ("curriculum_text", "curriculum", "modules", "learning_outcomes")


def declared_curriculum(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(proposal[key])
        for key in CURRICULUM_FIELDS
        if proposal.get(key) not in (None, "", [], {})
    }


def _texts(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _texts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _texts(child)


def curriculum_text(proposal: dict[str, Any]) -> str:
    return "\n".join(_texts(declared_curriculum(proposal)))
