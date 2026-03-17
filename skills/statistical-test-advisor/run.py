#!/usr/bin/env python3
"""
CLI entry point for the statistical-test-advisor skill.

Usage:
    python run.py --input /tmp/stats_input.json
    python run.py --input /tmp/stats_input.json --no-interpret
"""
import argparse
import json
import os
import sys
from unittest.mock import patch

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main():
    parser = argparse.ArgumentParser(description="Recommend and optionally run a statistical test.")
    parser.add_argument("--input", metavar="JSON_FILE", required=True,
                        help="Path to input JSON file with research design parameters")
    parser.add_argument("--no-interpret", action="store_true",
                        help="Skip LLM-generated interpretation (faster, offline)")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            params = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'{{"error": "Failed to read input: {e}"}}', file=sys.stderr)
        sys.exit(1)

    try:
        from sciskills.skills.statistical_advisor import StatisticalTestAdvisor
    except ImportError:
        print('{"error": "sciskills not installed. Run: pip install -e ."}', file=sys.stderr)
        sys.exit(1)

    skill = StatisticalTestAdvisor()

    if args.no_interpret:
        with patch.object(skill, "_generate_interpretation",
                         return_value="[Interpretation skipped — use --interpret to enable]"):
            result = skill(params)
    else:
        result = skill(params)

    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
