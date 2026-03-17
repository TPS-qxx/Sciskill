#!/usr/bin/env python3
"""
CLI entry point for the experiment-result-comparator skill.

Usage:
    python run.py --input experiments.json
    python run.py --input experiments.json --no-tradeoff
"""
import argparse
import json
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main():
    parser = argparse.ArgumentParser(description="Compare experiment results and generate tables.")
    parser.add_argument("--input", metavar="JSON_FILE", required=True,
                        help="Path to input JSON file with experiments")
    parser.add_argument("--no-tradeoff", action="store_true",
                        help="Skip LLM trade-off analysis (faster)")
    parser.add_argument("--format", choices=["json", "latex", "markdown", "all"],
                        default=None, help="Override output_format in the input JSON")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            params = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'{{"error": "Failed to read input file: {e}"}}', file=sys.stderr)
        sys.exit(1)

    if args.no_tradeoff:
        params["include_tradeoff"] = False
    if args.format:
        params["output_format"] = args.format

    try:
        from sciskills.skills.experiment_comparator import ExperimentResultComparator
    except ImportError:
        print('{"error": "sciskills not installed. Run: pip install -e ."}', file=sys.stderr)
        sys.exit(1)

    skill = ExperimentResultComparator()
    result = skill(params)

    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
