# SciSkills

**AI Agent Skills for Academic Research**

SciSkills is an open-source collection of Agent Skills for graduate researchers. Each skill is a self-contained folder with a `SKILL.md` instruction file, executable scripts, and reference docs — following the [Anthropic Agent Skills open standard](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

---

## What is an Agent Skill?

An Agent Skill is a **folder containing `SKILL.md`** — a structured instruction file that tells an AI agent *when* to use the skill and *how* to execute it, step by step. Skills are:

- **Lazily loaded**: the agent only reads the full `SKILL.md` when the task matches the skill's description
- **Composable**: skills can call other skills (e.g. `research-gap-identifier` depends on output from `paper-structural-extractor`)
- **Framework-agnostic**: work with Claude Code, Claude API, Claude App, and any framework supporting the open standard

---

## Skills

| Skill folder | What it does | Requires LLM? |
|---|---|---|
| `paper-structural-extractor` | Extract structured JSON from a paper (arXiv / DOI / PDF) | Yes |
| `bibtex-fixer-enricher` | Fix, normalize, and enrich BibTeX via Crossref API | No |
| `experiment-result-comparator` | Rank experiments, generate LaTeX/Markdown tables, trade-off analysis | Optional |
| `statistical-test-advisor` | Recommend + run statistical tests with Python/R code | Optional |
| `research-gap-identifier` | Coverage matrix + unexplored research directions | Yes |
| `reproducibility-checker` | Analyze a GitHub repo for reproducibility issues (score 0–100) | Optional |

**Dependency graph:**
```
Layer 1 — foundational:   paper-structural-extractor · bibtex-fixer-enricher · reproducibility-checker
Layer 2 — standalone:     experiment-result-comparator · statistical-test-advisor
Layer 3 — composite:      research-gap-identifier  (uses output of paper-structural-extractor)
```

---

## Project Structure

```
sciskills/
├── skills/                          ← Agent Skills (official standard)
│   ├── paper-structural-extractor/
│   │   ├── SKILL.md                 ← Instructions for the agent
│   │   └── run.py                   ← Executable script called from SKILL.md
│   ├── bibtex-fixer-enricher/
│   │   ├── SKILL.md
│   │   ├── run.py
│   │   └── docs/issue-types.md      ← Reference loaded on demand
│   ├── experiment-result-comparator/
│   │   ├── SKILL.md
│   │   ├── run.py
│   │   └── docs/ablation-tables.md
│   ├── statistical-test-advisor/
│   │   ├── SKILL.md
│   │   ├── run.py
│   │   └── docs/normality-testing.md
│   ├── research-gap-identifier/
│   │   ├── SKILL.md
│   │   ├── run.py
│   │   └── merge_papers.py
│   └── reproducibility-checker/
│       ├── SKILL.md
│       ├── run.py
│       └── docs/checks-reference.md
│
├── sciskills/                       ← Python execution library (used by run.py scripts)
│   ├── core/                        ← BaseSkill, SkillResult, registry
│   ├── skills/                      ← Python skill implementations
│   └── utils/                       ← LLM client, API clients, LaTeX templates
│
├── tests/                           ← 57 passing unit tests
├── examples/                        ← standalone / LangChain / Claude usage
└── pyproject.toml
```

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/sciskills/sciskills
cd sciskills
pip install -e ".[all]"
```

### 2. Configure LLM

```bash
cp .env.example .env
# Edit .env and fill in your LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
```

Or export directly:
```bash
export LLM_API_KEY=your_key
export LLM_BASE_URL=https://ep-llm.zhenguanyu.com/gateway-cn-online/openai-compatible/v1
export LLM_MODEL=doubao-seed-1.8
```

### 3. Use with Claude Code (Agent Skills standard)

Place the `skills/` directory in your project or global `~/.claude/skills/`:

```bash
# Project-level (recommended):
mkdir -p .claude/skills
cp -r skills/* .claude/skills/

# Or global:
cp -r skills/* ~/.claude/skills/
```

Claude will automatically discover the skills and use them when relevant.

### 4. Use the scripts directly

```bash
# Extract paper structure from arXiv
python skills/paper-structural-extractor/run.py --arxiv 1706.03762

# Fix a .bib file
python skills/bibtex-fixer-enricher/run.py --bib refs.bib

# Compare experiment results
python skills/experiment-result-comparator/run.py --input experiments.json

# Get statistical test recommendation
python skills/statistical-test-advisor/run.py --input study_design.json

# Check a repo's reproducibility
python skills/reproducibility-checker/run.py --repo https://github.com/owner/repo
```

---

## Using the Python API Directly

For programmatic use in your own code or agent framework:

```python
import sciskills
from sciskills import registry

# Skill 1: Extract paper
skill = registry.get("paper_structural_extractor")
result = skill({"arxiv_id": "1706.03762"})
print(result.data["paper"]["research_question"])

# Skill 3: Compare experiments and get LaTeX table
skill = registry.get("experiment_result_comparator")
result = skill({
    "experiments": [
        {"name": "BERT",      "metrics": {"F1": 88.5, "Latency_ms": 120}},
        {"name": "RoBERTa",   "metrics": {"F1": 91.2, "Latency_ms": 280}},
        {"name": "DistilBERT","metrics": {"F1": 85.3, "Latency_ms":  65}},
    ],
    "primary_metric": "F1",
    "higher_is_better": {"F1": True, "Latency_ms": False},
    "output_format": "all",
})
print(result.data["latex_table"])

# Skill 4: Run a statistical test
skill = registry.get("statistical_test_advisor")
result = skill({
    "research_question_type": "group_comparison",
    "num_groups": 2,
    "variable_type": "continuous",
    "paired": False,
    "data": [control_group_scores, treatment_group_scores],
})
print(result.data["test_results"])    # p-value, statistic, significant
print(result.data["python_code"])     # ready-to-run code
```

---

## Agent Framework Integration

### Claude Tool Use (Anthropic API)

```python
from sciskills.core.adapters import SciSkillClaudeTool
from sciskills import registry
import anthropic

adapter = SciSkillClaudeTool(registry.get("paper_structural_extractor"))
client  = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    tools=[adapter.tool_definition()],
    messages=[{"role": "user", "content": "Extract arXiv:1706.03762"}],
)
```

### LangChain

```python
from sciskills.core.adapters import SciSkillLangChainTool
from sciskills import registry

lc_tool = SciSkillLangChainTool(registry.get("bibtex_fixer_enricher")).as_langchain_tool()
```

### All skills as OpenAI-compatible tools

```python
from sciskills import registry
tools = registry.to_openai_tools()  # plug into any OpenAI-compatible framework
```

---

## Architecture: Two Layers

SciSkills has a **dual-layer architecture**:

| Layer | Location | Purpose |
|-------|----------|---------|
| **Skill folders** (`skills/`) | Agent Skills standard | `SKILL.md` instructions + CLI scripts. What the agent reads and invokes. |
| **Python library** (`sciskills/`) | Internal execution engine | `BaseSkill`, `SkillResult`, implementations. What the scripts run. |

This means you can use SciSkills in three ways:
1. **Agent Skills** — drop the `skills/` folder into `.claude/skills/` and let Claude use them autonomously
2. **CLI scripts** — call `run.py` directly from the command line or shell scripts
3. **Python API** — import and call from your own code or agent framework

---

## Development

```bash
git clone https://github.com/sciskills/sciskills
cd sciskills
pip install -e ".[dev,pdf,bibtex,stats]"
pytest  # 57 tests
```

### Roadmap

- **v0.1** ✓ — Core framework + all 6 skills + official Skill folders
- **v0.2** — Async execution, streaming, skill composition helpers
- **v0.3** — Skill versioning, dependency declarations, evaluation harness
- **v1.0** — Stable API, full docs site, PyPI release

---

## Contributing

Contributions welcome. Please open an issue before a large PR. See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

## License

MIT © SciSkills Contributors
