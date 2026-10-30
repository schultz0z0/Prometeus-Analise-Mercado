"""Schema de geração; referências são limitadas aos fatos aprovados da análise."""

from typing import Any


def dossier_json_schema(
    evidence_ids: list[str], *, claim_ids: list[str] | None = None
) -> dict[str, Any]:
    def obj(properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    def arr(item: dict[str, Any], minimum: int = 0, maximum: int = 12) -> dict[str, Any]:
        return {"type": "array", "items": item, "minItems": minimum, "maxItems": maximum}

    text = {"type": "string"}
    refs = arr({"type": "string", "enum": sorted(set(evidence_ids))}, 1, 15)
    claim_id = {
        "type": "string",
        "enum": sorted(set(claim_ids)) if claim_ids else [f"CLM-{n:02}" for n in range(1, 13)],
    }
    claim_refs = arr(claim_id, 1, 12)
    return obj(
        {
            "schema_version": {"type": "integer", "enum": [2, 3]},
            "executive_summary": text,
            "executive_summary_claim_ids": claim_refs,
            "sections": arr(
                obj(
                    {
                        "section_id": text,
                        "title": text,
                        "target_audience": {
                            "type": "string",
                            "enum": ["executive", "academic", "marketing"],
                        },
                        "content": text,
                        "claim_ids": claim_refs,
                    }
                ),
                3,
                3,
            ),
            "claims": arr(
                obj(
                    {
                        "claim_id": claim_id,
                        "statement": text,
                        "claim_type": {
                            "type": "string",
                            "enum": ["quantitative", "qualitative", "strategic"],
                        },
                        "evidence_ids": refs,
                        "support_level": {
                            "type": "string",
                            "enum": ["observed", "suggestive", "hypothesis"],
                        },
                    }
                ),
                1,
                12,
            ),
            "highlights": obj(
                {
                    "pros": arr(claim_id, 0, 4),
                    "cons": arr(claim_id, 0, 4),
                    "competitors": arr(obj({"label": text, "claim_ids": claim_refs}), 0, 4),
                    "curriculum_alignment": arr(
                        obj(
                            {
                                "module": text,
                                "need_claim_ids": claim_refs,
                                "coverage_claim_ids": claim_refs,
                            }
                        ),
                        0,
                        6,
                    ),
                    "validation_criteria": arr(
                        obj(
                            {
                                "criterion": text,
                                "target": text,
                                "claim_ids": claim_refs,
                                "status": {"type": "string", "enum": ["pending"]},
                            }
                        ),
                        0,
                        3,
                    ),
                    "action_recommendations": arr(
                        obj(
                            {
                                "area": text,
                                "action": text,
                                "claim_ids": claim_refs,
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                                "status": {"type": "string", "enum": ["proposed"]},
                            }
                        ),
                        0,
                        3,
                    ),
                }
            ),
        }
    )
