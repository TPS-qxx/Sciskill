"""
Core base classes for SciSkills framework.
All skills must inherit from BaseSkill and return SkillResult.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import jsonschema


@dataclass
class SkillResult:
    """Unified result structure returned by all skills."""

    success: bool
    data: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def ok(cls, data: dict, metadata: dict | None = None) -> "SkillResult":
        return cls(success=True, data=data, metadata=metadata or {})

    @classmethod
    def fail(cls, errors: list[str], data: dict | None = None) -> "SkillResult":
        return cls(success=False, data=data or {}, errors=errors)


class BaseSkill(ABC):
    """
    Abstract base class for all SciSkills skills.

    Each skill exposes:
    - name / description for agent discovery
    - input_schema / output_schema (JSON Schema dicts)
    - validate_input() for pre-execution validation
    - execute() as the main entry point
    - explain() for human-readable usage docs
    """

    # --- Subclasses MUST define these ---
    name: str = ""
    description: str = ""
    input_schema: dict = {}
    output_schema: dict = {}

    # ------------------------------------------------------------------ #

    def validate_input(self, params: dict) -> bool:
        """Validate params against input_schema. Raises ValidationError on failure."""
        jsonschema.validate(instance=params, schema=self.input_schema)
        return True

    @abstractmethod
    def execute(self, params: dict) -> SkillResult:
        """Main execution logic. Must return a SkillResult."""
        ...

    def __call__(self, params: dict) -> SkillResult:
        """Convenience: validate then execute, wrapping timing in metadata."""
        self.validate_input(params)
        t0 = time.perf_counter()
        result = self.execute(params)
        elapsed = round(time.perf_counter() - t0, 3)
        result.metadata.setdefault("elapsed_seconds", elapsed)
        result.metadata.setdefault("skill", self.name)
        return result

    def explain(self) -> str:
        """Return a human-readable description and usage example."""
        lines = [
            f"Skill: {self.name}",
            f"Description: {self.description}",
            "",
            "Input Schema:",
            str(self.input_schema),
            "",
            "Output Schema:",
            str(self.output_schema),
        ]
        return "\n".join(lines)

    # --- Tool-Use / OpenAI function-call representation ---------------- #

    def to_openai_tool(self) -> dict:
        """Export as an OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def to_anthropic_tool(self) -> dict:
        """Export as an Anthropic Claude tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
