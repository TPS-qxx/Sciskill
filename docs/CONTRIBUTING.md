# Contributing to SciSkills

Thank you for your interest in contributing! SciSkills is an open-source project and contributions of all kinds are welcome.

## Before You Start

**Please open an issue before submitting a large PR.** Discussing the design first saves everyone time. For small bug fixes or typos, feel free to open a PR directly.

## Types of Contributions

### 1. New Skills

The most impactful contribution. A new Skill should:

- Have a clear, narrow scope (one well-defined task)
- Have a `SKILL.md` with proper frontmatter and step-by-step instructions
- Have a `run.py` CLI script that works standalone
- Have a corresponding Python implementation under `sciskills/skills/`
- Have tests (at least 5-8 unit tests, no LLM calls in tests)

Suggested new skills:
- `related-work-generator` — generate a Related Work section from structured paper data
- `paper-reviewer` — structured review following NeurIPS / ICLR format
- `dataset-card-generator` — generate a HuggingFace-style dataset card
- `citation-network-analyzer` — analyze citation patterns from a paper list

### 2. Improving Existing Skills

- Better heuristics in `bibtex-fixer-enricher` rules
- More reproducibility checks in `reproducibility-checker`
- Additional statistical tests in `statistical-test-advisor`
- Improved PDF parsing in `paper-structural-extractor`

### 3. Bug Fixes

Check the [Issues](https://github.com/TPS-qxx/Sciskill/issues) page for open bugs.

### 4. Documentation

- Improving SKILL.md instructions
- Adding more examples to `docs/` reference files
- Translating the README (Chinese, Japanese, etc.)

---

## Development Setup

```bash
git clone https://github.com/TPS-qxx/Sciskill.git
cd Sciskill

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with all dev dependencies
pip install -e ".[dev,bibtex,stats]"

# Run tests
pytest

# Lint
ruff check sciskills/
```

---

## Adding a New Skill

### Step 1: Create the Skill folder

```
skills/your-skill-name/
├── SKILL.md       # required
├── run.py         # required — CLI entry point
└── docs/          # optional — reference files
    └── reference.md
```

**`SKILL.md` frontmatter rules** (from the official standard):
- `name`: kebab-case, max 64 characters, no "anthropic" or "claude"
- `description`: max 1024 characters, must describe both WHAT it does AND WHEN to use it

### Step 2: Create the Python implementation

```
sciskills/skills/your_skill_name/
├── __init__.py    # exports YourSkillClass
└── skill.py       # inherits BaseSkill, decorated with @registry.register
```

```python
from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry

@registry.register
class YourSkill(BaseSkill):
    name = "your_skill_name"           # underscore version of folder name
    description = "..."
    input_schema = { ... }
    output_schema = { ... }

    def execute(self, params: dict) -> SkillResult:
        ...
        return SkillResult.ok(data={...})
```

### Step 3: Register in `sciskills/skills/__init__.py`

```python
from sciskills.skills.your_skill_name import YourSkill
```

### Step 4: Write tests

```
tests/skills/test_your_skill.py
```

Tests must not make real LLM or network calls. Use `unittest.mock.patch` to mock external dependencies.

### Step 5: Add a `run.py` CLI script

Follow the pattern in existing `skills/*/run.py` files.

---

## Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Linter passes (`ruff check sciskills/`)
- [ ] New skill has `SKILL.md` with valid frontmatter
- [ ] New skill has `run.py` CLI that works standalone
- [ ] No hardcoded API keys or personal paths
- [ ] Updated `sciskills/skills/__init__.py` if adding a new skill

---

## Code Style

- Python 3.10+ syntax (use `X | Y` unions, `match`, etc.)
- Type hints on all public functions
- No line length limit enforced, but keep lines readable (< 120 chars preferred)
- `ruff` for linting (configured in `pyproject.toml`)
- Docstrings only where logic isn't self-evident

---

## Questions?

Open a [Discussion](https://github.com/TPS-qxx/Sciskill/discussions) or an Issue.
