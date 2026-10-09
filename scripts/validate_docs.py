"""Validação leve da fundação documental, sem dependências externas."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")

REQUIRED = {
    "README.md",
    ".env.example",
    "docs/README.md",
    "docs/product/PRD.md",
    "docs/architecture/system-overview.md",
    "docs/agent/workflow.md",
    "docs/scoring/scoring-model.md",
    "docs/security/threat-model.md",
    "docs/roadmap/roadmap.md",
    "docs/plans/2026-10-09-product-foundation.md",
}

EXPECTED_PHASES = {f"docs/implementation/phase-{index:02d}" for index in range(10)}


def validate_required() -> list[str]:
    return [f"missing required file: {path}" for path in sorted(REQUIRED) if not (ROOT / path).exists()]


def validate_links() -> list[str]:
    errors: list[str] = []
    for document in ROOT.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"broken link: {document.relative_to(ROOT)} -> {target}")
    return errors


def validate_env() -> list[str]:
    names: set[str] = set()
    errors: list[str] = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name = stripped.split("=", 1)[0]
        if name in names:
            errors.append(f"duplicate environment variable: {name}")
        names.add(name)
    return errors


def validate_implementation_phases() -> list[str]:
    present: set[str] = set()
    for path in (ROOT / "docs" / "implementation").glob("phase-*.md"):
        match = re.match(r"phase-(\d{2})-", path.name)
        if match:
            present.add(f"docs/implementation/phase-{match.group(1)}")
    return [f"missing implementation phase: {phase}" for phase in sorted(EXPECTED_PHASES - present)]


def validate_scoring_weights() -> list[str]:
    path = ROOT / "config" / "scoring" / "default-v1.example.yaml"
    text = path.read_text(encoding="utf-8")
    weights_block = text.split("weights:", 1)[1].split("gates:", 1)[0]
    weights = [float(value) for value in re.findall(r":\s+(0\.\d+|1\.0+)\s*$", weights_block, re.MULTILINE)]
    if abs(sum(weights) - 1.0) > 1e-9:
        return [f"scoring weights sum to {sum(weights):.6f}, expected 1.0"]
    return []


def main() -> int:
    errors = (
        validate_required()
        + validate_links()
        + validate_env()
        + validate_implementation_phases()
        + validate_scoring_weights()
    )
    if errors:
        print("Documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    md_count = sum(1 for _ in ROOT.rglob("*.md"))
    print(f"Documentation validation passed: {md_count} Markdown files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
