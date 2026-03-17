#!/usr/bin/env python3
"""
CLI entry point for the research-gap-identifier skill.

Usage:
    python run.py --input papers.json
    python run.py --input papers.json --topic "relation extraction" --threshold 0.4
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
    parser = argparse.ArgumentParser(description="Identify research gaps from a paper collection.")
    parser.add_argument("--input", metavar="JSON_FILE", required=True,
                        help="Path to JSON file with 'papers' array")
    parser.add_argument("--topic", metavar="TOPIC",
                        help="Research topic for context (e.g. 'relation extraction')")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Coverage fraction below which a combination is a 'gap' (default: 0.3)")
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'{{"error": "Failed to read input: {e}"}}', file=sys.stderr)
        sys.exit(1)

    # Support both {"papers": [...]} and [...] directly
    if isinstance(data, list):
        papers = data
    else:
        papers = data.get("papers", [])

    params = {
        "papers": papers,
        "min_coverage_threshold": args.threshold or data.get("min_coverage_threshold", 0.3),
        "topic": args.topic or data.get("topic", ""),
        "dimensions": data.get("dimensions", ["methods", "datasets", "tasks"]),
    }

    if not params["papers"]:
        print('{"error": "No papers found in input. Expected a list or {\"papers\": [...]}"}',
              file=sys.stderr)
        sys.exit(1)

    try:
        from sciskills.skills.gap_identifier import ResearchGapIdentifier
    except ImportError:
        print('{"error": "sciskills not installed. Run: pip install -e ."}', file=sys.stderr)
        sys.exit(1)

    skill = ResearchGapIdentifier()
    result = skill(params)

    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
