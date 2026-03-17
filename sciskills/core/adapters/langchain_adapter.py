"""
LangChain adapter: wraps a SciSkill as a LangChain BaseTool.

Usage:
    from sciskills.core.adapters import SciSkillLangChainTool
    from sciskills.skills.paper_extractor import PaperStructuralExtractor

    tool = SciSkillLangChainTool(skill=PaperStructuralExtractor())
    # Use in any LangChain agent or chain
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sciskills.core.base import BaseSkill

if TYPE_CHECKING:
    pass


def _make_langchain_tool(skill: BaseSkill):  # type: ignore[return]
    """
    Dynamically create a LangChain BaseTool subclass for the given skill.
    Requires langchain to be installed.
    """
    try:
        from langchain.tools import BaseTool
        from pydantic import BaseModel, Field, create_model
    except ImportError as e:
        raise ImportError(
            "langchain is required for LangChain adapter. "
            "Install with: pip install langchain"
        ) from e

    # Build a pydantic model from the skill's JSON Schema
    schema_props: dict = skill.input_schema.get("properties", {})
    required_fields: list = skill.input_schema.get("required", [])
    field_definitions: dict[str, Any] = {}
    for prop_name, prop_schema in schema_props.items():
        description = prop_schema.get("description", "")
        default = ... if prop_name in required_fields else None
        field_definitions[prop_name] = (Any, Field(default=default, description=description))

    InputModel = create_model(f"{skill.name}_Input", **field_definitions)

    class _SkillTool(BaseTool):
        name: str = skill.name
        description: str = skill.description
        args_schema: type[BaseModel] = InputModel

        def _run(self, **kwargs: Any) -> str:
            result = skill(kwargs)
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

        async def _arun(self, **kwargs: Any) -> str:  # type: ignore[override]
            return self._run(**kwargs)

    return _SkillTool()


class SciSkillLangChainTool:
    """
    Convenience wrapper.

    Example:
        tool = SciSkillLangChainTool(skill=PaperStructuralExtractor())
        agent = initialize_agent(tools=[tool.as_langchain_tool()], ...)
    """

    def __init__(self, skill: BaseSkill):
        self._skill = skill

    def as_langchain_tool(self):
        return _make_langchain_tool(self._skill)
