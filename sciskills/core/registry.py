"""
Skill registry: central catalog for discovering and instantiating skills.
"""
from __future__ import annotations

from typing import Type

from sciskills.core.base import BaseSkill


class SkillRegistry:
    """Thread-safe singleton registry for all registered skills."""

    _instance: "SkillRegistry | None" = None
    _skills: dict[str, Type[BaseSkill]] = {}

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    # ------------------------------------------------------------------ #

    def register(self, skill_cls: Type[BaseSkill]) -> Type[BaseSkill]:
        """Register a skill class. Can be used as a decorator."""
        if not skill_cls.name:
            raise ValueError(f"Skill class {skill_cls.__name__} must define 'name'.")
        self._skills[skill_cls.name] = skill_cls
        return skill_cls

    def get(self, name: str) -> BaseSkill:
        """Instantiate and return a skill by name."""
        if name not in self._skills:
            available = ", ".join(self._skills.keys())
            raise KeyError(f"Skill '{name}' not found. Available: {available}")
        return self._skills[name]()

    def list_skills(self) -> list[dict]:
        """Return metadata for all registered skills."""
        return [
            {
                "name": cls.name,
                "description": cls.description,
            }
            for cls in self._skills.values()
        ]

    def to_openai_tools(self) -> list[dict]:
        return [cls().to_openai_tool() for cls in self._skills.values()]

    def to_anthropic_tools(self) -> list[dict]:
        return [cls().to_anthropic_tool() for cls in self._skills.values()]


# Module-level singleton
registry = SkillRegistry()
