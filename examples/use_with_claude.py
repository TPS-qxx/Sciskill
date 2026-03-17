"""
Example: Using SciSkills with Claude Tool Use API (Anthropic SDK).

Prerequisites:
    pip install sciskills anthropic
    export ANTHROPIC_API_KEY=your_anthropic_key
    export LLM_API_KEY=your_key   # for internal skill LLM calls
"""
import json
import os

import anthropic

import sciskills
from sciskills import registry
from sciskills.core.adapters import SciSkillClaudeTool


def run_agent_loop(user_message: str, skill_names: list[str]) -> str:
    """
    Run a simple Claude tool-use loop with the specified SciSkills.

    Args:
        user_message: The user's research request.
        skill_names: Names of SciSkills to expose as tools.

    Returns:
        Final text response from Claude.
    """
    client = anthropic.Anthropic()

    # Build tool definitions
    adapters = {name: SciSkillClaudeTool(registry.get(name)) for name in skill_names}
    tools = [adapter.tool_definition() for adapter in adapters.values()]

    messages = [{"role": "user", "content": user_message}]

    print(f"User: {user_message}\n")

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            print(f"Claude: {final_text}")
            return final_text

        if response.stop_reason != "tool_use":
            break

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            print(f"  [Tool call: {tool_name}]")

            if tool_name in adapters:
                result_json = adapters[tool_name].handle_tool_call(tool_input)
            else:
                result_json = json.dumps({"error": f"Unknown tool: {tool_name}"})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_json,
            })

        messages.append({"role": "user", "content": tool_results})

    return "[No response]"


if __name__ == "__main__":
    # Example 1: Paper extraction + gap analysis
    run_agent_loop(
        user_message=(
            "Please extract the key information from the paper arXiv:1706.03762 "
            "(Attention Is All You Need), then tell me what research gaps might exist "
            "based on its methodology and datasets."
        ),
        skill_names=["paper_structural_extractor"],
    )

    # Example 2: Experiment comparison
    run_agent_loop(
        user_message=(
            "I have these NER results:\n"
            "- BERT-base: F1=88.5, Latency=120ms\n"
            "- RoBERTa: F1=91.2, Latency=280ms\n"
            "- DistilBERT: F1=85.3, Latency=65ms\n"
            "Generate a LaTeX comparison table and analyze the speed-accuracy trade-off."
        ),
        skill_names=["experiment_result_comparator"],
    )
