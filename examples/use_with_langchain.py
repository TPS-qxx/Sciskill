"""
Example: Using SciSkills with LangChain agents.

Prerequisites:
    pip install sciskills langchain langchain-openai
    export OPENAI_API_KEY=your_key   (or configure your LLM provider)
    export LLM_API_KEY=your_key      (for SciSkills internal LLM calls)
"""
import os

import sciskills
from sciskills import registry
from sciskills.core.adapters import SciSkillLangChainTool


def build_research_agent():
    """Build a LangChain agent with SciSkills tools."""
    try:
        from langchain.agents import AgentType, initialize_agent
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install: pip install langchain langchain-openai")
        return

    # Wrap skills as LangChain tools
    skill_names = [
        "paper_structural_extractor",
        "experiment_result_comparator",
        "bibtex_fixer_enricher",
        "statistical_test_advisor",
    ]
    tools = [
        SciSkillLangChainTool(registry.get(name)).as_langchain_tool()
        for name in skill_names
    ]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
    )
    return agent


if __name__ == "__main__":
    agent = build_research_agent()
    if agent:
        result = agent.run(
            "Extract the key information from the paper arXiv:2303.08774. "
            "Then check if there are any research gaps in the methodology."
        )
        print(result)
