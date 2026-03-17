"""
Claude Tool Use adapter: wraps a SciSkill as an Anthropic-compatible tool.

Usage:
    import anthropic
    from sciskills.core.adapters import SciSkillClaudeTool
    from sciskills.skills.paper_extractor import PaperStructuralExtractor

    skill = PaperStructuralExtractor()
    adapter = SciSkillClaudeTool(skill)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        tools=[adapter.tool_definition()],
        messages=[{"role": "user", "content": "Extract paper ..."}],
    )
    # Handle tool_use blocks:
    result = adapter.handle_tool_call(response)
"""
from __future__ import annotations

import json
from typing import Any

from sciskills.core.base import BaseSkill


class SciSkillClaudeTool:
    """Thin adapter for Claude Tool Use API."""

    def __init__(self, skill: BaseSkill):
        self._skill = skill

    def tool_definition(self) -> dict:
        """Return dict suitable for the `tools` parameter of Anthropic messages API."""
        return self._skill.to_anthropic_tool()

    def handle_tool_call(self, tool_input: dict[str, Any]) -> str:
        """
        Execute the skill from a tool_use block's `input` dict.
        Returns a JSON string to be placed in the tool_result content.
        """
        result = self._skill(tool_input)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
