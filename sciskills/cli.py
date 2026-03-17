"""
Unified CLI entry point for SciSkills.

Usage:
    sciskills list
    sciskills run <skill-name> [--help]
    sciskills run paper-structural-extractor --arxiv 1706.03762
    sciskills run bibtex-fixer-enricher --bib refs.bib
    sciskills run experiment-result-comparator --input experiments.json
    sciskills run statistical-test-advisor --input study.json
    sciskills run research-gap-identifier --input papers.json
    sciskills run reproducibility-checker --repo https://github.com/owner/repo
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# Map skill name (kebab-case) → run.py path relative to project root
_SKILL_SCRIPTS: dict[str, str] = {
    "paper-structural-extractor":   "skills/paper-structural-extractor/run.py",
    "bibtex-fixer-enricher":        "skills/bibtex-fixer-enricher/run.py",
    "experiment-result-comparator": "skills/experiment-result-comparator/run.py",
    "statistical-test-advisor":     "skills/statistical-test-advisor/run.py",
    "research-gap-identifier":      "skills/research-gap-identifier/run.py",
    "reproducibility-checker":      "skills/reproducibility-checker/run.py",
}

# Aliases: underscore_names also work
_ALIASES: dict[str, str] = {
    s.replace("-", "_"): s for s in _SKILL_SCRIPTS
}


def _find_project_root() -> Path:
    """Walk up from this file until we find pyproject.toml."""
    here = Path(__file__).resolve().parent
    for candidate in [here, here.parent, here.parent.parent]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def cmd_list() -> None:
    """Print all available skills."""
    import sciskills  # noqa: F401
    from sciskills import registry
    print("Available SciSkills:\n")
    for skill_info in registry.list_skills():
        print(f"  {skill_info['name']}")
        print(f"    {skill_info['description'][:100]}...")
        print()


def cmd_run(skill_name: str, args: list[str]) -> None:
    """Delegate to the skill's run.py, passing remaining args through."""
    # Normalize name
    canonical = _ALIASES.get(skill_name, skill_name)
    if canonical not in _SKILL_SCRIPTS:
        available = "\n  ".join(_SKILL_SCRIPTS.keys())
        print(f"Unknown skill: '{skill_name}'\n\nAvailable skills:\n  {available}", file=sys.stderr)
        sys.exit(1)

    root = _find_project_root()
    script = root / _SKILL_SCRIPTS[canonical]

    if not script.exists():
        print(f"Script not found: {script}\nMake sure you cloned the full repo.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([sys.executable, str(script)] + args)
    sys.exit(result.returncode)


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    command = args[0]

    if command == "list":
        cmd_list()
    elif command == "run":
        if len(args) < 2:
            print("Usage: sciskills run <skill-name> [args...]\n\nRun 'sciskills list' to see available skills.", file=sys.stderr)
            sys.exit(1)
        cmd_run(args[1], args[2:])
    else:
        print(f"Unknown command: '{command}'. Use 'list' or 'run'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
