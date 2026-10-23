"""Registry allowlisted de skills versionadas usadas pelo workflow."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


class SkillRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class DomainSkill:
    name: str
    description: str
    version: str
    instructions: str
    content_hash: str

    def snapshot(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "content_hash": self.content_hash,
        }


class SkillRegistry:
    ALLOWLIST: dict[str, tuple[str, ...]] = {
        "course_understanding": ("understanding-course-proposals",),
        "research_planning": ("planning-market-research",),
        "evidence_review": ("reviewing-market-evidence",),
        "curriculum_audit": ("auditing-course-curriculum",),
        "dossier_synthesis": ("reviewing-market-evidence", "building-course-offers"),
    }

    def __init__(self, root: Path | str = "skills") -> None:
        self.root = Path(root)
        self._cache: dict[str, DomainSkill] = {}

    @property
    def allowed_names(self) -> set[str]:
        return {name for names in self.ALLOWLIST.values() for name in names}

    def _parse(self, name: str) -> DomainSkill:
        if name not in self.allowed_names:
            raise SkillRegistryError(f"Skill '{name}' não pertence à allowlist.")
        skill_path = self.root / name / "SKILL.md"
        if not skill_path.is_file():
            raise SkillRegistryError(f"Skill allowlisted não encontrada: {name}")
        content = skill_path.read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter:
            raise SkillRegistryError(f"Frontmatter inválido na skill '{name}'.")
        metadata: dict[str, str] = {}
        for line in frontmatter.group(1).splitlines():
            key, separator, value = line.partition(":")
            if separator:
                metadata[key.strip()] = value.strip()
        version_match = re.search(r"\*\*Version:\*\*\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
        if not version_match:
            raise SkillRegistryError(f"Versão semântica ausente na skill '{name}'.")
        if metadata.get("name") != name:
            raise SkillRegistryError(f"Nome divergente na skill '{name}'.")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return DomainSkill(
            name=name,
            description=metadata.get("description", ""),
            version=version_match.group(1),
            instructions=content[frontmatter.end() :].strip(),
            content_hash=digest,
        )

    def get(self, name: str) -> DomainSkill:
        if name not in self._cache:
            self._cache[name] = self._parse(name)
        return self._cache[name]

    def load_all(self) -> dict[str, DomainSkill]:
        return {name: self.get(name) for name in sorted(self.allowed_names)}

    def for_stage(self, stage: str) -> list[DomainSkill]:
        names = self.ALLOWLIST.get(stage)
        if names is None:
            raise SkillRegistryError(f"Estágio de skills não allowlisted: {stage}")
        return [self.get(name) for name in names]
