# SciSkills

**AI Agent Skills for Academic Research**

SciSkills is an open-source collection of standardized, composable AI agent skills for graduate researchers. Each skill is a self-contained, callable module with a well-defined JSON Schema interface — designed to work standalone or plug into any agent framework (LangChain, Claude Tool Use, AutoGPT, custom agents).

---

## Skills

| # | Skill | What it does | LLM? |
|---|-------|-------------|------|
| 1 | `paper_structural_extractor` | Extract structured JSON from a paper (arXiv ID / DOI / PDF) | ✓ |
| 2 | `bibtex_fixer_enricher` | Fix, normalize and enrich BibTeX entries via Crossref API | rule-based |
| 3 | `experiment_result_comparator` | Rank experiments, bold best values, generate LaTeX/Markdown tables | optional |
| 4 | `statistical_test_advisor` | Recommend and run statistical tests with Python/R code | optional |
| 5 | `research_gap_identifier` | Build coverage matrix and identify unexplored research directions | ✓ |
| 6 | `reproducibility_checker` | Analyze a GitHub repo for reproducibility issues (score 0-100) | optional |

**Dependency graph:**
```
Layer 1 (foundational):  Skill 1 · Skill 2 · Skill 6
Layer 2 (standalone):    Skill 3 · Skill 4
Layer 3 (composite):     Skill 5  ← uses output of Skill 1
```

---

## Installation

```bash
pip install sciskills                    # core only
pip install "sciskills[all]"             # all optional dependencies
pip install "sciskills[pdf,bibtex,stats]"  # pick what you need
```

**Optional extras:**

| Extra | Installs |
|-------|---------|
| `pdf` | `pymupdf` — local PDF parsing |
| `bibtex` | `bibtexparser` — BibTeX parsing |
| `stats` | `scipy`, `pingouin` — running statistical tests |
| `langchain` | LangChain adapter support |
| `anthropic` | Claude Tool Use adapter support |

---

## Quick Start

### 1. Configure LLM

```bash
export LLM_API_KEY=your_key
export LLM_BASE_URL=https://ep-llm.zhenguanyu.com/gateway-cn-online/openai-compatible/v1
export LLM_MODEL=doubao-seed-1.8
```

Or copy `.env.example` → `.env` and fill in your values.

### 2. Use a skill directly

```python
import sciskills
from sciskills import registry

# Extract structured info from a paper
skill = registry.get("paper_structural_extractor")
result = skill({"arxiv_id": "1706.03762"})

print(result.success)          # True
print(result.data["paper"]["research_question"])
print(result.data["paper"]["datasets"])
```

### 3. Compare experiment results

```python
skill = registry.get("experiment_result_comparator")
result = skill({
    "experiments": [
        {"name": "BERT",     "metrics": {"F1": 88.5, "Latency_ms": 120}},
        {"name": "RoBERTa",  "metrics": {"F1": 91.2, "Latency_ms": 280}},
        {"name": "DistilBERT","metrics": {"F1": 85.3, "Latency_ms":  65}},
    ],
    "primary_metric": "F1",
    "higher_is_better": {"F1": True, "Latency_ms": False},
    "output_format": "all",
})
print(result.data["latex_table"])   # ready to paste into your paper
print(result.data["markdown_table"])
```

### 4. Fix BibTeX

```python
skill = registry.get("bibtex_fixer_enricher")
result = skill({
    "bib_path": "refs.bib",
    "auto_enrich": True,
    "remove_duplicates": True,
    "normalize_authors": True,
})
print(result.data["fixed_bibtex"])
print(result.data["stats"])  # {"total": 50, "issues_found": 12, ...}
```

### 5. Get statistical test recommendation

```python
skill = registry.get("statistical_test_advisor")
result = skill({
    "research_question_type": "group_comparison",
    "num_groups": 2,
    "variable_type": "continuous",
    "paired": False,
    "sample_size": [35, 32],
    "data": [control_group, treatment_group],  # optional: actually run the test
})
print(result.data["primary_recommendation"]["test_name"])
print(result.data["python_code"])
print(result.data["test_results"])   # statistic, p_value, significant
```

### 6. Check reproducibility

```python
skill = registry.get("reproducibility_checker")
result = skill({"repo_url": "https://github.com/owner/mymodel"})
print(result.data["score"])    # 0-100
for check in result.data["checks"]:
    status = "✓" if check["passed"] else "✗"
    print(f"  {status} {check['item']}")
```

---

## Architecture

All skills follow the same interface:

```python
from sciskills.core.base import BaseSkill, SkillResult

class MySkill(BaseSkill):
    name = "my_skill"
    description = "What this skill does (used by agents for tool discovery)."
    input_schema  = { ... }   # JSON Schema
    output_schema = { ... }   # JSON Schema

    def execute(self, params: dict) -> SkillResult:
        ...
        return SkillResult.ok(data={...})
```

`SkillResult` always has:
```python
{
    "success": bool,
    "data":    dict,      # structured output
    "errors":  list[str], # non-empty only on failure
    "metadata": dict      # elapsed_seconds, skill name, etc.
}
```

---

## Agent Framework Integration

### Claude Tool Use

```python
from sciskills.core.adapters import SciSkillClaudeTool
import anthropic

skill   = registry.get("paper_structural_extractor")
adapter = SciSkillClaudeTool(skill)

client   = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-4-6",
    tools=[adapter.tool_definition()],
    messages=[{"role": "user", "content": "Extract info from arXiv:1706.03762"}],
)
# On tool_use block:
result_json = adapter.handle_tool_call(tool_use_block.input)
```

### LangChain

```python
from sciskills.core.adapters import SciSkillLangChainTool

tool  = SciSkillLangChainTool(registry.get("bibtex_fixer_enricher"))
lc_tool = tool.as_langchain_tool()
# Use in any LangChain agent or chain
```

### List all available skills as OpenAI-compatible tools

```python
from sciskills import registry
tools = registry.to_openai_tools()   # plug into any OpenAI-compatible framework
```

---

## Development

```bash
git clone https://github.com/sciskills/sciskills
cd sciskills
pip install -e ".[dev,pdf,bibtex,stats]"
pytest
```

### Roadmap

- **v0.1** — Core framework + Skill 1 (Paper Extractor) + Skill 2 (BibTeX Fixer) ✓
- **v0.2** — Skill 3 (Experiment Comparator) + Skill 6 (Reproducibility Checker) ✓
- **v0.3** — Skill 4 (Statistical Advisor) + Skill 5 (Gap Identifier) + full adapters ✓
- **v0.4** — Async support, caching layer, more PDF backends, OpenAlex enrichment
- **v1.0** — Stable API, full docs, CLI tool

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) and open an issue before submitting a large PR.

---

## License

MIT © SciSkills Contributors
