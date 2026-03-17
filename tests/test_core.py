"""Tests for core framework components."""
import pytest
import jsonschema

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import SkillRegistry


# ------------------------------------------------------------------ #
# SkillResult                                                          #
# ------------------------------------------------------------------ #

def test_skill_result_ok():
    r = SkillResult.ok(data={"key": "value"}, metadata={"elapsed": 0.1})
    assert r.success is True
    assert r.data == {"key": "value"}
    assert r.errors == []


def test_skill_result_fail():
    r = SkillResult.fail(errors=["something went wrong"])
    assert r.success is False
    assert "something went wrong" in r.errors


def test_skill_result_to_dict():
    r = SkillResult.ok(data={"x": 1})
    d = r.to_dict()
    assert d["success"] is True
    assert d["data"] == {"x": 1}
    assert isinstance(d["errors"], list)


# ------------------------------------------------------------------ #
# BaseSkill                                                            #
# ------------------------------------------------------------------ #

class _MockSkill(BaseSkill):
    name = "mock_skill"
    description = "A mock skill for testing."
    input_schema = {
        "type": "object",
        "required": ["value"],
        "properties": {"value": {"type": "integer"}},
    }
    output_schema = {
        "type": "object",
        "properties": {"doubled": {"type": "integer"}},
    }

    def execute(self, params: dict) -> SkillResult:
        return SkillResult.ok(data={"doubled": params["value"] * 2})


def test_mock_skill_execute():
    skill = _MockSkill()
    result = skill({"value": 5})
    assert result.success is True
    assert result.data["doubled"] == 10


def test_mock_skill_invalid_input():
    skill = _MockSkill()
    with pytest.raises(jsonschema.ValidationError):
        skill({"value": "not_an_int"})


def test_mock_skill_openai_tool():
    skill = _MockSkill()
    tool = skill.to_openai_tool()
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "mock_skill"


def test_mock_skill_anthropic_tool():
    skill = _MockSkill()
    tool = skill.to_anthropic_tool()
    assert tool["name"] == "mock_skill"
    assert "input_schema" in tool


def test_mock_skill_metadata():
    skill = _MockSkill()
    result = skill({"value": 3})
    assert "elapsed_seconds" in result.metadata
    assert result.metadata["skill"] == "mock_skill"


# ------------------------------------------------------------------ #
# Registry                                                             #
# ------------------------------------------------------------------ #

def test_registry_register_and_get():
    reg = SkillRegistry()
    reg.register(_MockSkill)
    skill = reg.get("mock_skill")
    assert isinstance(skill, _MockSkill)


def test_registry_list():
    reg = SkillRegistry()
    reg.register(_MockSkill)
    names = [s["name"] for s in reg.list_skills()]
    assert "mock_skill" in names


def test_registry_unknown_skill():
    reg = SkillRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent_skill_xyz")


def test_registry_to_openai_tools():
    reg = SkillRegistry()
    reg.register(_MockSkill)
    tools = reg.to_openai_tools()
    assert any(t["function"]["name"] == "mock_skill" for t in tools)
