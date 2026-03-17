"""
SciSkills — AI Agent Skills for Academic Research.

Quick start:
    from sciskills import registry, skills
    skill = registry.get("paper_structural_extractor")
    result = skill({"arxiv_id": "2303.08774"})
    print(result.data)
"""
from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
import sciskills.skills  # noqa: F401 — triggers registration of all skills

__version__ = "0.1.0"
__all__ = ["BaseSkill", "SkillResult", "registry"]
